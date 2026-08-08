import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def base_report():
    commit = "a" * 40
    return {
        "record_type": "ministerial_report",
        "id": "MREP-ADV-001",
        "report_id": "MREP-ADV-001",
        "report_status": "DRAFT_PENDING_MINISTER_REPOSITORY_VALIDATION",
        "inquiry_ref": {"ref": "INQ-ADV-001"},
        "minister": {"actor": "xenophon", "manifest_commit": commit},
        "mode": "reasoned",
        "repository": {"full_name": "izzy9118-blip/Xenophon", "git_commit": commit},
        "governing_manifest": {"path": "manifest.yaml", "version": "1.70.0"},
        "provisional_judgment": {
            "path": "reports/test.provisional.json",
            "sha256": "b" * 64,
            "proposition_count": 1,
        },
        "horus_exchanges": [
            {
                "exchange_kind": "investigative",
                "query_id": "MHQ-ADV-001",
                "request_path": "exchanges/investigative.request.json",
                "response_path": "exchanges/investigative.response.json",
                "exchange_sha256": "c" * 64,
                "response_status": "GATHERED",
                "unfilled_request_count": 0,
            },
            {
                "exchange_kind": "adversarial",
                "query_id": "MHAQ-ADV-001",
                "request_path": "exchanges/adversarial.request.json",
                "response_path": "exchanges/adversarial.response.json",
                "exchange_sha256": "d" * 64,
                "response_status": "PARTIALLY_GATHERED",
                "unfilled_request_count": 1,
            },
        ],
        "evidence": [
            {
                "witness_id": "XEN-WIT-PRI-001",
                "source_id": "XEN-SRC-PRI-001",
                "repository_commit": commit,
                "path": "corpus/witness.yaml",
            }
        ],
        "propositions": [{"kind": "supported_inference", "claim": "A tested claim."}],
        "uncertainties": ["One adversarial information need remains unfilled."],
        "termination": {"status": "COMPLETE_WITH_PRESERVED_UNCERTAINTY"},
        "provenance": {},
        "certification_status": "PENDING_OWNER_CERTIFICATION",
    }


def test_historical_root_contract_remains_v1_3_0():
    assert load("ministerial-report.schema.json")["$id"] == (
        "urn:sanctum:federation:ministerial-report:1.3.0"
    )


def test_predecessor_v1_4_contract_is_preserved():
    assert load("federation/contracts/ministerial-report.schema.v1.4.0.json")["$id"] == (
        "urn:sanctum:federation:ministerial-report:1.4.0"
    )


def test_forward_adversarial_contract_accepts_both_exchange_kinds():
    schema = load("federation/contracts/ministerial-report.schema.v1.5.0.json")
    Draft202012Validator(schema).validate(base_report())


def test_forward_contract_rejects_missing_adversarial_exchange():
    schema = load("federation/contracts/ministerial-report.schema.v1.5.0.json")
    report = base_report()
    report["horus_exchanges"] = report["horus_exchanges"][:1]
    errors = list(Draft202012Validator(schema).iter_errors(report))
    assert errors


def test_forward_contract_rejects_mislabeled_adversarial_query_id():
    schema = load("federation/contracts/ministerial-report.schema.v1.5.0.json")
    report = base_report()
    report["horus_exchanges"][1]["query_id"] = "MHQ-WRONG-PREFIX"
    errors = list(Draft202012Validator(schema).iter_errors(report))
    assert errors
