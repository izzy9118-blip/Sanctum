import copy

import pytest

from proposition_matrix import (
    PropositionMatrixError,
    build_inventory,
    required_presidential_matrix_call,
    synthesis_payload,
    validate_matrix,
)


def package(minister, props):
    return {
        "record_type": "final_judgment_package",
        "inquiry_id": "INQ-1",
        "minister_id": minister,
        "repository": {"full_name": minister.title(), "git_commit": "a" * 40},
        "summary": f"{minister} summary",
        "propositions": props,
        "uncertainties": [],
    }


def packages():
    return {
        "strauss": package("strauss", [
            {"proposition_id": "PROP-S1", "kind": "supported_inference", "claim": "Claim S1", "provisional_disposition": "retained", "genealogy": [{}]},
        ]),
        "xenophon": package("xenophon", [
            {"proposition_id": "PROP-X1", "kind": "documented_finding", "claim": "Claim X1", "provisional_disposition": "retained", "genealogy": [{}]},
            {"proposition_id": "PROP-X2", "kind": "unresolved_uncertainty", "claim": "Claim X2", "provisional_disposition": "left_unresolved", "genealogy": []},
        ]),
    }


def valid_matrix(pkgs=None):
    pkgs = pkgs or packages()
    inv = build_inventory(pkgs)
    return {
        "record_type": "presidential_proposition_matrix",
        "inquiry_id": "INQ-1",
        "alignment_authority": "PRESIDENTIAL_ALIGNMENT",
        "participating_ministers": inv["participating_ministers"],
        "package_bindings": inv["package_bindings"],
        "rows": [
            {
                "matrix_row_id": "ROW-1",
                "comparison_question": "How do the ministers characterize the first issue?",
                "presidential_note": None,
                "minister_entries": [
                    {"minister_id": "strauss", "state": "QUALIFIES", "propositions": [
                        {"proposition_id": "PROP-S1", "kind": "supported_inference", "claim": "Claim S1"}
                    ]},
                    {"minister_id": "xenophon", "state": "AFFIRMS", "propositions": [
                        {"proposition_id": "PROP-X1", "kind": "documented_finding", "claim": "Claim X1"}
                    ]},
                ],
            },
            {
                "matrix_row_id": "ROW-2",
                "comparison_question": "What remains unresolved?",
                "presidential_note": None,
                "minister_entries": [
                    {"minister_id": "strauss", "state": "NOT_ADDRESSED", "propositions": []},
                    {"minister_id": "xenophon", "state": "UNCERTAIN", "propositions": [
                        {"proposition_id": "PROP-X2", "kind": "unresolved_uncertainty", "claim": "Claim X2"}
                    ]},
                ],
            },
        ],
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }


def test_valid_matrix_covers_every_proposition_exactly_once():
    assert validate_matrix(packages(), valid_matrix())["record_type"] == "presidential_proposition_matrix"


def test_omitted_proposition_aborts():
    matrix = valid_matrix()
    matrix["rows"].pop()
    with pytest.raises(PropositionMatrixError, match="omits propositions"):
        validate_matrix(packages(), matrix)


def test_duplicate_proposition_aborts():
    matrix = valid_matrix()
    matrix["rows"][1]["minister_entries"][1]["propositions"] = [
        {"proposition_id": "PROP-X1", "kind": "documented_finding", "claim": "Claim X1"}
    ]
    with pytest.raises(PropositionMatrixError, match="more than one matrix location"):
        validate_matrix(packages(), matrix)


def test_rewritten_claim_aborts():
    matrix = valid_matrix()
    matrix["rows"][0]["minister_entries"][0]["propositions"][0]["claim"] = "Presidential rewrite"
    with pytest.raises(PropositionMatrixError, match="rewrites claim"):
        validate_matrix(packages(), matrix)


def test_silence_cannot_be_affirmative_without_proposition():
    matrix = valid_matrix()
    matrix["rows"][1]["minister_entries"][0]["state"] = "AFFIRMS"
    with pytest.raises(PropositionMatrixError, match="AFFIRMS requires"):
        validate_matrix(packages(), matrix)


def test_not_addressed_cannot_hide_a_proposition():
    matrix = valid_matrix()
    matrix["rows"][1]["minister_entries"][0] = {
        "minister_id": "strauss", "state": "NOT_ADDRESSED",
        "propositions": [{"proposition_id": "PROP-S1", "kind": "supported_inference", "claim": "Claim S1"}],
    }
    with pytest.raises(PropositionMatrixError, match="NOT_ADDRESSED may not carry"):
        validate_matrix(packages(), matrix)


def test_package_hash_binding_blocks_changed_package():
    pkgs = packages()
    matrix = valid_matrix(pkgs)
    changed = copy.deepcopy(pkgs)
    changed["strauss"]["summary"] = "changed after alignment"
    with pytest.raises(PropositionMatrixError, match="package bindings"):
        validate_matrix(changed, matrix)


def test_required_call_validates_presidential_alignment():
    pkgs = packages()
    got = required_presidential_matrix_call(pkgs, lambda _: valid_matrix(pkgs))
    assert got["alignment_authority"] == "PRESIDENTIAL_ALIGNMENT"


def test_synthesis_payload_requires_validated_matrix():
    payload = synthesis_payload(packages(), valid_matrix())
    assert payload["rule"] == "SYNTHESIS_MUST_PRESERVE_MATRIX_DISAGREEMENT_AND_SILENCE"
