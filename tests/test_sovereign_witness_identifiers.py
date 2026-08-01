from pathlib import Path
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]


def schema():
    return json.loads((ROOT / "ministerial-report.schema.json").read_text(encoding="utf-8"))


def base_report(witness_id: str):
    commit = "a" * 40
    return {
        "record_type": "ministerial_report",
        "id": "MREP-TEST-001",
        "report_id": "MREP-TEST-001",
        "report_status": "DRAFT_PENDING_MINISTER_REPOSITORY_VALIDATION",
        "inquiry_ref": {"ref": "INQ-TEST-001"},
        "minister": {"actor": "xenophon", "manifest_commit": commit},
        "mode": "reasoned",
        "repository": {"full_name": "izzy9118-blip/Xenophon", "git_commit": commit},
        "governing_manifest": {"path": "manifest.yaml", "version": "1.69.0"},
        "evidence": [{
            "witness_id": witness_id,
            "source_id": "XEN-SRC-PRI-001",
            "repository_commit": commit,
            "path": "corpus/witnesses/xenophon-anabasis-dakyns.yaml",
        }],
        "propositions": [{"kind": "documented_finding", "claim": "A test claim."}],
        "uncertainties": ["A question remains open."],
        "termination": {"status": "COMPLETE_WITH_PRESERVED_UNCERTAINTY"},
        "provenance": {},
        "certification_status": "PENDING_OWNER_CERTIFICATION",
    }


def test_contract_version_is_1_3_0():
    assert schema()["$id"] == "urn:sanctum:federation:ministerial-report:1.3.0"


def test_repository_native_xenophon_witness_is_valid():
    Draft202012Validator(schema()).validate(base_report("XEN-WIT-PRI-001"))


def test_existing_corpus_witness_is_still_valid():
    Draft202012Validator(schema()).validate(base_report("CORPUS-WIT-001"))


def test_unstructured_witness_identifier_is_rejected():
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(base_report("witness-one"))
