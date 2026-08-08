import json
from pathlib import Path

import pytest

import secretary_audit


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
