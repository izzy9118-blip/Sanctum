#!/usr/bin/env python3
"""SECRETARY-GATE-001 — the Secretary's pre-run checklist, made executable.

Two proving runs failed on procedure that was already written. A gathering query
was formed before the board's principals were enumerated, so a principal who
belonged on the roster was never queried at all; the parties' positions were then
condensed into one narrating voice, which is how that omission left the room
unseen. Every safeguard for both failures existed. Nothing refused to proceed
without them.

This module is the refusal. It validates the pre-run checklist, issues a pass
token bound to that checklist by hash, and hands out per-stage receipts in the
declared order. The Sovereign Harness will not CALL without a receipt.

The Secretary judges nothing here. It selects no source, grades no truth, and
reads no claim for its merit. It checks that the steps were performed, in order,
and records what it checked. See offices/secretary/charter.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

GATE_STANDARD = "SECRETARY-GATE-001"
CHARTER_PATH = "offices/secretary/charter.md"
CHECKLIST_CONTRACT = "contracts/secretary-checklist.schema.json"
CHECKLIST_RECORD_TYPE = "secretary_pre_run_checklist"
TOKEN_RECORD_TYPE = "secretary_pass_token"
RECEIPT_RECORD_TYPE = "secretary_stage_receipt"
VOID_RECORD_TYPE = "secretary_void_record"

# The sequence is constitutional: investigative -> provisional judgment naming its
# own weaknesses -> adversarial pass -> final. A one-shot reasoned dispatch skips
# the stage at which the judgment could have been disconfirmed.
REQUIRED_SEQUENCE = ("investigative_query", "provisional_judgment", "adversarial_pass", "final_judgment")
OPTIONAL_TRAILING_STAGES = ("genealogy_finalization",)
KNOWN_STAGES = REQUIRED_SEQUENCE + OPTIONAL_TRAILING_STAGES

ROOMS = ("harness", "agent", "chat")
ROSTER_STATES = ("ENUMERATED", "ABSENT_DECLARED")
LANGUAGE_STATES = ("ORIGINAL", "TRANSLATION", "UNRECORDED", "NOT_APPLICABLE")
PROVENANCE_FLAGS = ("HEARD_IN_OWN_WORDS", "FILLED_FROM_ELSEWHERE", "NOT_GATHERED")
QUERY_PLAN_RULE = "GATHER_TO_THE_WHOLE_ROSTER_NOT_TO_A_THESIS"
CERTIFICATION = "NONE_SELF_CERTIFICATION_PROHIBITED"

# On a polity board the resident publics and the populations under the polity's
# control are principals, not context. They are enumerated or their absence is
# declared under their own name; it is never silent.
POLITY_BOARD_TYPES = ("polity", "polis", "state", "regime", "occupation", "governance")
POPULATION_KINDS = (
    "resident_public",
    "population_under_control",
    "governed_population",
    "stateless_population",
    "public",
)

GATE_PASS_STATUS = "SECRETARY_PRE_RUN_GATE_PASS_NOT_TRUTH_CERTIFICATION"
VOID_STATUS = "NON_CONFORMING_VOID"


class SecretaryGateError(RuntimeError):
    """Raised when the procedure was not performed. It is never a claim about truth."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SecretaryGateError(message)


def _text(value, field: str) -> str:
    _require(isinstance(value, str) and value.strip(), f"{field} is required and must be a non-empty string")
    return value


