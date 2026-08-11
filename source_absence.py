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

def _acquisition_attempts(response: Dict[str, Any]) -> tuple[set[str], list[dict[str, Any]]]:
    acquisition = response.get("acquisition")
    _require(isinstance(acquisition, dict), "Horus response requires acquisition receipt")
    _require(acquisition.get("protocol") == "HORUS-ACQUISITION-1.0", "Horus acquisition protocol must be HORUS-ACQUISITION-1.0")
    runtime = acquisition.get("runtime")
    _require(isinstance(runtime, dict), "Horus acquisition receipt requires runtime provenance")
    _require(runtime.get("engine") == "HORUS_CANONICAL_ACQUISITION_ENGINE", "Horus acquisition receipt must come from canonical engine")
    _require(runtime.get("engine_path") == "runtime/gather.py", "Horus acquisition engine path must be runtime/gather.py")
    attempts = acquisition.get("search_attempts")
    _require(isinstance(attempts, list), "Horus acquisition receipt search_attempts must be a list")
    ids: set[str] = set()
    for i, attempt in enumerate(attempts):
        _require(isinstance(attempt, dict), f"acquisition.search_attempts[{i}] must be an object")
        attempt_id = attempt.get("attempt_id")
        _require(isinstance(attempt_id, str) and attempt_id, f"acquisition.search_attempts[{i}].attempt_id is required")
        _require(attempt_id not in ids, f"duplicate acquisition attempt id: {attempt_id}")
        ids.add(attempt_id)
    requirements = acquisition.get("requirements")
    _require(isinstance(requirements, list), "Horus acquisition receipt requirements must be a list")
    return ids, requirements

def validate_source_states(response: Dict[str, Any]) -> Dict[str, Any]:
    searched_refs = {s.get("source_ref") for s in response.get("sources_searched", []) if isinstance(s, dict)}
    used_refs = {s.get("source_ref") for s in response.get("sources_used", []) if isinstance(s, dict)}
    attempt_ids, acquisition_requirements = _acquisition_attempts(response)

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
        need = missing.get("information_need")
        _require(state in UNRESOLVED_STATES, f"unfilled_requests[{i}].evidence_state invalid or missing")
        refs = set(missing.get("searched_source_refs") or [])
        attempt_refs = set(missing.get("searched_attempt_refs") or [])
        _require(refs <= searched_refs, f"unfilled_requests[{i}] cites an unsearched documentary source")
        _require(attempt_refs <= attempt_ids, f"unfilled_requests[{i}] cites an acquisition attempt not present in the receipt")
        if state == "NOT_SEARCHED":
            _require(not refs, f"unfilled_requests[{i}] NOT_SEARCHED may not cite searched_source_refs")
            _require(not attempt_refs, f"unfilled_requests[{i}] NOT_SEARCHED may not cite searched_attempt_refs")
        else:
            _require(bool(attempt_refs), f"unfilled_requests[{i}] {state} requires searched_attempt_refs")
        if state == "SEARCHED_NOT_FOUND":
            matching = [r for r in acquisition_requirements if isinstance(r, dict) and r.get("information_need") == need]
            if matching:
                _require(all(r.get("minimum_protocol_satisfied") is True for r in matching),
                         f"unfilled_requests[{i}] SEARCHED_NOT_FOUND requires a completed reachable acquisition protocol")
        _require(missing.get("absence_claim") in (None, False),
                 f"unfilled_requests[{i}] unresolved state may not assert absence")

    _require(all(x.get("evidence_state") != "DOCUMENTED_ABSENCE" for x in response.get("unfilled_requests", [])),
             "DOCUMENTED_ABSENCE belongs in records_returned, never unfilled_requests")
    return response
