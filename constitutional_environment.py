#!/usr/bin/env python3
"""Build, persist, and validate a forward Sanctum constitutional environment manifest."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Callable, TypeVar

import harness

STANDARD_ID = "CONSTITUTIONAL-ENVIRONMENT-001"
CERTIFICATION = "NONE_SELF_CERTIFICATION_PROHIBITED"
HORUS_RESPONSE_CONTRACT = "contracts/horus-query-response.schema.json"
T = TypeVar("T")


class ConstitutionalEnvironmentError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConstitutionalEnvironmentError(message)


def sha256_file(path: Path) -> str:
    _require(path.is_file(), f"required file missing: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit(repo: Path) -> str:
    _require((repo / ".git").exists(), f"not a git checkout: {repo}")
    try:
        value = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError as exc:
        raise ConstitutionalEnvironmentError(f"cannot resolve git commit for {repo}") from exc
    _require(len(value) == 40, f"invalid git commit for {repo}: {value}")
    return value


def _binding(base: Path, relpath: str) -> dict:
    return {"path": relpath, "sha256": sha256_file(base / relpath)}


def build_manifest(*, estate: Path, inquiry_id: str) -> dict:
    sanctum, horus = estate / "Sanctum", estate / "Horus"
    _require(sanctum.is_dir(), "Sanctum repository missing from estate")
    _require(horus.is_dir(), "Horus repository missing from estate")
    _require(isinstance(inquiry_id, str) and inquiry_id.strip(), "inquiry_id is required")

    registry_path = sanctum / "registry/ministers.yaml"
    registry = harness.yaml_load(registry_path.read_text(encoding="utf-8"))
    established = [m for m in registry.get("ministers", []) if m.get("membership_status") == "established"]
    _require(established, "registry contains no established ministers")

    minister_bindings, seen = [], set()
    for item in established:
        minister_id, repository, pinned = item.get("minister_id"), item.get("repository"), item.get("pinned_commit")
        manifest_path = item.get("manifest_path") or item.get("manifest_ref") or "manifest.yaml"
        _require(minister_id and repository and pinned, "established minister registry entry incomplete")
        _require(minister_id not in seen, f"duplicate established minister: {minister_id}")
        seen.add(minister_id)
        repo = estate / repository.split("/")[-1]
        actual = git_commit(repo)
        _require(actual == pinned, f"{minister_id} checkout {actual} does not match registry pin {pinned}")
        minister_bindings.append({
            "minister_id": minister_id,
            "repository": repository,
            "pinned_commit": pinned,
            "manifest_path": manifest_path,
            "manifest_sha256": sha256_file(repo / manifest_path),
        })

    sanctum_files = {
        "assembly_spec": _binding(sanctum, "standards/assembly-spec.yaml"),
        "registry": _binding(sanctum, "registry/ministers.yaml"),
        "final_judgment_contract": _binding(sanctum, "contracts/final-judgment-package.schema.v1.1.0.json"),
        "proposition_matrix_standard": _binding(sanctum, "standards/proposition-matrix.yaml"),
        "ministerial_silence_standard": _binding(sanctum, "standards/ministerial-silence.yaml"),
        "source_absence_standard": _binding(sanctum, "standards/source-absence-taxonomy.yaml"),
    }
    manifest = {
        "record_type": "constitutional_environment_manifest",
        "standard": STANDARD_ID,
        "inquiry_id": inquiry_id,
        "sanctum": {
            "repository": "izzy9118-blip/Sanctum",
            "repository_commit": git_commit(sanctum),
            "assembly_spec": sanctum_files["assembly_spec"],
            "registry": {**sanctum_files["registry"], "version": str(registry.get("version"))},
            "final_judgment_contract": sanctum_files["final_judgment_contract"],
            "proposition_matrix_standard": sanctum_files["proposition_matrix_standard"],
            "ministerial_silence_standard": sanctum_files["ministerial_silence_standard"],
            "source_absence_standard": sanctum_files["source_absence_standard"],
        },
        "horus": {
            "repository": "izzy9118-blip/Horus",
            "repository_commit": git_commit(horus),
            "response_contract": _binding(horus, HORUS_RESPONSE_CONTRACT),
        },
        "ministers": sorted(minister_bindings, key=lambda x: x["minister_id"]),
        "runtime": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "manifest_builder_path": "constitutional_environment.py",
            "manifest_builder_sha256": sha256_file(sanctum / "constitutional_environment.py"),
        },
        "certification": CERTIFICATION,
    }
    validate_manifest(manifest, estate=estate)
    return manifest


def validate_manifest(manifest: dict, *, estate: Path) -> dict:
    _require(manifest.get("record_type") == "constitutional_environment_manifest", "wrong manifest record_type")
    _require(manifest.get("standard") == STANDARD_ID, "wrong constitutional environment standard")
    _require(manifest.get("certification") == CERTIFICATION, "manifest may not self-certify truth or completeness")
    sanctum, horus = estate / "Sanctum", estate / "Horus"
    _require(manifest.get("sanctum", {}).get("repository_commit") == git_commit(sanctum), "Sanctum commit mismatch")
    _require(manifest.get("horus", {}).get("repository_commit") == git_commit(horus), "Horus commit mismatch")

    for key in ["assembly_spec", "registry", "final_judgment_contract", "proposition_matrix_standard", "ministerial_silence_standard", "source_absence_standard"]:
        binding = manifest["sanctum"][key]
        _require(binding["sha256"] == sha256_file(sanctum / binding["path"]), f"Sanctum binding changed: {key}")
    hb = manifest["horus"]["response_contract"]
    _require(hb.get("path") == HORUS_RESPONSE_CONTRACT, "Horus response contract path mismatch")
    _require(hb["sha256"] == sha256_file(horus / hb["path"]), "Horus response contract binding changed")

    registry = harness.yaml_load((sanctum / "registry/ministers.yaml").read_text(encoding="utf-8"))
    _require(str(manifest["sanctum"]["registry"].get("version")) == str(registry.get("version")), "registry version mismatch")
    expected = {m["minister_id"]: m for m in registry.get("ministers", []) if m.get("membership_status") == "established"}
    actual_items = manifest.get("ministers", [])
    _require(len(actual_items) == len({m.get("minister_id") for m in actual_items}), "duplicate minister binding in manifest")
    actual = {m["minister_id"]: m for m in actual_items}
    _require(set(actual) == set(expected), "manifest minister set differs from established registry")
    for minister_id, reg in expected.items():
        item = actual[minister_id]
        _require(item["repository"] == reg["repository"], f"{minister_id} repository mismatch")
        _require(item["pinned_commit"] == reg["pinned_commit"], f"{minister_id} pin mismatch")
        repo = estate / reg["repository"].split("/")[-1]
        _require(git_commit(repo) == reg["pinned_commit"], f"{minister_id} live checkout differs from registry pin")
        _require(item["manifest_sha256"] == sha256_file(repo / item["manifest_path"]), f"{minister_id} manifest hash mismatch")
    _require(manifest.get("runtime", {}).get("manifest_builder_sha256") == sha256_file(sanctum / "constitutional_environment.py"), "manifest builder hash mismatch")
    return manifest


def manifest_path(*, estate: Path, inquiry_id: str) -> Path:
    return estate / "Sanctum" / "inquiries" / inquiry_id / "constitutional-environment.json"


def write_manifest(*, estate: Path, inquiry_id: str) -> Path:
    target = manifest_path(estate=estate, inquiry_id=inquiry_id)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        _require(existing.get("inquiry_id") == inquiry_id, "existing constitutional environment inquiry identity mismatch")
        validate_manifest(existing, estate=estate)
        return target
    manifest = build_manifest(estate=estate, inquiry_id=inquiry_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def required_environment_call(*, estate: Path, inquiry_id: str, downstream: Callable[[], T]) -> T:
    """Hard precondition seam for forward inquiry work."""
    path = write_manifest(estate=estate, inquiry_id=inquiry_id)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(persisted, estate=estate)
    return downstream()


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--inquiry-id", required=True)
    args = p.parse_args(argv)
    try:
        config = harness.load_config(Path(args.config))
        path = write_manifest(estate=Path(config["estate"]), inquiry_id=args.inquiry_id)
        print(f"CONSTITUTIONAL ENVIRONMENT READY: {path}")
        return 0
    except (ConstitutionalEnvironmentError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CONSTITUTIONAL ENVIRONMENT FAIL: {exc}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
