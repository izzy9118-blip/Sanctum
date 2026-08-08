import json
from pathlib import Path

import harness
from jsonschema import Draft202012Validator

BASE = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((BASE / path).read_text(encoding="utf-8"))


def load_yaml(path):
    return harness.yaml_load((BASE / path).read_text(encoding="utf-8"))


def test_historical_root_report_contract_remains_v1_3_0():
    assert load("ministerial-report.schema.json")["$id"] == "urn:sanctum:federation:ministerial-report:1.3.0"


def test_adversarial_forward_contract_remains_v1_5_0():
    assert load("federation/contracts/ministerial-report.schema.v1.5.0.json")["$id"] == "urn:sanctum:federation:ministerial-report:1.5.0"


def test_genealogy_forward_contract_is_v1_6_0():
    assert load("federation/contracts/ministerial-report.schema.v1.6.0.json")["$id"] == "urn:sanctum:federation:ministerial-report:1.6.0"


def test_genealogy_assembly_spec_is_preserved_as_v1_4_0():
    spec = load_yaml("standards/assembly-spec.v1.4.0.yaml")
    assert str(spec["version"]) == "1.4.0"
    assert spec["predecessor"]["path"] == "standards/assembly-spec.v1.3.0.yaml"


def test_governing_spec_advances_without_rewriting_genealogy_predecessor():
    spec = load_yaml("standards/assembly-spec.yaml")
    assert str(spec["version"]) == "1.5.0"
    assert spec["predecessor"]["path"] == "standards/assembly-spec.v1.4.0.yaml"


def test_adversarial_assembly_spec_is_preserved_as_v1_3_0():
    spec = load_yaml("standards/assembly-spec.v1.3.0.yaml")
    assert str(spec["version"]) == "1.3.0"


def test_final_judgment_contract_accepts_typed_horus_genealogy():
    schema = load("contracts/final-judgment-package.schema.json")
    document = {
        "record_type": "final_judgment_package",
        "inquiry_id": "INQ-1",
        "minister_id": "xenophon",
        "repository": {"full_name": "Xenophon", "git_commit": "a" * 40},
        "summary": "A summary.",
        "propositions": [{
            "proposition_id": "PROP-001",
            "kind": "documented_finding",
            "claim": "A documented claim.",
            "provisional_disposition": "retained",
            "genealogy": [{
                "origin": "horus_exchange",
                "query_id": "MHQ-INQ-001",
                "exchange_sha256": "b" * 64,
                "source_ref": "SRC-1",
                "document_identity": "Primary instrument",
                "locator": "section 1",
                "source_sha256": None
            }]
        }],
        "uncertainties": []
    }
    Draft202012Validator(schema).validate(document)


def test_final_judgment_contract_rejects_substantive_claim_without_genealogy():
    schema = load("contracts/final-judgment-package.schema.json")
    document = {
        "record_type": "final_judgment_package",
        "inquiry_id": "INQ-1",
        "minister_id": "xenophon",
        "repository": {"full_name": "Xenophon", "git_commit": "a" * 40},
        "summary": "A summary.",
        "propositions": [{
            "proposition_id": "PROP-001",
            "kind": "documented_finding",
            "claim": "An ungrounded claim.",
            "provisional_disposition": "retained",
            "genealogy": []
        }],
        "uncertainties": []
    }
    errors = list(Draft202012Validator(schema).iter_errors(document))
    assert errors
