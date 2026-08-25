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
HORUS_REGISTRY = "registry/horus.yaml"
ADAPTER_REGISTRY = "registry/adapters.v1.yaml"
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
    proc = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    value = proc.stdout.strip()
    _require(proc.returncode == 0 and len(value) == 40, f"invalid git commit for {repo}: {value}")
    return value


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)


def _binding(base: Path, relpath: str) -> dict:
    return {"path": relpath, "sha256": sha256_file(base / relpath)}


def _load_horus_registry(sanctum: Path) -> dict:
    path = sanctum / HORUS_REGISTRY
    _require(path.is_file(), f"Horus registry missing: {path}")
    registry = harness.yaml_load(path.read_text(encoding="utf-8"))
    _require(registry.get("record_type") == "sanctum_horus_registry", "wrong Horus registry record_type")
    _require(registry.get("repository") == "izzy9118-blip/Horus", "Horus registry repository mismatch")
    pin = registry.get("pinned_commit", "")
    _require(isinstance(pin, str) and len(pin) == 40, "Horus registry pinned_commit is invalid")
    _require(registry.get("canonical_runtime") == "runtime/gather.py", "Horus registry canonical runtime mismatch")
    _require(registry.get("acquisition_protocol") == "HORUS-ACQUISITION-1.0", "Horus registry acquisition protocol mismatch")
    return registry


def _load_adapter_registry(sanctum: Path) -> dict:
    path = sanctum / ADAPTER_REGISTRY
    _require(path.is_file(), f"adapter registry missing: {path}")
    registry = harness.yaml_load(path.read_text(encoding="utf-8"))
    _require(registry.get("record_type") == "sanctum_adapter_registry", "wrong adapter registry record_type")
    _require(registry.get("protocol") == "sanctum.adapter.v1", "adapter registry protocol mismatch")
    _require(registry.get("status") == "OWNER_AUTHORIZED_OPERATIONAL_OVERLAYS", "adapter registry is not operationally authorized")
    return registry


def _verify_overlay(repo: Path, base_commit: str, overlay_commit: str, allowed_paths: list[str]) -> None:
    ancestor = _git(repo, "merge-base", "--is-ancestor", base_commit, overlay_commit)
    _require(ancestor.returncode == 0, f"overlay {overlay_commit} does not descend from certified base {base_commit}")
    diff = _git(repo, "diff", "--name-only", f"{base_commit}..{overlay_commit}")
    _require(diff.returncode == 0, f"cannot inspect overlay diff for {repo}")
    changed = sorted(line.strip() for line in diff.stdout.splitlines() if line.strip())
    _require(changed == sorted(allowed_paths), f"overlay changed forbidden paths for {repo.name}: {changed}")


def _minister_runtime_bindings(sanctum: Path, estate: Path, registry: dict) -> list[dict]:
    adapters = _load_adapter_registry(sanctum)
    bindings = {item["minister_id"]: item for item in adapters.get("bindings", [])}
    established = [m for m in registry.get("ministers", []) if m.get("membership_status") == "established"]
    _require({m.get("minister_id") for m in established} == set(bindings), "adapter registry must exactly cover established ministers")
    result = []
    seen = set()
    for item in established:
        minister_id = item.get("minister_id")
        repository = item.get("repository")
        pinned = item.get("pinned_commit")
        manifest_path = item.get("manifest_path") or item.get("manifest_ref") or "manifest.yaml"
        _require(minister_id and repository and pinned, "established minister registry entry incomplete")
        _require(minister_id not in seen, f"duplicate established minister: {minister_id}")
        seen.add(minister_id)
        binding = bindings[minister_id]
        _require(binding.get("repository") == repository, f"{minister_id} adapter repository mismatch")
        _require(binding.get("certified_base_commit") == pinned, f"{minister_id} adapter base differs from certified minister pin")
        overlay = binding.get("runtime_overlay_commit", "")
        entrypoint = binding.get("entrypoint", "")
        allowed = binding.get("allowed_overlay_paths")
        _require(isinstance(overlay, str) and len(overlay) == 40, f"{minister_id} runtime overlay pin invalid")
        _require(isinstance(entrypoint, str) and entrypoint, f"{minister_id} adapter entrypoint missing")
        _require(isinstance(allowed, list) and allowed == [entrypoint], f"{minister_id} overlay path policy invalid")
        repo = estate / repository.split("/")[-1]
        actual = git_commit(repo)
        _require(actual == overlay, f"{minister_id} checkout {actual} does not match runtime overlay {overlay}")
        _verify_overlay(repo, pinned, overlay, allowed)
        result.append({
            "minister_id": minister_id,
            "repository": repository,
            "pinned_commit": pinned,
            "certified_base_commit": pinned,
            "runtime_overlay_commit": overlay,
            "adapter_entrypoint": entrypoint,
            "manifest_path": manifest_path,
            "manifest_sha256": sha256_file(repo / manifest_path),
        })
    return sorted(result, key=lambda x: x["minister_id"])


