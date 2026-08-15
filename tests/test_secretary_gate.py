"""Regressions for SECRETARY-GATE-001.

Every test here is a procedure that was skipped in a real run, or could be. None
of them is about whether a judgment was right: the gate has no opinion on that.
"""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import harness
import secretary_audit
import secretary_gate

ROOT = Path(__file__).resolve().parents[1]
T0 = "2026-08-11T09:00:00+00:00"
T1 = "2026-08-11T09:05:00+00:00"


def polity_checklist(**overrides):
    """A conforming polity-board checklist: the shape the failed runs never had."""
    checklist = {
        "record_type": "secretary_pre_run_checklist",
        "gate_standard": "SECRETARY-GATE-001",
        "checklist_id": "SPC-israeli-polis-2026-08-11-talleyrand",
        "inquiry_id": "israeli-polis-2026-08-11",
        "board": "israeli-polis",
        "board_type": "polity",
        "minister_id": "talleyrand",
        "room": "chat",
        "board_manifest": {
            "path": "boards/israeli-polis.yaml",
            "sha256": "a" * 64,
            "frozen": True,
            "frozen_at": T0,
        },
        "roster": [
            {"principal_id": "state", "name": "The State", "type": "body",
             "roster_state": "ENUMERATED", "language": "Hebrew", "language_state": "ORIGINAL",
             "provenance_flag": "HEARD_IN_OWN_WORDS"},
            {"principal_id": "governed-public", "name": "The Governed Public",
             "type": "population_under_control", "roster_state": "ENUMERATED",
             "language": "Arabic", "language_state": "UNRECORDED",
             "provenance_flag": "NOT_GATHERED"},
        ],
        "query_plan": [
            {"plan_id": "QP-state", "principals": ["state"],
             "information_sought": "first-party matter", "language": "Hebrew"},
            {"plan_id": "QP-governed-public", "principals": ["governed-public"],
             "information_sought": "first-party matter", "language": "Arabic"},
        ],
        "query_plan_rule": "GATHER_TO_THE_WHOLE_ROSTER_NOT_TO_A_THESIS",
        "sequence": list(secretary_gate.REQUIRED_SEQUENCE),
        "one_shot_dispatch": "NON_CONFORMING",
        "enumeration_precedes_gathering": True,
        "timestamps": {
            "enumerated_at": T0,
            "query_plan_recorded_at": T1,
            "board_frozen_at": T1,
            "submitted_at": T1,
        },
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }
    checklist.update(overrides)
    return checklist


# --------------------------------------------------------------------------
# the contract
# --------------------------------------------------------------------------

