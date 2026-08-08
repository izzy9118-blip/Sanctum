import pytest

from proposition_matrix import PropositionMatrixError, build_inventory


def forward_package():
    return {
        "record_type": "final_judgment_package",
        "inquiry_id": "INQ-1",
        "minister_id": "strauss",
        "repository": {"full_name": "Strauss", "git_commit": "a" * 40},
        "summary": "Summary",
        "propositions": [],
        "uncertainties": [],
        "silence_semantics_standard": "MINISTERIAL-SILENCE-001",
        "issue_register": [{"issue_id": "ISSUE-1", "issue": "A question"}],
        "issue_states": [{"issue_id": "ISSUE-1", "state": "NOT_ADDRESSED", "proposition_refs": [], "basis": "Not treated", "uncertainty_ref": None}],
    }


def test_presidential_inventory_receives_sovereign_silence_state():
    inv = build_inventory({"strauss": forward_package()})
    assert inv["ministerial_issue_states"][0]["issue_states"][0]["state"] == "NOT_ADDRESSED"


def test_invalid_forward_silence_cannot_reach_president():
    p = forward_package()
    p["issue_states"] = []
    with pytest.raises(PropositionMatrixError, match="silence semantics invalid"):
        build_inventory({"strauss": p})