def canonical_sha256(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _moment(value, field: str) -> dt.datetime:
    _text(value, field)
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SecretaryGateError(f"{field} is not an ISO-8601 timestamp: {value!r}") from exc


def is_polity_board(board_type: str) -> bool:
    return str(board_type or "").strip().lower() in POLITY_BOARD_TYPES


def _is_population(kind: str) -> bool:
    return str(kind or "").strip().lower() in POPULATION_KINDS


# --------------------------------------------------------------------------
# a. — the checklist itself
# --------------------------------------------------------------------------

def validate_checklist(checklist) -> dict:
    """Validate a pre-run checklist. Raise on the first thing that was skipped."""
    _require(isinstance(checklist, dict), "checklist must be one JSON object")
    _require(checklist.get("record_type") == CHECKLIST_RECORD_TYPE,
             f"record_type must be {CHECKLIST_RECORD_TYPE}")
    _require(checklist.get("gate_standard") == GATE_STANDARD,
             f"gate_standard must be {GATE_STANDARD}")
    _require(checklist.get("certification") == CERTIFICATION,
             f"certification must be {CERTIFICATION}: the Secretary certifies nothing")

    checklist_id = _text(checklist.get("checklist_id"), "checklist_id")
    _require(checklist_id.startswith("SPC-"), "checklist_id must begin with SPC-")
    for field in ("inquiry_id", "board", "board_type", "minister_id"):
        _text(checklist.get(field), field)
    _require(checklist.get("room") in ROOMS,
             f"room must be one of {', '.join(ROOMS)}: the gate has the same force in every room")

    # d. first, because it is the most categorical: a run that never declared the
    # sequence has nothing for the rest of the checklist to be a checklist of.
    _validate_sequence(checklist.get("sequence"))
    _validate_board_manifest(checklist.get("board_manifest"))
    roster = _validate_roster(checklist.get("roster"), checklist["board_type"])
    _validate_query_plan(checklist, roster)

    _require(checklist.get("one_shot_dispatch") == "NON_CONFORMING",
             "one_shot_dispatch must be declared NON_CONFORMING")
    _require(checklist.get("enumeration_precedes_gathering") is True,
             "enumeration_precedes_gathering must be declared true")
    _validate_timestamps(checklist.get("timestamps"))
    return checklist


def _validate_board_manifest(manifest) -> None:
    _require(isinstance(manifest, dict), "board_manifest is required: the board is identified or created, then frozen")
    _text(manifest.get("path"), "board_manifest.path")
    digest = manifest.get("sha256", "")
    _require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
             "board_manifest.sha256 must be a lowercase sha256 of the frozen board")
    _require(manifest.get("frozen") is True,
             "the board must be frozen before judgment; a board that grows during a run is fitted to a conclusion")
    _moment(manifest.get("frozen_at"), "board_manifest.frozen_at")


def _validate_roster(roster, board_type: str) -> list:
    _require(isinstance(roster, list) and roster,
             "roster must be a non-empty list: the principals are enumerated before the first gathering query")
    seen = set()
    for index, entry in enumerate(roster):
        where = f"roster[{index}]"
        _require(isinstance(entry, dict), f"{where} must be an object")
        principal_id = _text(entry.get("principal_id"), f"{where}.principal_id")
        _require(principal_id not in seen, f"{where}.principal_id {principal_id!r} is enumerated twice")
        seen.add(principal_id)
        _text(entry.get("name"), f"{where}.name")
        _text(entry.get("type"), f"{where}.type")
        _require(entry.get("roster_state") in ROSTER_STATES,
                 f"{where}.roster_state must be one of {', '.join(ROSTER_STATES)}")
        if entry["roster_state"] == "ABSENT_DECLARED":
            _require(isinstance(entry.get("absence_reason"), str) and entry["absence_reason"].strip(),
                     f"{where} is absent and gives no reason; absence from the roster is declared, never silent")
        # the tooth: the language each principal is to be heard in is named per
        # principal. Whether that language is adequate is Horus's finding and the
        # owner's grade, never the Secretary's.
        _text(entry.get("language"), f"{where}.language (the language tooth: name it per principal)")
        _require(entry.get("language_state") in LANGUAGE_STATES,
                 f"{where}.language_state must be one of {', '.join(LANGUAGE_STATES)}")
        _require(entry.get("provenance_flag") in PROVENANCE_FLAGS,
                 f"{where}.provenance_flag must be one of {', '.join(PROVENANCE_FLAGS)}")

    if is_polity_board(board_type):
        populations = [e for e in roster if _is_population(e.get("type"))]
        _require(bool(populations),
                 "polity board: the resident publics and the populations under the polity's control are "
                 "principals and are absent from this roster. Enumerate them, or declare the absence under "
                 "their own name with a reason. Absence is never silent.")
    return roster