def test_conforming_checklist_matches_the_recorded_contract():
    schema = json.loads((ROOT / "contracts" / "secretary-checklist.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(polity_checklist())


def test_conforming_checklist_opens_the_gate():
    token = secretary_gate.open_gate(polity_checklist(), now=T1)
    assert token["status"] == "SECRETARY_PRE_RUN_GATE_PASS_NOT_TRUTH_CERTIFICATION"
    assert token["certification"] == "NONE_SELF_CERTIFICATION_PROHIBITED"
    assert token["stages_authorized"] == list(secretary_gate.REQUIRED_SEQUENCE)
    secretary_gate.verify_token(token, checklist=polity_checklist())


# --------------------------------------------------------------------------
# a. principal enumeration first
# --------------------------------------------------------------------------

def test_polity_board_without_its_population_is_refused():
    checklist = polity_checklist()
    checklist["roster"] = [checklist["roster"][0]]
    checklist["query_plan"] = [checklist["query_plan"][0]]
    with pytest.raises(secretary_gate.SecretaryGateError, match="polity board"):
        secretary_gate.open_gate(checklist)


def test_a_declared_absence_satisfies_the_polity_requirement():
    checklist = polity_checklist()
    checklist["roster"][1] = {
        "principal_id": "governed-public", "name": "The Governed Public",
        "type": "population_under_control", "roster_state": "ABSENT_DECLARED",
        "absence_reason": "no gathering channel exists for this principal on this date",
        "language": "Arabic", "language_state": "NOT_APPLICABLE",
        "provenance_flag": "NOT_GATHERED",
    }
    checklist["query_plan"] = [checklist["query_plan"][0]]
    secretary_gate.open_gate(checklist)


def test_silent_absence_is_refused():
    checklist = polity_checklist()
    checklist["roster"][1]["roster_state"] = "ABSENT_DECLARED"
    checklist["query_plan"] = [checklist["query_plan"][0]]
    with pytest.raises(secretary_gate.SecretaryGateError, match="declared, never silent"):
        secretary_gate.open_gate(checklist)


def test_a_roster_written_after_its_query_plan_is_refused():
    checklist = polity_checklist()
    checklist["timestamps"]["enumerated_at"] = T1
    checklist["timestamps"]["query_plan_recorded_at"] = T0
    with pytest.raises(secretary_gate.SecretaryGateError, match="written by the query"):
        secretary_gate.open_gate(checklist)


def test_gathering_before_the_gate_is_refused():
    checklist = polity_checklist()
    checklist["timestamps"]["first_gathering_query_at"] = T1
    with pytest.raises(secretary_gate.SecretaryGateError, match="gathering began before the gate"):
        secretary_gate.open_gate(checklist)


def test_the_language_tooth_must_be_named_per_principal():
    checklist = polity_checklist()
    checklist["roster"][1]["language"] = ""
    with pytest.raises(secretary_gate.SecretaryGateError, match="language tooth"):
        secretary_gate.open_gate(checklist)


# --------------------------------------------------------------------------
# b. the query plan follows the roster
# --------------------------------------------------------------------------

def test_a_plan_that_skips_an_enumerated_principal_is_refused():
    checklist = polity_checklist()
    checklist["query_plan"] = [checklist["query_plan"][0]]
    with pytest.raises(secretary_gate.SecretaryGateError, match="not a thesis"):
        secretary_gate.open_gate(checklist)


def test_a_formed_query_that_omits_a_principal_is_refused():
    """The first Israeli-polis failure, caught at the query instead of after the run."""
    checklist = polity_checklist()
    with pytest.raises(secretary_gate.SecretaryGateError, match="governed-public"):
        secretary_gate.require_roster_coverage(checklist, ["state"])


def test_roster_coverage_excuses_only_declared_absence():
    checklist = polity_checklist()
    checklist["roster"][1]["roster_state"] = "ABSENT_DECLARED"
    checklist["roster"][1]["absence_reason"] = "no channel"
    checklist["query_plan"] = [checklist["query_plan"][0]]
    coverage = secretary_gate.require_roster_coverage(checklist, ["state"])
    assert coverage["declared_absent"] == ["governed-public"]
    assert coverage["missing"] == []


# --------------------------------------------------------------------------
# c. the board is frozen
# --------------------------------------------------------------------------

def test_an_unfrozen_board_is_refused():
    checklist = polity_checklist()
    checklist["board_manifest"]["frozen"] = False
    with pytest.raises(secretary_gate.SecretaryGateError, match="frozen"):
        secretary_gate.open_gate(checklist)


def test_a_token_does_not_survive_a_changed_checklist():
    checklist = polity_checklist()
    token = secretary_gate.open_gate(checklist, now=T1)
    changed = copy.deepcopy(checklist)
    changed["roster"].pop()
    with pytest.raises(secretary_gate.SecretaryGateError, match="checklist changed"):
        secretary_gate.verify_token(token, checklist=changed)


def test_an_altered_token_is_refused():
    token = secretary_gate.open_gate(polity_checklist(), now=T1)
    token["minister_id"] = "someone-else"
    with pytest.raises(secretary_gate.SecretaryGateError, match="altered"):
        secretary_gate.verify_token(token)


# --------------------------------------------------------------------------
# d. the declared sequence
# --------------------------------------------------------------------------

def test_a_one_shot_dispatch_cannot_obtain_a_token():
    checklist = secretary_gate.one_shot_checklist(
        board="israeli-polis", board_type="polity", minister_id="talleyrand",
        inquiry_id="israeli-polis-2026-08-11")
    with pytest.raises(secretary_gate.SecretaryGateError, match="one-shot reasoned dispatch is NON-CONFORMING"):
        secretary_gate.open_gate(checklist)


def test_stages_are_handed_out_in_the_declared_order():
    ledger = secretary_gate.StageLedger(secretary_gate.open_gate(polity_checklist(), now=T1))
    receipt = ledger.enter("investigative_query")
    assert receipt["stage_index"] == 0 and receipt["prior_stages"] == []
    ledger.enter("provisional_judgment")
    with pytest.raises(secretary_gate.SecretaryGateError, match="out of order"):
        ledger.enter("final_judgment")


def test_the_adversarial_pass_cannot_be_skipped():
    ledger = secretary_gate.StageLedger(secretary_gate.open_gate(polity_checklist(), now=T1))
    ledger.enter("investigative_query")
    ledger.enter("provisional_judgment")
    with pytest.raises(secretary_gate.SecretaryGateError, match="out of order"):
        ledger.enter("final_judgment")


def test_a_forged_stage_history_is_refused():
    token = secretary_gate.open_gate(polity_checklist(), now=T1)
    ledger = secretary_gate.StageLedger(token)
    receipt = ledger.enter("investigative_query")
    receipt["stage"] = "final_judgment"
    receipt["stage_index"] = 3
    receipt["prior_stages"] = list(secretary_gate.REQUIRED_SEQUENCE[:3])
    with pytest.raises(secretary_gate.SecretaryGateError, match="altered"):
        secretary_gate.verify_stage_receipt(token, receipt)


def test_the_genealogy_stage_may_follow_the_constitutional_four():
    checklist = polity_checklist()
    checklist["sequence"] = list(secretary_gate.REQUIRED_SEQUENCE) + ["genealogy_finalization"]
    token = secretary_gate.open_gate(checklist, now=T1)
    ledger = secretary_gate.StageLedger.resume(token, list(secretary_gate.REQUIRED_SEQUENCE))
    assert ledger.enter("genealogy_finalization")["stage_index"] == 4


# --------------------------------------------------------------------------
# the harness refuses to CALL
# --------------------------------------------------------------------------

def test_harness_refuses_to_call_without_a_pass_token():
    with pytest.raises(secretary_gate.SecretaryGateError, match="CALL REFUSED"):
        harness.call({"provider": "stub"}, "any context at all")


def test_harness_refuses_a_receipt_from_another_run():
    token = secretary_gate.open_gate(polity_checklist(), now=T1)
    other = secretary_gate.open_gate(polity_checklist(minister_id="xenophon"), now=T1)
    receipt = secretary_gate.StageLedger(other).enter("investigative_query")
    with pytest.raises(secretary_gate.SecretaryGateError, match="not issued against this pass token"):
        harness.call({"provider": "stub"}, "context", pass_token=token, stage_receipt=receipt)


def test_harness_calls_with_a_gated_stage_receipt():
    token = secretary_gate.open_gate(polity_checklist(), now=T1)
    receipt = secretary_gate.StageLedger(token).enter("investigative_query")
    answer = harness.call({"provider": "stub"}, "context", pass_token=token, stage_receipt=receipt)
    assert answer["model"] == "stub"


# --------------------------------------------------------------------------
# the builder records the estate, and invents nothing
# --------------------------------------------------------------------------

def test_checklist_from_board_records_language_and_provenance_per_principal():
    board = {
        "board": "israeli-polis",
        "board_type": "polity",
        "roster": [
            {"id": "state", "name": "The State", "type": "body", "file": "files/state.md"},
            {"id": "governed-public", "name": "The Governed Public",
             "type": "population_under_control", "file": "files/governed-public.md"},
        ],
    }
    parity_record = {"principals": [
        {"id": "state", "file_state": "PRESENT", "heard_in_own_words": True,
         "tiers": {"T1": {"language": "Hebrew", "language_state": "ORIGINAL"}}},
        {"id": "governed-public", "file_state": "ABSENT", "tiers": {}},
    ]}
    checklist = secretary_gate.checklist_from_board(
        board=board, parity_record=parity_record, inquiry_id="israeli-polis-2026-08-11",
        minister_id="talleyrand", room="harness", board_manifest_path="Horus/boards/israeli-polis.yaml",
        board_manifest_sha256="b" * 64, now=T0)
    secretary_gate.open_gate(checklist)
    flags = {entry["principal_id"]: entry["provenance_flag"] for entry in checklist["roster"]}
    assert flags == {"state": "HEARD_IN_OWN_WORDS", "governed-public": "NOT_GATHERED"}
    assert [item["plan_id"] for item in checklist["query_plan"]] == ["QP-state", "QP-governed-public"]


# --------------------------------------------------------------------------
# the post-run audit
# --------------------------------------------------------------------------

CONFORMING_DISPATCH = """### POSITION — The State [state]
PROVENANCE: HEARD_IN_OWN_WORDS — Hebrew

Its position, in its own voice.

### POSITION — The Governed Public [governed-public]
PROVENANCE: NOT_GATHERED — Arabic
SILENCE: NOT_ASKED

This principal was not gathered.

## MINISTERIAL JUDGMENT — talleyrand

The judgment, after the parties.
"""


def test_a_conforming_dispatch_passes_the_post_run_audit():
    audit = secretary_audit.require_conforming_dispatch(polity_checklist(), CONFORMING_DISPATCH)
    assert audit["failures"] == []
    assert audit["counterfeits_triggered"] == []
    assert audit["checks"]["voices_held_distinct"] == "PASS"


def test_condensed_voices_are_voided_and_named_as_counterfeits():
    """The second Israeli-polis failure: one narrator, and the omission travels inside it."""
    dispatch = "## MINISTERIAL JUDGMENT — talleyrand\n\nOne voice for everyone.\n"
    audit = secretary_audit.audit_dispatch(polity_checklist(), dispatch)
    assert audit["status"] == secretary_gate.VOID_STATUS
    assert secretary_audit.COUNTERFEIT_CONDENSED_VOICES in audit["counterfeits_triggered"]
    assert secretary_audit.COUNTERFEIT_FRAME_CAPTURE in audit["counterfeits_triggered"]


def test_an_unattributed_population_triggers_frame_capture():
    dispatch = CONFORMING_DISPATCH.replace(
        "### POSITION — The Governed Public [governed-public]\n"
        "PROVENANCE: NOT_GATHERED — Arabic\nSILENCE: NOT_ASKED\n", "")
    audit = secretary_audit.audit_dispatch(polity_checklist(), dispatch)
    assert secretary_audit.COUNTERFEIT_FRAME_CAPTURE in audit["counterfeits_triggered"]
    assert audit["unattributed_principals"] == ["governed-public"]


def test_the_judgment_may_not_stand_before_the_parties():
    dispatch = "## MINISTERIAL JUDGMENT — talleyrand\n\n" + CONFORMING_DISPATCH.split(
        "## MINISTERIAL JUDGMENT")[0]
    audit = secretary_audit.audit_dispatch(polity_checklist(), dispatch)
    assert any("placed before" in failure for failure in audit["failures"])


def test_a_principal_may_not_be_raised_above_how_he_was_heard():
    dispatch = CONFORMING_DISPATCH.replace("PROVENANCE: NOT_GATHERED — Arabic\nSILENCE: NOT_ASKED",
                                           "PROVENANCE: HEARD_IN_OWN_WORDS — Arabic")
    audit = secretary_audit.audit_dispatch(polity_checklist(), dispatch)
    assert any("rises above" in failure for failure in audit["failures"])


def test_the_synthesis_may_not_author_a_party_view():
    dispatch = CONFORMING_DISPATCH.replace("### POSITION — The State [state]",
                                           "### POSITION — The President [president]")
    audit = secretary_audit.audit_dispatch(polity_checklist(), dispatch)
    assert any("synthesis authors a party" in failure for failure in audit["failures"])


def test_untyped_silence_is_a_failure():
    dispatch = CONFORMING_DISPATCH.replace("SILENCE: NOT_ASKED\n", "")
    audit = secretary_audit.audit_dispatch(polity_checklist(), dispatch)
    assert any("untyped" in failure for failure in audit["failures"])


def test_ground_outside_the_frozen_board_is_a_failure():
    dispatch = CONFORMING_DISPATCH + "\n### POSITION — Somebody Else [somebody-else]\n" \
        "PROVENANCE: FILLED_FROM_ELSEWHERE — English\n"
    audit = secretary_audit.audit_dispatch(polity_checklist(), dispatch)
    assert any("invented ground" in failure for failure in audit["failures"])


def test_the_registered_counterfeits_are_the_ones_the_audit_scans_for():
    """A registry the scanner does not read is decoration. These are bound."""
    registry = harness.yaml_load((ROOT / "registry" / "counterfeits.yaml").read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in registry["counterfeits"]}
    assert secretary_audit.COUNTERFEIT_FRAME_CAPTURE in entries
    assert secretary_audit.COUNTERFEIT_CONDENSED_VOICES in entries
    for entry in entries.values():
        assert entry["cure"].strip(), "a registered counterfeit carries its cure"
        assert entry["record"], "a counterfeit is entered when a run produces it"
    proposal = registry["federation"][0]
    assert proposal["house"] == "Talleyrand"
    assert proposal["status"] == "PROPOSED_PENDING_OWNER_RATIFICATION"
    assert (ROOT / proposal["proposal"]).is_file()


def test_the_charter_and_the_gate_agree_on_the_sequence():
    charter = (ROOT / "offices" / "secretary" / "charter.md").read_text(encoding="utf-8")
    assert "NON_CONFORMING_VOID" in charter
    for stage in ("investigative", "provisional judgment", "adversarial pass", "final"):
        assert stage in charter
    assert secretary_gate.REQUIRED_SEQUENCE == (
        "investigative_query", "provisional_judgment", "adversarial_pass", "final_judgment")


def test_the_void_record_never_grades_substance():
    record = secretary_gate.void_record(
        inquiry_id="israeli-polis-2026-08-11", board="israeli-polis", minister_id="talleyrand",
        room="chat", stage="post_run_audit", reason="voices not held distinct", now=T1)
    assert record["status"] == "NON_CONFORMING_VOID"
    assert "reports/" in record["consequence"]
    assert record["certification"] == "NONE_SELF_CERTIFICATION_PROHIBITED"
