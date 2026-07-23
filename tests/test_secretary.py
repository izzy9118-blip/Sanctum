from __future__ import annotations

from copy import deepcopy

from sanctum_federation.contracts import ContractSet
from sanctum_federation.integrity import object_sha256_without_integrity
from sanctum_federation.registry import RegistrySnapshot
from sanctum_federation.secretary import SecretaryValidator

from .fixtures.stub_adapter import build_report
from .helpers import (
    SANCTUM_ROOT,
    custos_root,
    envelope,
    git,
    json_bytes,
)


def _context():
    contracts = ContractSet.load(SANCTUM_ROOT)
    registry = RegistrySnapshot.load(SANCTUM_ROOT, contracts)
    entry = registry.entries[0]
    value = envelope(registry)
    validator = SecretaryValidator(
        contracts,
        registry,
        secretary_actor_id="SANCTUM-CONSTITUTIONAL-SECRETARY",
        repository_roots={entry.repository_full_name: custos_root()},
        sanctum_commit=git(SANCTUM_ROOT, "rev-parse", "HEAD"),
    )
    return contracts, registry, entry, value, validator


def test_valid_report_gets_separate_noncertifying_validation():
    contracts, _, entry, value, validator = _context()
    report = build_report(
        custos_root(),
        entry.repository_commit,
        value,
    )

    result = validator.validate_report_bytes(
        value,
        json_bytes(report),
        entry,
    )

    assert result.validated is True
    assert result.record["outcome"] == "VALIDATED"
    assert result.record["certification_status"] == "NOT_CERTIFIED"
    assert (
        result.record["constitutional_effect"]
        == "PROVENANCE_VALIDATION_ONLY"
    )
    assert all(
        check["status"] == "PASS" for check in result.record["checks"]
    )
    contracts.validate_secretary_record(result.record)
    assert report["secretary_validation_status"] == "NOT_YET_VALIDATED"


def test_stale_report_self_hash_is_rejected():
    _, _, entry, value, validator = _context()
    report = build_report(
        custos_root(),
        entry.repository_commit,
        value,
    )
    report["findings"][0]["statement"] = "Altered after submission."

    result = validator.validate_report_bytes(
        value,
        json_bytes(report),
        entry,
    )

    assert result.validated is False
    checks = {item["check_id"]: item for item in result.record["checks"]}
    assert checks["REPORT_INTEGRITY"]["status"] == "FAIL"
    assert result.record["preservation_status"] == (
        "QUARANTINED_REJECTED_REPORT"
    )


def test_false_evidence_hash_is_rejected_after_valid_report_rehash():
    _, _, entry, value, validator = _context()
    report = build_report(
        custos_root(),
        entry.repository_commit,
        value,
        tamper_evidence=True,
    )

    result = validator.validate_report_bytes(
        value,
        json_bytes(report),
        entry,
    )

    checks = {item["check_id"]: item for item in result.record["checks"]}
    assert checks["REPORT_INTEGRITY"]["status"] == "PASS"
    assert checks["EVIDENCE_GIT_FIXITY"]["status"] == "FAIL"
    assert result.validated is False


def test_unresolved_finding_reference_is_rejected():
    _, _, entry, value, validator = _context()
    report = build_report(
        custos_root(),
        entry.repository_commit,
        value,
    )
    report["findings"][0]["evidence_refs"] = ["EVR-FED-DOES-NOT-EXIST"]
    report["integrity"]["report_sha256"] = (
        object_sha256_without_integrity(report)
    )

    result = validator.validate_report_bytes(
        value,
        json_bytes(report),
        entry,
    )

    checks = {item["check_id"]: item for item in result.record["checks"]}
    assert checks["REFERENCE_INTEGRITY"]["status"] == "FAIL"
    assert result.validated is False


def test_malformed_json_produces_a_quarantined_validation_record():
    contracts, _, entry, value, validator = _context()
    result = validator.validate_report_bytes(
        value,
        b'{"report_id": "MREP-BROKEN", "report_id": "DUPLICATE"}',
        entry,
    )

    assert result.report is None
    assert result.record["outcome"] == "REJECTED"
    assert result.record["checks"][0]["check_id"] == "REPORT_JSON"
    assert result.record["checks"][0]["status"] == "FAIL"
    assert all(
        item["status"] == "SKIPPED"
        for item in result.record["checks"][1:]
    )
    contracts.validate_secretary_record(result.record)


def test_authentic_failed_minister_report_validates_without_becoming_success():
    _, _, entry, value, validator = _context()
    report = build_report(
        custos_root(),
        entry.repository_commit,
        value,
        failed=True,
    )

    result = validator.validate_report_bytes(
        value,
        json_bytes(report),
        entry,
    )

    assert result.validated is True
    assert result.record["report_termination_status"] == "FAILED"
    assert result.record["certification_status"] == "NOT_CERTIFIED"
