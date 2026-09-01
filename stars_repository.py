#!/usr/bin/env python3
"""Validate and bind the read-only Stars research corpus into a Sanctum estate."""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath

import harness


REGISTRY_PATH = "registry/stars.yaml"
REPOSITORY = "izzy9118-blip/Stars"
ROLE = "READ_ONLY_RESEARCH_PROVENANCE_CORPUS"
CONSUMPTION_MODE = "EXPLICIT_CONTEXT_ONLY_REQUIRES_SEPARATE_EVIDENCE_ADMISSION"
CERTIFICATION = "NONE_SELF_CERTIFICATION_PROHIBITED"
ARTIFACT_ROOTS = ["stars", "narratives", "sources"]
GOVERNING_METHOD = "sources/SOURCE-WITNESS-METHOD.md"


class StarsRepositoryError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StarsRepositoryError(message)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _sha256(path: Path) -> str:
    _require(path.is_file(), f"required Stars file missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _binding(base: Path, relpath: str) -> dict:
    return {"path": relpath, "sha256": _sha256(base / relpath)}


def _safe_relpath(value: object, *, label: str) -> str:
    _require(isinstance(value, str) and value, f"{label} must be a non-empty path")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and ".." not in path.parts, f"unsafe {label}: {value}")
    return value


def load_registry(sanctum: Path) -> dict:
    path = sanctum / REGISTRY_PATH
    _require(path.is_file(), f"Stars registry missing: {path}")
    registry = harness.yaml_load(path.read_text(encoding="utf-8"))
    _require(registry.get("record_type") == "sanctum_stars_registry", "wrong Stars registry record_type")
    _require(registry.get("repository") == REPOSITORY, "Stars registry repository mismatch")
    _require(registry.get("status") == "OWNER_AUTHORIZED_READ_ONLY_RESEARCH_CORPUS", "Stars registry is not authorized")
    _require(registry.get("role") == ROLE, "Stars registry role mismatch")
    _require(registry.get("consumption_mode") == CONSUMPTION_MODE, "Stars consumption mode mismatch")
    pin = registry.get("pinned_commit", "")
    _require(isinstance(pin, str) and re.fullmatch(r"[0-9a-f]{40}", pin) is not None, "Stars pinned_commit is invalid")
    roots = registry.get("artifact_roots")
    _require(roots == ARTIFACT_ROOTS, "Stars artifact roots differ from the constitutional allowlist")
    _require(registry.get("governing_method") == GOVERNING_METHOD, "Stars governing method mismatch")
    policy = registry.get("admission_policy") or {}
    _require(policy.get("structured_star_status") == "SOURCE_REPOSITORY_INTERNAL_STATE_NOT_SANCTUM_TRUTH_CERTIFICATION", "Stars status semantics mismatch")
    _require(policy.get("contextual_use") == "ALLOWED_ONLY_WHEN_EXPLICITLY_SELECTED_AND_PIN_BOUND", "Stars contextual-use policy mismatch")
    _require(policy.get("live_evidence_use") == "PROHIBITED_WITHOUT_SEPARATE_HORUS_ACQUISITION_AND_INQUIRY_ADMISSION", "Stars live-evidence policy mismatch")
    _require(policy.get("local_source_paths") == "LOCATOR_METADATA_NOT_PORTABLE_ACQUIRED_EVIDENCE", "Stars local-path policy mismatch")
    _require(policy.get("automatic_prompt_injection") == "PROHIBITED", "Stars automatic-injection policy mismatch")
    _require(registry.get("certification") == CERTIFICATION, "Stars registry may not self-certify truth or completeness")
    return registry


def _repository_commit(repo: Path) -> str:
    _require((repo / ".git").exists(), f"not a git checkout: {repo}")
    result = _git(repo, "rev-parse", "HEAD")
    commit = result.stdout.strip()
    _require(result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", commit) is not None, f"invalid Stars commit: {commit}")
    return commit


def _tracked_files(repo: Path) -> list[str]:
    result = _git(repo, "ls-files", "--", *ARTIFACT_ROOTS)
    _require(result.returncode == 0, "cannot enumerate tracked Stars artifacts")
    files = sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
    _require(files, "Stars repository contains no tracked artifacts")
    for relpath in files:
        _safe_relpath(relpath, label="tracked Stars artifact")
        _require(any(relpath == root or relpath.startswith(root + "/") for root in ARTIFACT_ROOTS), f"Stars artifact escapes allowed roots: {relpath}")
        _require((repo / relpath).is_file(), f"tracked Stars artifact missing from checkout: {relpath}")
    return files


def _inventory(repo: Path, files: list[str]) -> str:
    digest = hashlib.sha256()
    for relpath in files:
        digest.update(relpath.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(repo / relpath)))
        digest.update(b"\n")
    return digest.hexdigest()


def _top_level_scalar(path: Path, key: str) -> str:
    prefix = key + ":"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            _require(value, f"empty {key} in {path}")
            return value
    raise StarsRepositoryError(f"missing top-level {key} in {path}")


def _catalog(repo: Path, files: list[str]) -> list[dict]:
    star_files = [path for path in files if re.fullmatch(r"stars/STAR-[A-Z0-9-]+\.yaml", path)]
    _require(star_files, "Stars repository contains no structured Star records")
    catalog = []
    seen = set()
    for relpath in star_files:
        path = repo / relpath
        star_id = _top_level_scalar(path, "star_id")
        _require(star_id == path.stem, f"Star identity does not match filename: {relpath}")
        _require(star_id not in seen, f"duplicate Star identity: {star_id}")
        seen.add(star_id)
        catalog.append({
            "star_id": star_id,
            "name": _top_level_scalar(path, "name"),
            "status": _top_level_scalar(path, "status"),
            "path": relpath,
            "sha256": _sha256(path),
        })
    return sorted(catalog, key=lambda item: item["star_id"])


def build_binding(*, estate: Path) -> dict:
    sanctum = estate / "Sanctum"
    repo = estate / "Stars"
    _require(sanctum.is_dir(), "Sanctum repository missing from estate")
    _require(repo.is_dir(), "Stars repository missing from estate")
    registry = load_registry(sanctum)
    actual = _repository_commit(repo)
    _require(actual == registry["pinned_commit"], f"Stars checkout {actual} does not match Sanctum pin {registry['pinned_commit']}")
    status = _git(repo, "status", "--porcelain", "--untracked-files=all")
    _require(status.returncode == 0, "cannot inspect Stars checkout state")
    _require(not status.stdout.strip(), "Stars checkout contains uncommitted or untracked files")
    files = _tracked_files(repo)
    return {
        "repository": REPOSITORY,
        "repository_commit": actual,
        "pinned_commit": registry["pinned_commit"],
        "registry": {
            **_binding(sanctum, REGISTRY_PATH),
            "version": str(registry.get("version")),
        },
        "role": ROLE,
        "consumption_mode": CONSUMPTION_MODE,
        "governing_method": _binding(repo, GOVERNING_METHOD),
        "artifact_roots": list(ARTIFACT_ROOTS),
        "tracked_file_count": len(files),
        "tracked_inventory_sha256": _inventory(repo, files),
        "catalog": _catalog(repo, files),
        "certification": CERTIFICATION,
    }


def validate_binding(binding: dict, *, estate: Path) -> dict:
    _require(isinstance(binding, dict), "Stars binding must be an object")
    expected = build_binding(estate=estate)
    _require(binding == expected, "Stars binding differs from the pinned repository and registry")
    return binding