def _validate_query_plan(checklist: dict, roster: list) -> None:
    plan = checklist.get("query_plan")
    _require(isinstance(plan, list) and plan, "query_plan must be a non-empty list")
    _require(checklist.get("query_plan_rule") == QUERY_PLAN_RULE,
             f"query_plan_rule must be {QUERY_PLAN_RULE}")

    known = {entry["principal_id"] for entry in roster}
    planned = set()
    for index, item in enumerate(plan):
        where = f"query_plan[{index}]"
        _require(isinstance(item, dict), f"{where} must be an object")
        _text(item.get("plan_id"), f"{where}.plan_id")
        principals = item.get("principals")
        _require(isinstance(principals, list) and principals, f"{where}.principals must be a non-empty list")
        for principal in principals:
            _text(principal, f"{where}.principals[]")
            _require(principal in known,
                     f"{where} plans a query for {principal!r}, who is not on the frozen roster")
            planned.add(principal)
        _text(item.get("information_sought"), f"{where}.information_sought")
        _text(item.get("language"), f"{where}.language")

    missing = sorted(e["principal_id"] for e in roster
                     if e["roster_state"] == "ENUMERATED" and e["principal_id"] not in planned)
    _require(not missing,
             "the query plan follows the roster, not a thesis; these enumerated principals are in no "
             f"plan item: {', '.join(missing)}")


def _validate_sequence(sequence) -> None:
    _require(isinstance(sequence, list) and sequence, "sequence must be a non-empty list")
    if len(sequence) < len(REQUIRED_SEQUENCE):
        raise SecretaryGateError(
            "the declared sequence is "
            f"{sequence!r}: a one-shot reasoned dispatch is NON-CONFORMING. The constitutional "
            f"sequence is {' -> '.join(REQUIRED_SEQUENCE)}."
        )
    _require(tuple(sequence[:len(REQUIRED_SEQUENCE)]) == REQUIRED_SEQUENCE,
             f"the first four declared stages must be exactly {' -> '.join(REQUIRED_SEQUENCE)}")
    for stage in sequence[len(REQUIRED_SEQUENCE):]:
        _require(stage in OPTIONAL_TRAILING_STAGES,
                 f"unknown trailing stage {stage!r}; permitted: {', '.join(OPTIONAL_TRAILING_STAGES)}")
    _require(len(set(sequence)) == len(sequence), "the declared sequence repeats a stage")


def _validate_timestamps(timestamps) -> None:
    _require(isinstance(timestamps, dict), "timestamps are required: the gate records the order it checked")
    enumerated = _moment(timestamps.get("enumerated_at"), "timestamps.enumerated_at")
    planned = _moment(timestamps.get("query_plan_recorded_at"), "timestamps.query_plan_recorded_at")
    frozen = _moment(timestamps.get("board_frozen_at"), "timestamps.board_frozen_at")
    submitted = _moment(timestamps.get("submitted_at"), "timestamps.submitted_at")
    _require(enumerated <= planned,
             "the query plan was recorded before the roster: a roster written after the first query is "
             "written by the query")
    _require(planned <= submitted, "the checklist was submitted before its own query plan")
    _require(frozen <= submitted, "the board was frozen after the checklist was submitted")
    first_query = timestamps.get("first_gathering_query_at")
    _require(first_query in (None, ""),
             "timestamps.first_gathering_query_at is already set: gathering began before the gate was asked")


# --------------------------------------------------------------------------
# the pass token and the stage receipts
# --------------------------------------------------------------------------

def checklist_digest(checklist: dict) -> str:
    return canonical_sha256(checklist)


def open_gate(checklist: dict, *, now: str | None = None) -> dict:
    """Validate the checklist and issue the pass token bound to it by hash."""
    validate_checklist(checklist)
    issued_at = now or utc_now()
    _moment(issued_at, "issued_at")
    token = {
        "record_type": TOKEN_RECORD_TYPE,
        "gate_standard": GATE_STANDARD,
        "charter": CHARTER_PATH,
        "checklist_contract": CHECKLIST_CONTRACT,
        "checklist_id": checklist["checklist_id"],
        "checklist_sha256": checklist_digest(checklist),
        "inquiry_id": checklist["inquiry_id"],
        "board": checklist["board"],
        "minister_id": checklist["minister_id"],
        "room": checklist["room"],
        "stages_authorized": list(checklist["sequence"]),
        "issued_at": issued_at,
        "status": GATE_PASS_STATUS,
        "certification": CERTIFICATION,
    }
    token["token_sha256"] = canonical_sha256(token)
    return token


