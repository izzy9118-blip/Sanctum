#!/usr/bin/env python3
"""Universal minister adapter dispatcher for the adopted Sanctum transport.

The authoritative minister registry continues to define sovereign membership and the
owner-certified minister corpus pin. registry/adapters.v1.yaml defines a separate
runtime overlay pin. The overlay must descend from the certified corpus pin and may
change only the explicitly allowed adapter transport paths. Sanctum never inspects a
minister's private load order.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

import harness

BASE = Path(__file__).resolve().parent
PROTOCOL = "sanctum.adapter.v1"
AUTHORITATIVE_REGISTRY = "registry/ministers.yaml"
ADAPTER_REGISTRY = "registry/adapters.v1.yaml"
CONTRACT = "contracts/sanctum-adapter.schema.v1.json"


class UniversalDispatchError(RuntimeError):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    value = harness.yaml_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UniversalDispatchError(f"expected mapping at {path}")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UniversalDispatchError(f"expected JSON object at {path}")
    return value


def _git(repo: Path, *args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, timeout=timeout)


def _git_head(repo: Path) -> str:
    proc = _git(repo, "rev-parse", "HEAD")
    value = proc.stdout.strip()
    if proc.returncode != 0 or len(value) != 40:
        raise UniversalDispatchError(f"cannot resolve exact commit for {repo}")
    return value


def _verify_overlay(repo: Path, base_commit: str, overlay_commit: str, allowed_paths: list[str]) -> None:
    ancestor = _git(repo, "merge-base", "--is-ancestor", base_commit, overlay_commit)
    if ancestor.returncode != 0:
        raise UniversalDispatchError(f"runtime overlay {overlay_commit} does not descend from certified base {base_commit}")
    diff = _git(repo, "diff", "--name-only", f"{base_commit}..{overlay_commit}")
    if diff.returncode != 0:
        raise UniversalDispatchError(f"cannot inspect runtime overlay diff for {repo.name}")
    changed = sorted(line.strip() for line in diff.stdout.splitlines() if line.strip())
    expected = sorted(allowed_paths)
    if changed != expected:
        raise UniversalDispatchError(
            f"runtime overlay for {repo.name} changed forbidden paths: expected={expected}, actual={changed}"
        )


def _invoke(repo: Path, entrypoint: str, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path = (repo / entrypoint).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError as exc:
        raise UniversalDispatchError("adapter entrypoint escapes repository") from exc
    if not path.is_file():
        raise UniversalDispatchError(f"adapter entrypoint missing: {path}")
    proc = subprocess.run(
        [sys.executable, str(path), command], cwd=repo,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True, text=True, check=False, shell=False, timeout=120,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "no detail"
        raise UniversalDispatchError(f"{repo.name} adapter {command} failed: {detail[:500]}")
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise UniversalDispatchError(f"{repo.name} adapter {command} returned invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise UniversalDispatchError(f"{repo.name} adapter {command} must return one JSON object")
    return value


def _validate_contract(value: dict[str, Any]) -> None:
    schema = _load_json(BASE / CONTRACT)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(e.path))
    if errors:
        raise UniversalDispatchError("adapter contract validation failed: " + "; ".join(e.message for e in errors))


def _registries() -> tuple[dict[str, Any], dict[str, Any]]:
    authoritative = _load_yaml(BASE / AUTHORITATIVE_REGISTRY)
    adapters = _load_yaml(BASE / ADAPTER_REGISTRY)
    if adapters.get("protocol") != PROTOCOL:
        raise UniversalDispatchError("adapter registry protocol mismatch")
    if adapters.get("status") != "OWNER_AUTHORIZED_OPERATIONAL_OVERLAYS":
        raise UniversalDispatchError("adapter registry is not owner-authorized for operation")
    if adapters.get("authority") != "REPOSITORY_OWNER_DIRECTIVE":
        raise UniversalDispatchError("adapter registry lacks owner authority")
    return authoritative, adapters


def binding_plan(estate: Path) -> list[tuple[dict[str, Any], dict[str, Any], Path]]:
    authoritative, adapters = _registries()
    established = {
        item["minister_id"]: item
        for item in authoritative.get("ministers", [])
        if item.get("membership_status") == "established"
    }
    bindings = {item["minister_id"]: item for item in adapters.get("bindings", [])}
    if set(bindings) != set(established):
        raise UniversalDispatchError(
            f"adapter set must exactly cover established ministers: established={sorted(established)}, bindings={sorted(bindings)}"
        )
    plan = []
    for minister_id in sorted(established):
        minister = established[minister_id]
        binding = bindings[minister_id]
        if binding.get("repository") != minister.get("repository"):
            raise UniversalDispatchError(f"{minister_id} adapter repository differs from authoritative registry")
        if binding.get("certified_base_commit") != minister.get("pinned_commit"):
            raise UniversalDispatchError(f"{minister_id} adapter overlay is not bound to the authoritative minister pin")
        if binding.get("protocol") != PROTOCOL:
            raise UniversalDispatchError(f"{minister_id} adapter protocol mismatch")
        allowed = binding.get("allowed_overlay_paths")
        if not isinstance(allowed, list) or allowed != [binding.get("entrypoint")]:
            raise UniversalDispatchError(f"{minister_id} overlay path policy must contain only its adapter entrypoint")
        repo = estate / str(binding["repository"]).split("/")[-1]
        if not repo.is_dir():
            raise UniversalDispatchError(f"runtime overlay checkout missing: {repo}")
        actual = _git_head(repo)
        overlay = binding.get("runtime_overlay_commit")
        if actual != overlay:
            raise UniversalDispatchError(f"{minister_id} checkout {actual} does not match runtime overlay {overlay}")
        _verify_overlay(repo, minister["pinned_commit"], overlay, allowed)
        plan.append((minister, binding, repo))
    return plan


def probe(estate: Path) -> dict[str, Any]:
    results = []
    for minister, binding, repo in binding_plan(estate):
        descriptor = _invoke(repo, binding["entrypoint"], "describe")
        _validate_contract(descriptor)
        if descriptor.get("minister_id") != minister["minister_id"] or descriptor.get("repository") != minister["repository"]:
            raise UniversalDispatchError("adapter descriptor identity mismatch")
        if descriptor.get("repository_commit") != binding["runtime_overlay_commit"]:
            raise UniversalDispatchError("adapter descriptor runtime overlay mismatch")
        validation = _invoke(repo, binding["entrypoint"], "validate-interface")
        _validate_contract(validation)
        results.append({
            "minister_id": minister["minister_id"],
            "repository": minister["repository"],
            "certified_base_commit": minister["pinned_commit"],
            "runtime_overlay_commit": binding["runtime_overlay_commit"],
            "descriptor": descriptor,
            "interface_validation": validation,
        })
    return {
        "record_type": "sanctum_universal_adapter_probe",
        "protocol": PROTOCOL,
        "status": "ALL_ESTABLISHED_MINISTERS_INTEROPERABLE_THROUGH_ADOPTED_OVERLAYS",
        "established_minister_count": len(results),
        "results": results,
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }


def prepare(estate: Path, inquiry: dict[str, Any]) -> dict[str, Any]:
    inquiry_id = inquiry.get("inquiry_id")
    question = inquiry.get("question")
    briefing = inquiry.get("common_briefing")
    if not isinstance(inquiry_id, str) or not inquiry_id:
        raise UniversalDispatchError("inquiry_id is required")
    if not isinstance(question, str) or not question.strip():
        raise UniversalDispatchError("question is required")
    if not isinstance(briefing, dict) or not isinstance(briefing.get("sha256"), str) or len(briefing["sha256"]) != 64:
        raise UniversalDispatchError("common_briefing.sha256 is required")
    prepared = []
    for minister, binding, repo in binding_plan(estate):
        request = {
            "record_type": "sanctum_adapter_request",
            "protocol": PROTOCOL,
            "inquiry_id": inquiry_id,
            "minister_id": minister["minister_id"],
            "question": question,
            "common_briefing": briefing,
            "repository_pin": {
                "repository": minister["repository"],
                "commit": binding["runtime_overlay_commit"],
            },
        }
        extras = inquiry.get("minister_inputs", {}).get(minister["minister_id"], {}) if isinstance(inquiry.get("minister_inputs"), dict) else {}
        if isinstance(extras, dict):
            request.update(extras)
        _validate_contract(request)
        result = _invoke(repo, binding["entrypoint"], "prepare-request", request)
        _validate_contract(result)
        if result.get("common_briefing", {}).get("sha256") != briefing["sha256"]:
            raise UniversalDispatchError("adapter changed the immutable common briefing binding")
        if result.get("repository_commit") != binding["runtime_overlay_commit"]:
            raise UniversalDispatchError("adapter changed its exact runtime overlay pin")
        result["certified_base_commit"] = minister["pinned_commit"]
        prepared.append(result)
    return {
        "record_type": "sanctum_universal_preparation",
        "protocol": PROTOCOL,
        "inquiry_id": inquiry_id,
        "common_briefing_sha256": briefing["sha256"],
        "prepared_count": len(prepared),
        "prepared": prepared,
        "authority": "OWNER_AUTHORIZED_OPERATIONAL_OVERLAYS",
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--estate", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe")
    prep = sub.add_parser("prepare")
    prep.add_argument("--inquiry", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = probe(args.estate.resolve()) if args.command == "probe" else prepare(args.estate.resolve(), _load_json(args.inquiry))
    except (UniversalDispatchError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"UNIVERSAL DISPATCH ERROR: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
