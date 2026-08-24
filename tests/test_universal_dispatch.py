import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import universal_dispatch


BASE = Path(__file__).resolve().parents[1]


def test_candidate_bindings_cover_every_established_minister_without_repinning():
    authoritative, candidates = universal_dispatch._registries()
    established = {
        item["minister_id"]: item
        for item in authoritative["ministers"]
        if item.get("membership_status") == "established"
    }
    bindings = {item["minister_id"]: item for item in candidates["bindings"]}
    assert set(bindings) == set(established) == {"leo-strauss", "xenophon"}
    for minister_id, minister in established.items():
        binding = bindings[minister_id]
        assert binding["repository"] == minister["repository"]
        assert binding["authoritative_registry_pin_unchanged"] == minister["pinned_commit"]
        assert binding["candidate_commit"] != "0" * 40
        assert binding["protocol"] == "sanctum.adapter.v1"
    assert candidates["status"] == "CANDIDATE_PENDING_OWNER_ADOPTION"
    assert candidates["authority"] == "NONE"


def test_universal_request_contract_accepts_common_transport():
    schema = json.loads((BASE / universal_dispatch.CONTRACT).read_text(encoding="utf-8"))
    request = {
        "record_type": "sanctum_adapter_request",
        "protocol": "sanctum.adapter.v1",
        "inquiry_id": "INQ-TEST-001",
        "minister_id": "leo-strauss",
        "question": "What is the problem?",
        "common_briefing": {"sha256": "a" * 64},
        "repository_pin": {
            "repository": "izzy9118-blip/Strauss",
            "commit": "b" * 40,
        },
    }
    errors = list(Draft202012Validator(schema).iter_errors(request))
    assert errors == []


def test_universal_request_contract_rejects_moving_ref():
    schema = json.loads((BASE / universal_dispatch.CONTRACT).read_text(encoding="utf-8"))
    request = {
        "record_type": "sanctum_adapter_request",
        "protocol": "sanctum.adapter.v1",
        "inquiry_id": "INQ-TEST-001",
        "minister_id": "xenophon",
        "question": "What is the problem?",
        "common_briefing": {"sha256": "a" * 64},
        "repository_pin": {
            "repository": "izzy9118-blip/Xenophon",
            "commit": "main",
        },
    }
    errors = list(Draft202012Validator(schema).iter_errors(request))
    assert errors


def test_prepare_requires_one_immutable_briefing_hash(tmp_path):
    with pytest.raises(universal_dispatch.UniversalDispatchError):
        universal_dispatch.prepare(
            tmp_path,
            {
                "inquiry_id": "INQ-TEST-001",
                "question": "What is the problem?",
                "common_briefing": {"sha256": "short"},
            },
        )
