from pathlib import Path
import hashlib
import json
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
INQ = ROOT / "inquiries" / "0001"


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate(schema_name, document):
    schema = json.loads((ROOT / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(document)


def test_all_four_proving_dispatch_artifacts_validate():
    envelope = load_yaml(INQ / "envelope.yaml")
    receipt = load_yaml(INQ / "dispatch-receipt.yaml")
    report = load_yaml(INQ / "ministerial-report-leo-strauss.yaml")
    secretary = load_yaml(INQ / "secretary-validation-record.yaml")
    validate("inquiry-envelope.schema.json", envelope)
    validate("dispatch-receipt.schema.json", receipt)
    validate("ministerial-report.schema.json", report)
    validate("secretary-validation-record.schema.json", secretary)


def test_envelope_hash_and_historical_universal_dispatch_match():
    envelope = load_yaml(INQ / "envelope.yaml")
    receipt = load_yaml(INQ / "dispatch-receipt.yaml")
    expected = hashlib.sha256(envelope["question"].encode("utf-8")).hexdigest()
    assert envelope["integrity"]["hash_scope"] == "question_utf8_for_proving_dispatch"
    assert envelope["integrity"]["envelope_sha256"] == expected
    assert receipt["envelope_sha256"] == expected

    # Inquiry 0001 is an immutable historical dispatch. Its universal scope is
    # determined by the exact registry commit and version recorded in the receipt,
    # not by ministers established after that dispatch occurred.
    assert receipt["registry_state"]["commit"] == "84f0b2d73e0fef153da004b2ff1e8136f57988a8"
    assert receipt["registry_state"]["version"] == "2.8.0"
    assert receipt["registry_state"]["participation_policy"] == "universal"
    dispatched = {item["minister_id"] for item in receipt["dispatched_ministers"]}
    assert dispatched == {"leo-strauss"}

    # Current registry expansion must not silently rewrite completed inquiry history.
    current_registry = load_yaml(ROOT / "registry" / "ministers.yaml")
    current_established = {
        item["minister_id"]
        for item in current_registry["ministers"]
        if item.get("membership_status") == "established"
    }
    assert current_established == {"leo-strauss", "xenophon"}


def test_report_and_dispatch_are_owner_certified_without_presidential_synthesis():
    report = load_yaml(INQ / "ministerial-report-leo-strauss.yaml")
    secretary = load_yaml(INQ / "secretary-validation-record.yaml")
    certification = load_yaml(INQ / "owner-certification.yaml")
    assert report["report_status"] == "OWNER_CERTIFIED_MINISTERIAL_REPORT"
    assert report["sovereign_validation"]["result"] == "SOVEREIGN_MINISTERIAL_VALIDATION_PASSED"
    assert report["certification_status"] == "OWNER_CERTIFIED"
    assert report["termination"]["presidential_synthesis"] == "NOT_PERFORMED"
    assert secretary["outcome"] == "validated"
    assert secretary["presidential_synthesis"] == "NOT_OCCURRED"
    assert secretary["certification_status"] == "OWNER_CERTIFIED"
    assert certification["decision"] == "OWNER_CERTIFIED"
    assert certification["preservation"]["artificial_intelligence_self_certification"] is False
    assert certification["preservation"]["presidential_synthesis_performed"] is False
