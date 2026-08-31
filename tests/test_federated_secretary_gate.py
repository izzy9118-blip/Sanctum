import json
from pathlib import Path

import pytest

import federated_proving
import secretary_gate


FIXTURE = Path(__file__).parent / "fixtures" / "federated-proving-inquiry.json"


def _inquiry():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_federated_gate_is_bound_to_immutable_inquiry_and_full_roster(tmp_path):
    hub = tmp_path / "Sanctum"
    hub.mkdir()
    checklist, token, ledger, checklist_path, token_path = federated_proving._secretary_gate_for_minister(
        hub=hub,
        inquiry=_inquiry(),
        inquiry_path=FIXTURE.resolve(),
        minister_id="xenophon",
    )

    assert checklist_path.is_file()
    assert token_path.is_file()
    assert {item["principal_id"] for item in checklist["roster"]} == {"ukraine", "russian-federation"}
    assert token["checklist_sha256"] == secretary_gate.checklist_digest(checklist)
    assert ledger.enter("investigative_query")["stage"] == "investigative_query"


def test_federated_model_boundary_refuses_wrong_stage_receipt():
    inquiry = _inquiry()
    checklist = {
        "record_type": secretary_gate.CHECKLIST_RECORD_TYPE,
        "gate_standard": secretary_gate.GATE_STANDARD,
    }
    # The boundary verifies before either fixture output or a live provider call.
    with pytest.raises(secretary_gate.SecretaryGateError):
        federated_proving._call_model(
            {}, "prompt", fixture=True, stage="investigative_query",
            minister={"minister_id": "xenophon"}, inquiry=inquiry,
            prepared={"repository_commit": "0" * 40}, exchanges=[],
            pass_token=checklist, stage_receipt={},
        )
