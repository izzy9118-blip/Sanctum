import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import universal_dispatch


BASE = Path(__file__).resolve().parents[1]


def test_adopted_overlays_cover_every_established_minister_without_repinning_corpus():
    authoritative, adapters = universal_dispatch._registries()
    established = {
        item["minister_id"]: item
        for item in authoritative["ministers"]
        if item.get("membership_status") == "established"
    }
    bindings = {item["minister_id"]: item for item in adapters["bindings"]}
    assert set(bindings) == set(established) == {"leo-strauss", "xenophon"}
    for minister_id, minister in established.items():
        binding = bindings[minister_id]
        assert binding["repository"] == minister["repository"]
        assert binding["certified_base_commit"] == minister["pinned_commit"]
        assert binding["runtime_overlay_commit"] != minister["pinned_commit"]
        assert binding["runtime_overlay_commit"] != "0" * 40
        assert binding["allowed_overlay_paths"] == ["sanctum_adapter.py"]
        assert binding["protocol"] == "sanctum.adapter.v1"
    assert adapters["status"] == "OWNER_AUTHORIZED_OPERATIONAL_OVERLAYS"
    assert adapters["authority"] == "REPOSITORY_OWNER_DIRECTIVE"


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
