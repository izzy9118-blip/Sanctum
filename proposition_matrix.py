#!/usr/bin/env python3
"""Hard proposition-aware pre-synthesis gate for Sanctum.

The President performs semantic alignment; code does not infer agreement. Forward
packages carrying MINISTERIAL-SILENCE-001 are validated before inventory construction,
so the President cannot retroactively author a minister's silence.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable, Dict

from ministerial_silence import STANDARD_ID as SILENCE_STANDARD_ID, validate_silence_semantics

MATRIX_RECORD_TYPE = "presidential_proposition_matrix"
ALIGNMENT_AUTHORITY = "PRESIDENTIAL_ALIGNMENT"
CERTIFICATION = "NONE_SELF_CERTIFICATION_PROHIBITED"
STATES = {
    "AFFIRMS", "QUALIFIES", "DISPUTES", "UNCERTAIN",
    "OUTSIDE_GROUND", "NOT_ADDRESSED", "NOT_ASKED",
}
POSITIVE_RELATION_STATES = {"AFFIRMS", "QUALIFIES", "DISPUTES"}
NO_PROPOSITION_STATES = {"OUTSIDE_GROUND", "NOT_ADDRESSED", "NOT_ASKED"}


class PropositionMatrixError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PropositionMatrixError(message)


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_inventory(packages: Dict[str, dict]) -> dict:
    _require(isinstance(packages, dict) and packages, "packages must be a non-empty minister mapping")
    inquiry_ids, inventory, bindings, silence = set(), [], [], []
    for minister_id in sorted(packages):
        package = packages[minister_id]
        _require(isinstance(package, dict), f"package for {minister_id} must be an object")
        _require(package.get("record_type") == "final_judgment_package", f"{minister_id} package is not a final_judgment_package")
        _require(package.get("minister_id") == minister_id, f"{minister_id} package minister identity mismatch")
        inquiry_id = package.get("inquiry_id")
        _require(isinstance(inquiry_id, str) and inquiry_id, f"{minister_id} inquiry_id missing")
        inquiry_ids.add(inquiry_id)

        if package.get("silence_semantics_standard") == SILENCE_STANDARD_ID:
            try:
                validate_silence_semantics(package)
            except ValueError as exc:
                raise PropositionMatrixError(f"{minister_id} silence semantics invalid: {exc}") from exc
            silence.append({
                "minister_id": minister_id,
                "standard": SILENCE_STANDARD_ID,
                "issue_states": package["issue_states"],
            })

        propositions = package.get("propositions")
        _require(isinstance(propositions, list), f"{minister_id} propositions must be a list")
        seen = set()
        for p in propositions:
            _require(isinstance(p, dict), f"{minister_id} proposition must be an object")
            pid = p.get("proposition_id")
            _require(isinstance(pid, str) and pid, f"{minister_id} proposition_id missing")
            _require(pid not in seen, f"duplicate proposition_id within {minister_id}: {pid}")
            seen.add(pid)
            claim, kind = p.get("claim"), p.get("kind")
            _require(isinstance(claim, str) and claim, f"{minister_id}:{pid} claim missing")
            _require(isinstance(kind, str) and kind, f"{minister_id}:{pid} kind missing")
            inventory.append({"minister_id": minister_id, "proposition_id": pid, "kind": kind, "claim": claim})
        bindings.append({"minister_id": minister_id, "package_sha256": canonical_sha256(package)})
    _require(len(inquiry_ids) == 1, "all minister packages must belong to the same inquiry")
    return {
        "record_type": "proposition_inventory",
        "inquiry_id": next(iter(inquiry_ids)),
        "participating_ministers": sorted(packages),
        "package_bindings": bindings,
        "propositions": inventory,
        "ministerial_issue_states": silence,
    }


def validate_matrix(packages: Dict[str, dict], matrix: dict) -> dict:
    inventory = build_inventory(packages)
    _require(isinstance(matrix, dict), "matrix must be an object")
    _require(matrix.get("record_type") == MATRIX_RECORD_TYPE, f"record_type must be {MATRIX_RECORD_TYPE}")
    _require(matrix.get("alignment_authority") == ALIGNMENT_AUTHORITY, "matrix alignment_authority must be PRESIDENTIAL_ALIGNMENT")
    _require(matrix.get("certification") == CERTIFICATION, "matrix may not self-certify correctness")
    _require(matrix.get("inquiry_id") == inventory["inquiry_id"], "matrix inquiry_id mismatch")
    ministers = inventory["participating_ministers"]
    _require(matrix.get("participating_ministers") == ministers, "matrix participating_ministers must exactly match the package set in sorted order")
    _require(matrix.get("package_bindings") == inventory["package_bindings"], "matrix package bindings do not match exact final judgment packages")

    source = {(p["minister_id"], p["proposition_id"]): p for p in inventory["propositions"]}
    seen_refs, row_ids = set(), set()
    rows = matrix.get("rows")
    _require(isinstance(rows, list) and rows, "matrix rows must be non-empty")
    for rindex, row in enumerate(rows):
        _require(isinstance(row, dict), f"rows[{rindex}] must be an object")
        row_id = row.get("matrix_row_id")
        _require(isinstance(row_id, str) and row_id.startswith("ROW-"), f"rows[{rindex}].matrix_row_id is invalid")
        _require(row_id not in row_ids, f"duplicate matrix_row_id: {row_id}")
        row_ids.add(row_id)
        _require(isinstance(row.get("comparison_question"), str) and row["comparison_question"].strip(), f"rows[{rindex}].comparison_question is required")
        entries = row.get("minister_entries")
        _require(isinstance(entries, list) and len(entries) == len(ministers), f"rows[{rindex}] must contain exactly one entry per participating minister")
        entry_ids = [e.get("minister_id") if isinstance(e, dict) else None for e in entries]
        _require(entry_ids == ministers, f"rows[{rindex}] minister entries must appear exactly once in sorted minister order")
        for eindex, entry in enumerate(entries):
            state, minister_id, props = entry.get("state"), entry["minister_id"], entry.get("propositions")
            _require(state in STATES, f"rows[{rindex}].minister_entries[{eindex}].state is invalid")
            _require(isinstance(props, list), f"rows[{rindex}] {minister_id} propositions must be a list")
            if state in POSITIVE_RELATION_STATES:
                _require(bool(props), f"{state} requires at least one proposition reference for {minister_id}")
            if state in NO_PROPOSITION_STATES:
                _require(not props, f"{state} may not carry proposition references for {minister_id}")
            for ref in props:
                _require(isinstance(ref, dict), "matrix proposition reference must be an object")
                key = (minister_id, ref.get("proposition_id"))
                _require(key in source, f"matrix cites unknown proposition {key}")
                original = source[key]
                _require(ref.get("kind") == original["kind"], f"matrix rewrites kind for {key}")
                _require(ref.get("claim") == original["claim"], f"matrix rewrites claim for {key}")
                _require(key not in seen_refs, f"proposition appears in more than one matrix location: {key}")
                seen_refs.add(key)
    missing = set(source) - seen_refs
    _require(not missing, f"matrix omits propositions: {sorted(missing)}")
    return matrix


def required_presidential_matrix_call(packages: Dict[str, dict], president_align: Callable[[dict], dict]) -> dict:
    inventory = build_inventory(packages)
    matrix = president_align(json.loads(json.dumps(inventory)))
    return validate_matrix(packages, matrix)


def synthesis_payload(packages: Dict[str, dict], matrix: dict) -> dict:
    validate_matrix(packages, matrix)
    return {"record_type": "presidential_synthesis_input", "inquiry_id": matrix["inquiry_id"], "proposition_matrix": matrix, "minister_packages": packages, "rule": "SYNTHESIS_MUST_PRESERVE_MATRIX_DISAGREEMENT_AND_SILENCE"}