def verify_token(token, *, checklist: dict | None = None) -> dict:
    """Verify a pass token's integrity, and its binding to a checklist if given."""
    _require(isinstance(token, dict), "pass token must be one JSON object")
    _require(token.get("record_type") == TOKEN_RECORD_TYPE, f"pass token record_type must be {TOKEN_RECORD_TYPE}")
    _require(token.get("gate_standard") == GATE_STANDARD, f"pass token must be issued under {GATE_STANDARD}")
    _require(token.get("status") == GATE_PASS_STATUS, "pass token does not carry the gate-pass status")
    recorded = token.get("token_sha256")
    _require(isinstance(recorded, str) and recorded, "pass token carries no token_sha256")
    body = {k: v for k, v in token.items() if k != "token_sha256"}
    _require(canonical_sha256(body) == recorded, "pass token has been altered since it was issued")
    stages = token.get("stages_authorized")
    _require(isinstance(stages, list) and tuple(stages[:len(REQUIRED_SEQUENCE)]) == REQUIRED_SEQUENCE,
             "pass token does not authorize the constitutional sequence")
    if checklist is not None:
        _require(token.get("checklist_sha256") == checklist_digest(checklist),
                 "pass token is not bound to this checklist; the checklist changed after the gate")
    return token


class StageLedger:
    """Hands out stage receipts in the declared order, and refuses any other order."""

    def __init__(self, token: dict, completed: list | None = None):
        self.token = verify_token(token)
        self.sequence = list(token["stages_authorized"])
        self.completed: list[str] = []
        for stage in completed or []:
            self._advance(stage)

    @classmethod
    def resume(cls, token: dict, completed: list) -> "StageLedger":
        """Resume a ledger across a runtime boundary from the recorded stages."""
        return cls(token, completed=completed)

    def _advance(self, stage: str) -> int:
        index = len(self.completed)
        _require(index < len(self.sequence),
                 f"stage {stage!r} was entered after the declared sequence was exhausted")
        expected = self.sequence[index]
        _require(stage == expected,
                 f"stage out of order: {expected!r} is next in the declared sequence, {stage!r} was entered. "
                 "The sequence is the safeguard; skipping a stage voids the run.")
        self.completed.append(stage)
        return index

    def enter(self, stage: str) -> dict:
        """Enter the next stage and return the receipt the harness requires to CALL."""
        index = self._advance(stage)
        receipt = {
            "record_type": RECEIPT_RECORD_TYPE,
            "gate_standard": GATE_STANDARD,
            "token_sha256": self.token["token_sha256"],
            "checklist_sha256": self.token["checklist_sha256"],
            "inquiry_id": self.token["inquiry_id"],
            "minister_id": self.token["minister_id"],
            "stage": stage,
            "stage_index": index,
            "prior_stages": list(self.completed[:index]),
            "entered_at": utc_now(),
        }
        receipt["receipt_sha256"] = canonical_sha256(receipt)
        return receipt

    def stages_completed(self) -> list:
        return list(self.completed)


