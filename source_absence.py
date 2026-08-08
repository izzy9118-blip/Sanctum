#!/usr/bin/env python3
"""Hard epistemic-state validator for Horus query responses."""
from __future__ import annotations

from typing import Any, Dict

RETURNED_STATES = {"SUPPORTED", "CONTRADICTORY_RECORD", "DOCUMENTED_ABSENCE"}
UNRESOLVED_STATES = {
    "NOT_SEARCHED",
    "SEARCHED_NOT_FOUND",
    "SOURCE_EXISTS_NOT_ACQUIRED",
    "SOURCE_ACQUIRED_INCOMPLETE",
}

class SourceStateError(ValueError):
    pass

def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceStateError(message)

def validate_source_states(response: Dict[str, Any]) -> Dict[str, Any]:
    searched_refs = {s.get("source_ref") for s in response.get("sources_searched", []) if isinstance(s, dict)}
    used_refs = {s.get("source_ref") for s in response.get("sources_used", []) if isinstance(s, dict)}

    for i, record in enumerate(response.get("records_returned", [])):
        state = record.get("evidence_state")
        _require(state in RETURNED_STATES, f"records_returned[{i}].evidence_state invalid or missing")
        refs = set(record.get("source_refs") or [])
        _require(bool(refs), f"records_returned[{i}] requires source_refs")
        _require(refs <= used_refs, f"records_returned[{i}] must bind only to sources_used")
        if state == "DOCUMENTED_ABSENCE":
            _require(bool(record.get("absence_scope")), f"records_returned[{i}] DOCUMENTED_ABSENCE requires absence_scope")
            _require(bool(record.get("absence_basis")), f"records_returned[{i}] DOCUMENTED_ABSENCE requires absence_basis")
        else:
            _require(record.get("absence_scope") in (None, ""), f"records_returned[{i}] absence_scope only allowed for DOCUMENTED_ABSENCE")
            _require(record.get("absence_basis") in (None, ""), f"records_returned[{i}] absence_basis only allowed for DOCUMENTED_ABSENCE")

    for i, missing in enumerate(response.get("unfilled_requests", [])):
        state = missing.get("evidence_state")
        _require(state in UNRESOLVED_STATES, f"unfilled_requests[{i}].evidence_state invalid or missing")
        refs = set(missing.get("searched_source_refs") or [])
        _require(refs <= searched_refs, f"unfilled_requests[{i}] cites an unsearched source")
        if state == "NOT_SEARCHED":
            _require(not refs, f"unfilled_requests[{i}] NOT_SEARCHED may not cite searched_source_refs")
        elif state in {"SEARCHED_NOT_FOUND", "SOURCE_EXISTS_NOT_ACQUIRED", "SOURCE_ACQUIRED_INCOMPLETE"}:
            _require(bool(refs), f"unfilled_requests[{i}] {state} requires searched_source_refs")
        _require(missing.get("absence_claim") in (None, False),
                 f"unfilled_requests[{i}] unresolved state may not assert absence")

    # Positive absence must never be encoded as an unresolved request.
    _require(all(x.get("evidence_state") != "DOCUMENTED_ABSENCE" for x in response.get("unfilled_requests", [])),
             "DOCUMENTED_ABSENCE belongs in records_returned, never unfilled_requests")
    return response
