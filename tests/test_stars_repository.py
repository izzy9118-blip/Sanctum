import json
import subprocess
from pathlib import Path

import pytest

import harness
from stars_repository import StarsRepositoryError, build_binding


PIN = "44d05c09aa75a043497930863abf82364dd8ab6a"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _registry(commit: str) -> str:
    return f"""record_type: sanctum_stars_registry
version: 1.0.0
status: OWNER_AUTHORIZED_READ_ONLY_RESEARCH_CORPUS
repository: izzy9118-blip/Stars
pinned_commit: "{commit}"
role: READ_ONLY_RESEARCH_PROVENANCE_CORPUS
consumption_mode: EXPLICIT_CONTEXT_ONLY_REQUIRES_SEPARATE_EVIDENCE_ADMISSION
governing_method: sources/SOURCE-WITNESS-METHOD.md
artifact_roots:
  - stars
  - narratives
  - sources
admission_policy:
  structured_star_status: SOURCE_REPOSITORY_INTERNAL_STATE_NOT_SANCTUM_TRUTH_CERTIFICATION
  contextual_use: ALLOWED_ONLY_WHEN_EXPLICITLY_SELECTED_AND_PIN_BOUND
  live_evidence_use: PROHIBITED_WITHOUT_SEPARATE_HORUS_ACQUISITION_AND_INQUIRY_ADMISSION
  local_source_paths: LOCATOR_METADATA_NOT_PORTABLE_ACQUIRED_EVIDENCE
  automatic_prompt_injection: PROHIBITED
certification: NONE_SELF_CERTIFICATION_PROHIBITED
"""


def _estate(tmp_path: Path) -> tuple[Path, Path, Path]:
    estate = tmp_path / "estate"
    sanctum = estate / "Sanctum"
    stars = estate / "Stars"
    (sanctum / "registry").mkdir(parents=True)
    (stars / "stars").mkdir(parents=True)
    (stars / "narratives").mkdir()
    (stars / "sources").mkdir()
    (stars / "stars/STAR-TEST-001.yaml").write_text(
        "star_id: STAR-TEST-001\nname: Test Star\nstatus: DRAFT\n",
        encoding="utf-8",
    )
    (stars / "narratives/STAR-TEST-001.md").write_text("# Test Star\n", encoding="utf-8")
    (stars / "sources/SOURCE-WITNESS-METHOD.md").write_text("# Method\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main", str(stars)], check=True, capture_output=True, text=True)
    _git(stars, "config", "user.email", "stars-test@example.invalid")
    _git(stars, "config", "user.name", "Stars Test")
    _git(stars, "add", ".")
    _git(stars, "commit", "-m", "fixture")
    commit = _git(stars, "rev-parse", "HEAD")
    (sanctum / "registry/stars.yaml").write_text(_registry(commit), encoding="utf-8")
    return estate, sanctum, stars


def test_build_binding_covers_all_tracked_roots_and_catalog(tmp_path):
    estate, _, _ = _estate(tmp_path)
    binding = build_binding(estate=estate)

    assert binding["repository"] == "izzy9118-blip/Stars"
    assert binding["repository_commit"] == binding["pinned_commit"]
    assert binding["artifact_roots"] == ["stars", "narratives", "sources"]
    assert binding["tracked_file_count"] == 3
    assert len(binding["tracked_inventory_sha256"]) == 64
    assert binding["catalog"] == [{
        "star_id": "STAR-TEST-001",
        "name": "Test Star",
        "status": "DRAFT",
        "path": "stars/STAR-TEST-001.yaml",
        "sha256": binding["catalog"][0]["sha256"],
    }]


def test_build_binding_rejects_dirty_stars_checkout(tmp_path):
    estate, _, stars = _estate(tmp_path)
    (stars / "stars/STAR-TEST-001.yaml").write_text(
        "star_id: STAR-TEST-001\nname: Changed\nstatus: FACT\n",
        encoding="utf-8",
    )

    with pytest.raises(StarsRepositoryError, match="uncommitted or untracked"):
        build_binding(estate=estate)


def test_build_binding_rejects_wrong_pin(tmp_path):
    estate, sanctum, _ = _estate(tmp_path)
    (sanctum / "registry/stars.yaml").write_text(_registry("1" * 40), encoding="utf-8")

    with pytest.raises(StarsRepositoryError, match="does not match Sanctum pin"):
        build_binding(estate=estate)


def test_authoritative_registry_prohibits_automatic_or_live_evidence_use():
    registry = harness.yaml_load(Path("registry/stars.yaml").read_text(encoding="utf-8"))

    assert registry["pinned_commit"] == PIN
    assert registry["admission_policy"]["automatic_prompt_injection"] == "PROHIBITED"
    assert registry["admission_policy"]["live_evidence_use"] == "PROHIBITED_WITHOUT_SEPARATE_HORUS_ACQUISITION_AND_INQUIRY_ADMISSION"


def test_constitutional_environment_schema_requires_stars_binding():
    schema = json.loads(Path("contracts/constitutional-environment.schema.json").read_text(encoding="utf-8"))

    assert schema["$id"] == "urn:sanctum:constitutional-environment:1.3.0"
    assert "stars" in schema["required"]
    assert schema["properties"]["stars"]["properties"]["repository"]["const"] == "izzy9118-blip/Stars"
    assert "stars_repository_boundary" in schema["properties"]["sanctum"]["required"]
