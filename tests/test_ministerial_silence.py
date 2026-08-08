import pytest

from ministerial_silence import MinisterialSilenceError, issue_state_map, validate_silence_semantics


def package(state="AFFIRMED", refs=None, basis="grounded", uncertainty_ref=None):
    if refs is None:
        refs = ["PROP-1"] if state in {"AFFIRMED", "REJECTED"} else []
    p = {
        "silence_semantics_standard": "MINISTERIAL-SILENCE-001",
        "propositions": [{"proposition_id": "PROP-1", "kind": "documented_finding", "claim": "Claim", "provisional_disposition": "retained", "genealogy": [{}]}],
        "uncertainties": ["Unresolved point"],
        "issue_register": [{"issue_id": "ISSUE-1", "issue": "Question one"}],
        "issue_states": [{"issue_id": "ISSUE-1", "state": state, "proposition_refs": refs, "basis": basis, "uncertainty_ref": uncertainty_ref}],
    }
    return p


def test_affirmed_is_explicit_and_resolves():
    assert issue_state_map(package()) == {"ISSUE-1": "AFFIRMED"}


def test_rejected_requires_proposition():
    with pytest.raises(MinisterialSilenceError, match="REJECTED requires"):
        validate_silence_semantics(package("REJECTED", refs=[]))


def test_not_addressed_cannot_hide_proposition():
    with pytest.raises(MinisterialSilenceError, match="NOT_ADDRESSED may not carry"):
        validate_silence_semantics(package("NOT_ADDRESSED", refs=["PROP-1"]))


def test_not_asked_is_not_agreement():
    assert issue_state_map(package("NOT_ASKED", refs=[]))["ISSUE-1"] == "NOT_ASKED"


def test_outside_ground_requires_basis():
    with pytest.raises(MinisterialSilenceError, match="explicit basis"):
        validate_silence_semantics(package("OUTSIDE_MY_GROUND", refs=[], basis=None))


def test_uncertain_requires_resolvable_uncertainty_or_proposition():
    with pytest.raises(MinisterialSilenceError, match="UNCERTAIN requires"):
        validate_silence_semantics(package("UNCERTAIN", refs=[], uncertainty_ref=None))
    assert validate_silence_semantics(package("UNCERTAIN", refs=[], uncertainty_ref=0))["silence_semantics_validated"]


def test_missing_issue_state_fails_closed():
    p = package()
    p["issue_states"] = []
    with pytest.raises(MinisterialSilenceError, match="exactly one state"):
        validate_silence_semantics(p)


def test_unknown_proposition_reference_fails():
    with pytest.raises(MinisterialSilenceError, match="unknown proposition"):
        validate_silence_semantics(package("AFFIRMED", refs=["PROP-NOPE"]))
