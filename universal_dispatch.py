#!/usr/bin/env python3
"""Forward-only universal minister adapter dispatcher.

This is an interoperability proving surface, not the adopted Assembly runner. It reads
established membership from the authoritative registry, reads exact candidate adapter
bindings from registry/adapter-candidates.v1.yaml, and invokes every candidate through
one transport without inspecting any minister-private corpus or load order.
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
CANDIDATE_REGISTRY = "registry/adapter-candidates.v1.yaml"
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


def _git_head(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    value = proc.stdout.strip()
    if proc.returncode != 0 or len(value) != 40:
        raise UniversalDispatchError(f"cannot resolve exact commit for {repo}")
    return value


def _invoke(repo: Path, entrypoint: str, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path = (repo / entrypoint).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError as exc:
        raise UniversalDispatchError("adapter entrypoint escapes repository") from exc
    if not path.is_file():
        raise UniversalDispatchError(f"adapter entrypoint missing: {path}")
    proc = subprocess.run(
        [sys.executable, str(path), command],
        cwd=repo,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        timeout=120,
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
    candidates = _load_yaml(BASE / CANDIDATE_REGISTRY)
    if candidates.get("protocol") != PROTOCOL:
        raise UniversalDispatchError("candidate registry protocol mismatch")
    if candidates.get("status") != "CANDIDATE_PENDING_OWNER_ADOPTION" or candidates.get("authority") != "NONE":
        raise UniversalDispatchError("candidate registry may not imply adopted authority")
    return authoritative, candidates


def _binding_plan(estate: Path) -> list[tuple[dict[str, Any], dict[str, Any], Path]]:
    authoritative, candidates = _registries()
    established = {
        item["minister_id"]: item
        for item in authoritative.get("ministers", [])
        if item.get("membership_status") == "established"
    }
    bindings = {item["minister_id"]: item for item in candidates.get("bindings", [])}
    if set(bindings) != set(established):
        raise UniversalDispatchError(
            f"candidate adapter set must exactly cover established ministers: established={sorted(established)}, bindings={sorted(bindings)}"
        )
    plan = []
    for minister_id in sorted(established):
        minister = established[minister_id]
        binding = bindings[minister_id]
        if binding.get("repository") != minister.get("repository"):
            raise UniversalDispatchError(f"{minister_id} candidate repository differs from authoritative registry")
        if binding.get("authoritative_registry_pin_unchanged") != minister.get("pinned_commit"):
            raise UniversalDispatchError(f"{minister_id} candidate record does not preserve the authoritative pin")
        if binding.get("protocol") != PROTOCOL:
            raise UniversalDispatchError(f"{minister_id} candidate protocol mismatch")
        repo = estate / str(binding["repository"]).split("/")[-1]
        if not repo.is_dir():
            raise UniversalDispatchError(f"candidate checkout missing: {repo}")
        actual = _git_head(repo)
        if actual != binding.get("candidate_commit"):
            raise UniversalDispatchError(
                f"{minister_id} checkout {actual} does not match candidate adapter commit {binding.get('candidate_commit')}"
            )
        plan.append((minister, binding, repo))
    return plan


def probe(estate: Path) -> dict[str, Any]:
    results = []
    for minister, binding, repo in _binding_plan(estate):
        descriptor = _invoke(repo, binding["entrypoint"], "describe")
        _validate_contract(descriptor)
        if descriptor.get("minister_id") != minister["minister_id"]:
            raise UniversalDispatchError("adapter descriptor minister identity mismatch")
        if descriptor.get("repository") != minister["repository"]:
            raise UniversalDispatchError("adapter descriptor repository mismatch")
        if descriptor.get("repository_commit") != binding["candidate_commit"]:
            raise UniversalDispatchError("adapter descriptor commit mismatch")
        validation = _invoke(repo, binding["entrypoint"], "validate-interface")
        _validate_contract(validation)
        if validation.get("repository_commit") != binding["candidate_commit"]:
            raise UniversalDispatchError("adapter validation commit mismatch")
        results.append(
            {
                "minister_id": minister["minister_id"],
                "repository": minister["repository"],
                "authoritative_registry_pin": minister["pinned_commit"],
                "candidate_adapter_commit": binding["candidate_commit"],
                "descriptor": descriptor,
                "interface_validation": validation,
            }
        )
    return {
        "record_type": "sanctum_universal_adapter_probe",
        "protocol": PROTOCOL,
        "status": "ALL_ESTABLISHED_MINISTERS_INTEROPERABLE_AS_CANDIDATES_NOT_ADOPTED",
        "established_minister_count": len(results),
        "results": results,
        "authority": "NONE",
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
    for minister, binding, repo in _binding_plan(estate):
        request = {
            "record_type": "sanctum_adapter_request",
            "protocol": PROTOCOL,
            "inquiry_id": inquiry_id,
            "minister_id": minister["minister_id"],
            "question": question,
            "common_briefing": briefing,
            "repository_pin": {
                "repository": minister["repository"],
                "commit": binding["candidate_commit"],
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
        if result.get("repository_commit") != binding["candidate_commit"]:
            raise UniversalDispatchError("adapter changed its exact repository pin")
        prepared.append(result)
    return {
        "record_type": "sanctum_universal_preparation",
        "protocol": PROTOCOL,
        "inquiry_id": inquiry_id,
        "common_briefing_sha256": briefing["sha256"],
        "prepared_count": len(prepared),
        "prepared": prepared,
        "authority": "CANDIDATE_INTEROPERABILITY_PROOF_ONLY",
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
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
