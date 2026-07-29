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


def test_envelope_hash_and_universal_dispatch_match():
    envelope = load_yaml(INQ / "envelope.yaml")
    receipt = load_yaml(INQ / "dispatch-receipt.yaml")
    expected = hashlib.sha256(envelope["question"].encode("utf-8")).hexdigest()
    assert envelope["integrity"]["hash_scope"] == "question_utf8_for_proving_dispatch"
    assert envelope["integrity"]["envelope_sha256"] == expected
    assert receipt["envelope_sha256"] == expected
    registry = load_yaml(ROOT / "registry" / "ministers.yaml")
    established = {m["minister_id"] for m in registry["ministers"] if m.get("membership_status") == "established"}
    dispatched = {m["minister_id"] for m in receipt["dispatched_ministers"]}
    assert dispatched == established


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