def build_manifest(*, estate: Path, inquiry_id: str) -> dict:
    sanctum, horus = estate / "Sanctum", estate / "Horus"
    _require(sanctum.is_dir(), "Sanctum repository missing from estate")
    _require(horus.is_dir(), "Horus repository missing from estate")
    _require(isinstance(inquiry_id, str) and inquiry_id.strip(), "inquiry_id is required")

    registry_path = sanctum / "registry/ministers.yaml"
    registry = harness.yaml_load(registry_path.read_text(encoding="utf-8"))
    minister_bindings = _minister_runtime_bindings(sanctum, estate, registry)

    horus_registry = _load_horus_registry(sanctum)
    horus_actual = git_commit(horus)
    horus_pin = horus_registry["pinned_commit"]
    _require(horus_actual == horus_pin, f"Horus checkout {horus_actual} does not match Sanctum pin {horus_pin}")

    adapter_registry = _load_adapter_registry(sanctum)
    sanctum_files = {
        "assembly_spec": _binding(sanctum, "standards/assembly-spec.yaml"),
        "registry": _binding(sanctum, "registry/ministers.yaml"),
        "adapter_registry": _binding(sanctum, ADAPTER_REGISTRY),
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
            "adapter_registry": {**sanctum_files["adapter_registry"], "version": str(adapter_registry.get("version"))},
            "final_judgment_contract": sanctum_files["final_judgment_contract"],
            "proposition_matrix_standard": sanctum_files["proposition_matrix_standard"],
            "ministerial_silence_standard": sanctum_files["ministerial_silence_standard"],
            "source_absence_standard": sanctum_files["source_absence_standard"],
        },
        "horus": {
            "repository": horus_registry["repository"],
            "repository_commit": horus_actual,
            "pinned_commit": horus_pin,
            "registry": {**_binding(sanctum, HORUS_REGISTRY), "version": str(horus_registry.get("version"))},
            "manifest": _binding(horus, horus_registry["manifest_path"]),
            "response_contract": _binding(horus, horus_registry["response_contract"]),
            "acquisition_receipt_contract": _binding(horus, horus_registry["acquisition_receipt_contract"]),
            "principal_source_profile_contract": _binding(horus, horus_registry["principal_source_profile_contract"]),
            "canonical_runtime": _binding(horus, horus_registry["canonical_runtime"]),
            "acquisition_protocol": horus_registry["acquisition_protocol"],
        },
        "ministers": minister_bindings,
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

    horus_registry = _load_horus_registry(sanctum)
    horus_actual = git_commit(horus)
    horus_doc = manifest.get("horus", {})
    _require(horus_actual == horus_registry["pinned_commit"], "live Horus checkout differs from Sanctum Horus pin")
    _require(horus_doc.get("repository") == horus_registry["repository"], "Horus repository mismatch")
    _require(horus_doc.get("repository_commit") == horus_actual, "Horus commit mismatch")
    _require(horus_doc.get("pinned_commit") == horus_registry["pinned_commit"], "Horus pinned_commit mismatch")
    _require(horus_doc.get("acquisition_protocol") == horus_registry["acquisition_protocol"], "Horus acquisition protocol mismatch")
    hr = horus_doc.get("registry", {})
    _require(hr.get("path") == HORUS_REGISTRY, "Horus registry path mismatch")
    _require(str(hr.get("version")) == str(horus_registry.get("version")), "Horus registry version mismatch")
    _require(hr.get("sha256") == sha256_file(sanctum / HORUS_REGISTRY), "Horus registry hash mismatch")

    for key in ["assembly_spec", "registry", "adapter_registry", "final_judgment_contract", "proposition_matrix_standard", "ministerial_silence_standard", "source_absence_standard"]:
        binding = manifest["sanctum"][key]
        _require(binding["sha256"] == sha256_file(sanctum / binding["path"]), f"Sanctum binding changed: {key}")

    adapter_registry = _load_adapter_registry(sanctum)
    _require(manifest["sanctum"]["adapter_registry"].get("path") == ADAPTER_REGISTRY, "adapter registry path mismatch")
    _require(str(manifest["sanctum"]["adapter_registry"].get("version")) == str(adapter_registry.get("version")), "adapter registry version mismatch")

    expected_horus_bindings = {
        "manifest": horus_registry["manifest_path"],
        "response_contract": horus_registry["response_contract"],
        "acquisition_receipt_contract": horus_registry["acquisition_receipt_contract"],
        "principal_source_profile_contract": horus_registry["principal_source_profile_contract"],
        "canonical_runtime": horus_registry["canonical_runtime"],
    }
    for key, expected_path in expected_horus_bindings.items():
        binding = horus_doc.get(key, {})
        _require(binding.get("path") == expected_path, f"Horus {key} path mismatch")
        _require(binding.get("sha256") == sha256_file(horus / expected_path), f"Horus {key} binding changed")

    registry = harness.yaml_load((sanctum / "registry/ministers.yaml").read_text(encoding="utf-8"))
    _require(str(manifest["sanctum"]["registry"].get("version")) == str(registry.get("version")), "registry version mismatch")
    expected_items = _minister_runtime_bindings(sanctum, estate, registry)
    actual_items = manifest.get("ministers", [])
    _require(len(actual_items) == len({m.get("minister_id") for m in actual_items}), "duplicate minister binding in manifest")
    _require(actual_items == expected_items, "minister runtime bindings differ from authoritative registry and adapter overlays")
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