def verify_stage_receipt(token, receipt) -> dict:
    """The check the Sovereign Harness makes before it will CALL anything."""
    verify_token(token)
    _require(isinstance(receipt, dict), "stage receipt must be one JSON object")
    _require(receipt.get("record_type") == RECEIPT_RECORD_TYPE,
             f"stage receipt record_type must be {RECEIPT_RECORD_TYPE}")
    recorded = receipt.get("receipt_sha256")
    _require(isinstance(recorded, str) and recorded, "stage receipt carries no receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    _require(canonical_sha256(body) == recorded, "stage receipt has been altered since it was issued")
    _require(receipt.get("token_sha256") == token["token_sha256"],
             "stage receipt was not issued against this pass token")
    sequence = list(token["stages_authorized"])
    index = receipt.get("stage_index")
    _require(isinstance(index, int) and 0 <= index < len(sequence), "stage receipt carries no valid stage_index")
    _require(receipt.get("stage") == sequence[index], "stage receipt names a stage the sequence does not place there")
    _require(list(receipt.get("prior_stages") or []) == sequence[:index],
             "stage receipt claims a history the declared sequence does not have")
    return receipt


# --------------------------------------------------------------------------
# b. — the query the minister actually formed, checked against the roster
# --------------------------------------------------------------------------

def roster_coverage(checklist: dict, principal_scope) -> dict:
    """Compare a formed gathering query against the frozen roster. Procedure only."""
    validate_checklist(checklist)
    scope = {s for s in (principal_scope or []) if isinstance(s, str)}
    enumerated = [e for e in checklist["roster"] if e["roster_state"] == "ENUMERATED"]
    declared_absent = [e["principal_id"] for e in checklist["roster"] if e["roster_state"] == "ABSENT_DECLARED"]
    covered, missing = [], []
    for entry in enumerated:
        identity = {entry["principal_id"], entry["name"]}
        (covered if identity & scope else missing).append(entry["principal_id"])
    return {
        "record_type": "secretary_roster_coverage",
        "gate_standard": GATE_STANDARD,
        "checklist_id": checklist["checklist_id"],
        "covered": sorted(covered),
        "missing": sorted(missing),
        "declared_absent": sorted(declared_absent),
        "outside_the_roster": sorted(scope - {e["principal_id"] for e in checklist["roster"]}
                                     - {e["name"] for e in checklist["roster"]}),
    }


def require_roster_coverage(checklist: dict, principal_scope) -> dict:
    coverage = roster_coverage(checklist, principal_scope)
    _require(not coverage["missing"],
             "the gathering query does not reach the whole roster. Enumerated principals absent from the "
             f"query's principal_scope: {', '.join(coverage['missing'])}. Query the roster, or declare the "
             "absence under the principal's own name.")
    return coverage


# --------------------------------------------------------------------------
# builders — the runner may not author substance, only record the procedure
# --------------------------------------------------------------------------

def _parity_principal(parity_record: dict, principal_id: str) -> dict:
    for principal in (parity_record or {}).get("principals", []):
        if principal.get("id") == principal_id:
            return principal
    return {}


def checklist_from_board(*, board: dict, parity_record: dict, inquiry_id: str, minister_id: str,
                         room: str, board_manifest_path: str, board_manifest_sha256: str,
                         sequence=None, now: str | None = None) -> dict:
    """Build the checklist from the frozen board and its parity manifest.

    The runner records what the estate already says: who is on the roster, in what
    language each principal is to be heard, and how each was last heard. It invents
    no principal and grades nothing.
    """
    stamp = now or utc_now()
    roster = []
    plan = []
    for entry in board.get("roster", []):
        principal_id = entry.get("id", "")
        principal = _parity_principal(parity_record, principal_id)
        tier_one = (principal.get("tiers") or {}).get("T1") or {}
        language = tier_one.get("language") or "UNRECORDED"
        language_state = tier_one.get("language_state") or "UNRECORDED"
        if language_state not in LANGUAGE_STATES:
            language_state = "UNRECORDED"
        if principal.get("heard_in_own_words"):
            provenance = "HEARD_IN_OWN_WORDS"
        elif principal.get("file_state") == "PRESENT":
            provenance = "FILLED_FROM_ELSEWHERE"
        else:
            provenance = "NOT_GATHERED"
        roster.append({
            "principal_id": principal_id,
            "name": entry.get("name", principal_id),
            "type": entry.get("type", "unspecified"),
            "roster_state": "ENUMERATED",
            "language": language,
            "language_state": language_state,
            "provenance_flag": provenance,
            "file": entry.get("file", ""),
        })
        plan.append({
            "plan_id": f"QP-{principal_id}",
            "principals": [principal_id],
            "information_sought": (
                "first-party matter, record, and current conduct for this principal, "
                "in the principal's own words"
            ),
            "language": language,
        })

    for absence in board.get("declared_absences", []) or []:
        principal_id = absence.get("id") or absence.get("principal_id", "")
        roster.append({
            "principal_id": principal_id,
            "name": absence.get("name", principal_id),
            "type": absence.get("type") or absence.get("principal_kind", "unspecified"),
            "roster_state": "ABSENT_DECLARED",
            "absence_reason": absence.get("reason", ""),
            "language": absence.get("language", "UNRECORDED"),
            "language_state": "NOT_APPLICABLE",
            "provenance_flag": "NOT_GATHERED",
        })

    checklist = {
        "record_type": CHECKLIST_RECORD_TYPE,
        "gate_standard": GATE_STANDARD,
        "checklist_id": f"SPC-{inquiry_id}-{minister_id}",
        "inquiry_id": inquiry_id,
        "board": board.get("board", ""),
        "board_type": board.get("board_type", "unspecified"),
        "minister_id": minister_id,
        "room": room,
        "board_manifest": {
            "path": board_manifest_path,
            "sha256": board_manifest_sha256,
            "frozen": True,
            "frozen_at": stamp,
        },
        "roster": roster,
        "query_plan": plan,
        "query_plan_rule": QUERY_PLAN_RULE,
        "sequence": list(sequence or REQUIRED_SEQUENCE),
        "one_shot_dispatch": "NON_CONFORMING",
        "enumeration_precedes_gathering": True,
        "timestamps": {
            "enumerated_at": stamp,
            "query_plan_recorded_at": stamp,
            "board_frozen_at": stamp,
            "submitted_at": stamp,
        },
        "certification": CERTIFICATION,
    }
    return checklist


def one_shot_checklist(*, board: str, board_type: str, minister_id: str, inquiry_id: str,
                       room: str = "harness", now: str | None = None) -> dict:
    """What a one-shot reasoned dispatch can truthfully declare.

    It is built so that a single-call path states what it actually does. The gate
    refuses it, which is the point: the refusal belongs to the Secretary, not to a
    hand-written check inside the caller.
    """
    stamp = now or utc_now()
    return {
        "record_type": CHECKLIST_RECORD_TYPE,
        "gate_standard": GATE_STANDARD,
        "checklist_id": f"SPC-{inquiry_id}-{minister_id}-one-shot",
        "inquiry_id": inquiry_id,
        "board": board,
        "board_type": board_type or "unspecified",
        "minister_id": minister_id,
        "room": room,
        "board_manifest": {"path": f"boards/{board}.yaml", "sha256": "0" * 64,
                           "frozen": True, "frozen_at": stamp},
        "roster": [],
        "query_plan": [],
        "query_plan_rule": QUERY_PLAN_RULE,
        "sequence": ["final_judgment"],
        "one_shot_dispatch": "NON_CONFORMING",
        "enumeration_precedes_gathering": True,
        "timestamps": {"enumerated_at": stamp, "query_plan_recorded_at": stamp,
                       "board_frozen_at": stamp, "submitted_at": stamp},
        "certification": CERTIFICATION,
    }


# --------------------------------------------------------------------------
# the void
# --------------------------------------------------------------------------

def void_record(*, inquiry_id: str, board: str, minister_id: str, room: str,
                stage: str, reason: str, checklist_sha256: str = "",
                preserved_at: str = "", now: str | None = None) -> dict:
    """Mark a run NON_CONFORMING_VOID. The Secretary voids; it never edits or judges."""
    record = {
        "record_type": VOID_RECORD_TYPE,
        "gate_standard": GATE_STANDARD,
        "charter": CHARTER_PATH,
        "status": VOID_STATUS,
        "inquiry_id": inquiry_id,
        "board": board,
        "minister_id": minister_id,
        "room": room,
        "failed_at": stage,
        "reason": reason,
        "checklist_sha256": checklist_sha256,
        "preserved_at": preserved_at,
        "consequence": (
            "This run may be preserved as history. It may not enter reports/, the ledger, or any "
            "synthesis. Nothing here grades the substance of the run; escalation is to the owner only."
        ),
        "voided_at": now or utc_now(),
        "certification": CERTIFICATION,
    }
    record["void_sha256"] = canonical_sha256(record)
    return record


def write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# CLI — a chat or agent run satisfies the gate by submitting its checklist
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Submit a Secretary pre-run checklist and obtain the pass token. Procedure only."
    )
    parser.add_argument("--checklist", required=True, help="path to a secretary_pre_run_checklist JSON artifact")
    parser.add_argument("--token-out", help="where to write the issued pass token")
    args = parser.parse_args(argv)
    try:
        checklist = json.loads(Path(args.checklist).expanduser().read_text(encoding="utf-8"))
        token = open_gate(checklist)
    except (SecretaryGateError, OSError, ValueError) as exc:
        print(f"SECRETARY PRE-RUN GATE REFUSED: {exc}", file=sys.stderr)
        print("No run is lawful until the checklist is satisfied and recorded.", file=sys.stderr)
        return 7
    if args.token_out:
        write_json(Path(args.token_out).expanduser(), token)
        print(f"SECRETARY PRE-RUN GATE PASS: {args.token_out}")
    else:
        print(json.dumps(token, indent=2, sort_keys=True))
    print("Procedure only. Nothing was certified, and no substance was read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
