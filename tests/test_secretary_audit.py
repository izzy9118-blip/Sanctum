import hashlib
import json
from pathlib import Path

import pytest

import secretary_audit
import secretary_gate
from tests.test_secretary_gate import CONFORMING_DISPATCH, polity_checklist


def test_canonical_hash_is_format_independent():
    a = {"b": 2, "a": 1}
    b = json.loads('{\n  "a": 1,\n  "b": 2\n}')
    assert secretary_audit._canonical_sha256(a) == secretary_audit._canonical_sha256(b)


def test_inside_rejects_escape(tmp_path):
    hub = tmp_path / "Sanctum"
    hub.mkdir()
    assert secretary_audit._inside(hub, hub / "reports" / "x.json")
    assert not secretary_audit._inside(hub, tmp_path / "Horus" / "x.json")


def test_artifact_path_rejects_escape(tmp_path):
    hub = tmp_path / "Sanctum"
    hub.mkdir()
    with pytest.raises(secretary_audit.SecretaryAuditError):
        secretary_audit._artifact_path(hub, "../Horus/fake.json", hub / "fallback.json")


def test_load_json_rejects_missing(tmp_path):
    with pytest.raises(secretary_audit.SecretaryAuditError):
        secretary_audit._load_json(tmp_path / "missing.json")


def test_exchange_records_rejects_changed_binding(tmp_path):
    hub = tmp_path / "Sanctum"
    hub.mkdir()
    req = {"query_id": "MHQ-1"}
    res = {"query_id": "MHQ-1", "sources_used": [], "records_returned": []}
    (hub / "req.json").write_text(json.dumps(req), encoding="utf-8")
    (hub / "res.json").write_text(json.dumps(res), encoding="utf-8")
    record = {"horus_exchanges": [
        {"exchange_kind": "investigative", "query_id": "MHQ-1", "exchange_sha256": "0" * 64,
         "request_path": "req.json", "response_path": "res.json"},
        {"exchange_kind": "adversarial", "query_id": "MHQ-1", "exchange_sha256": "0" * 64,
         "request_path": "req.json", "response_path": "res.json"},
    ]}
    with pytest.raises(secretary_audit.SecretaryAuditError, match="exchange hash"):
        secretary_audit._exchange_records(record, hub)


def _gated_round(hub: Path, dispatch: str = CONFORMING_DISPATCH) -> dict:
    """A round record as the runner writes it once the gate has been opened."""
    checklist = polity_checklist()
    token = secretary_gate.open_gate(checklist)
    secretary_gate.write_json(hub / "checklist.json", checklist)
    secretary_gate.write_json(hub / "token.json", token)
    (hub / "dispatch.md").write_text(dispatch, encoding="utf-8")
    return {
        "secretary_gate": {
            "checklist_path": "checklist.json",
            "checklist_sha256": token["checklist_sha256"],
            "token_path": "token.json",
            "stages_completed": list(secretary_gate.REQUIRED_SEQUENCE),
            "dispatch_path": "dispatch.md",
            "dispatch_sha256": hashlib.sha256(dispatch.encode("utf-8")).hexdigest(),
        }
    }


def test_gate_record_reverifies_the_run_from_disk(tmp_path):
    hub = tmp_path / "Sanctum"
    hub.mkdir()
    gate = secretary_audit._gate_record(_gated_round(hub), hub)
    assert gate["dispatch_audit"]["failures"] == []


def test_an_ungated_run_cannot_be_audited(tmp_path):
    hub = tmp_path / "Sanctum"
    hub.mkdir()
    with pytest.raises(secretary_audit.SecretaryAuditError, match="never gated"):
        secretary_audit._gate_record({"record_type": "sovereign_genealogical_round"}, hub)


def test_a_dispatch_swapped_after_the_run_is_caught(tmp_path):
    hub = tmp_path / "Sanctum"
    hub.mkdir()
    record = _gated_round(hub)
    (hub / "dispatch.md").write_text(CONFORMING_DISPATCH + "\nan added paragraph\n", encoding="utf-8")
    with pytest.raises(secretary_audit.SecretaryAuditError, match="not the dispatch the round recorded"):
        secretary_audit._gate_record(record, hub)


def test_a_skipped_stage_fails_the_run_audit(tmp_path):
    hub = tmp_path / "Sanctum"
    hub.mkdir()
    record = _gated_round(hub)
    record["secretary_gate"]["stages_completed"] = ["investigative_query", "final_judgment"]
    with pytest.raises(secretary_audit.SecretaryAuditError, match="do not perform the constitutional sequence"):
        secretary_audit._gate_record(record, hub)
