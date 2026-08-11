#!/usr/bin/env python3
"""Mandatory Minister -> Horus investigative call boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable

from source_absence import SourceStateError, validate_source_states

QUERY_RECORD_TYPE = "minister_horus_query"
RESPONSE_RECORD_TYPE = "horus_query_response"
SOURCE_SELECTION_RULE = "HORUS_RETAINS_SOURCE_SELECTION_INDEPENDENCE_EXCEPT_EXPLICIT_DOCUMENT_REQUESTS"
RESPONSE_STATUSES = {"GATHERED", "PARTIALLY_GATHERED", "NOT_GATHERED"}
TIERS = {"T1", "T2", "T3", "T4", "T5"}
ACQUISITION_PROTOCOL = "HORUS-ACQUISITION-1.0"
CANONICAL_ACQUISITION_ENGINE = "HORUS_CANONICAL_ACQUISITION_ENGINE"
CANONICAL_ACQUISITION_PATH = "runtime/gather.py"

class HorusExchangeError(ValueError):
    pass

def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HorusExchangeError(message)

def _nonempty_strings(values: Any, field: str) -> list[str]:
    _require(isinstance(values, list) and values, f"{field} must be a non-empty list")
    _require(all(isinstance(v, str) and v.strip() for v in values), f"{field} must contain only non-empty strings")
    return values

def validate_query(query: Dict[str, Any]) -> Dict[str, Any]:
    _require(isinstance(query, dict), "query must be an object")
    _require(query.get("record_type") == QUERY_RECORD_TYPE, f"record_type must be {QUERY_RECORD_TYPE}")
    for field in ("query_id", "inquiry_id", "minister_id", "reason_for_request"):
        _require(isinstance(query.get(field), str) and query[field].strip(), f"{field} is required")
    _nonempty_strings(query.get("information_needed"), "information_needed")
    requirements = query.get("source_requirements")
    _require(isinstance(requirements, list) and requirements, "source_requirements must be a non-empty list")
    for index, requirement in enumerate(requirements):
        _require(isinstance(requirement, dict), f"source_requirements[{index}] must be an object")
        for field in ("requirement", "rationale"):
            _require(isinstance(requirement.get(field), str) and requirement[field].strip(), f"source_requirements[{index}].{field} is required")
        tiers = requirement.get("acceptable_tiers", [])
        _require(isinstance(tiers, list) and all(t in TIERS for t in tiers), f"source_requirements[{index}].acceptable_tiers contains an invalid tier")
    rule = query.get("source_selection_rule", SOURCE_SELECTION_RULE)
    _require(rule == SOURCE_SELECTION_RULE, "minister may specify evidentiary requirements but may not take source-selection authority from Horus")
    query["source_selection_rule"] = SOURCE_SELECTION_RULE
    query["source_absence_taxonomy"] = "HORUS-SOURCE-STATE-1.0"
    provenance = query.get("provenance")
    _require(isinstance(provenance, dict), "provenance is required")
    _require(isinstance(provenance.get("produced_by"), str) and provenance["produced_by"].strip(), "provenance.produced_by is required")
    commit = provenance.get("repository_commit", "")
    _require(isinstance(commit, str) and len(commit) == 40 and all(c in "0123456789abcdef" for c in commit), "provenance.repository_commit must be a 40-character lowercase git SHA")
    return query

def _validate_acquisition(response: Dict[str, Any]) -> None:
    acquisition = response.get("acquisition")
    _require(isinstance(acquisition, dict), "Horus response requires acquisition receipt")
    _require(acquisition.get("protocol") == ACQUISITION_PROTOCOL, f"acquisition.protocol must be {ACQUISITION_PROTOCOL}")
    digest = acquisition.get("plan_sha256", "")
    _require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "acquisition.plan_sha256 must be a lowercase sha256")
    for field in ("principal_profiles", "date_normalizations", "search_attempts", "requirements"):
        _require(isinstance(acquisition.get(field), list), f"acquisition.{field} must be a list")
    runtime = acquisition.get("runtime")
    _require(isinstance(runtime, dict), "acquisition.runtime is required")
    _require(runtime.get("engine") == CANONICAL_ACQUISITION_ENGINE, "Horus response was not produced by the canonical acquisition engine")
    _require(runtime.get("engine_path") == CANONICAL_ACQUISITION_PATH, "Horus response acquisition engine path is not canonical")
    _require(runtime.get("mode") in {"LIVE", "FIXTURE"}, "acquisition.runtime.mode must be LIVE or FIXTURE")

def validate_response(query: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    validate_query(query)
    _require(isinstance(response, dict), "Horus response must be an object")
    _require(response.get("record_type") == RESPONSE_RECORD_TYPE, f"response.record_type must be {RESPONSE_RECORD_TYPE}")
    _require(response.get("query_id") == query["query_id"], "Horus response query_id does not match the minister request")
    _require(response.get("requesting_minister") == query["minister_id"], "Horus response requesting_minister does not match the request")
    _require(response.get("request_as_received") == query, "Horus response must preserve the minister request exactly as received")
    _require(response.get("status") in RESPONSE_STATUSES, "Horus response status is invalid")
    _require(response.get("source_absence_taxonomy") == "HORUS-SOURCE-STATE-1.0", "Horus response must declare source-absence taxonomy HORUS-SOURCE-STATE-1.0")
    _require(response.get("completeness") == "PENDING_PROBE", "Horus may not self-certify completeness")
    _validate_acquisition(response)

    searched, used, rejected = (response.get("sources_searched"), response.get("sources_used"), response.get("sources_rejected"))
    _require(isinstance(searched, list), "sources_searched must be a list")
    _require(isinstance(used, list), "sources_used must be a list")
    _require(isinstance(rejected, list), "sources_rejected must be a list")

    def source_refs(records: Iterable[Dict[str, Any]], label: str) -> set[str]:
        refs: set[str] = set()
        for index, source in enumerate(records):
            _require(isinstance(source, dict), f"{label}[{index}] must be an object")
            for field in ("source_ref", "document_identity", "issuer", "source_tier", "retrieval_date"):
                _require(source.get(field) not in (None, ""), f"{label}[{index}].{field} is required")
            _require(source["source_tier"] in TIERS, f"{label}[{index}].source_tier is invalid")
            ref = source["source_ref"]
            _require(ref not in refs, f"duplicate {label} source_ref: {ref}")
            refs.add(ref)
        return refs

    searched_refs = source_refs(searched, "sources_searched")
    used_refs = source_refs(used, "sources_used")
    rejected_refs = source_refs(rejected, "sources_rejected")
    _require(used_refs <= searched_refs, "every source used by Horus must also be recorded in sources_searched")
    _require(rejected_refs <= searched_refs, "every rejected source must also be recorded in sources_searched")
    for index, source in enumerate(rejected):
        _require(isinstance(source.get("rejection_reason"), str) and source["rejection_reason"].strip(), f"sources_rejected[{index}].rejection_reason is required")

    returned, unfilled = response.get("records_returned"), response.get("unfilled_requests")
    _require(isinstance(returned, list), "records_returned must be a list")
    _require(isinstance(unfilled, list), "unfilled_requests must be a list")
    for index, record in enumerate(returned):
        _require(isinstance(record, dict), f"records_returned[{index}] must be an object")
        _require(isinstance(record.get("information_need"), str) and record["information_need"].strip(), f"records_returned[{index}].information_need is required")
        refs = record.get("source_refs")
        _require(isinstance(refs, list) and refs, f"records_returned[{index}].source_refs must be non-empty")
        _require(set(refs) <= used_refs, f"records_returned[{index}] cites a source Horus did not record as used")
    for index, missing in enumerate(unfilled):
        _require(isinstance(missing, dict), f"unfilled_requests[{index}] must be an object")
        _require(isinstance(missing.get("information_need"), str) and missing["information_need"].strip(), f"unfilled_requests[{index}].information_need is required")
        _require(isinstance(missing.get("reason"), str) and missing["reason"].strip(), f"unfilled_requests[{index}].reason is required")

    try:
        validate_source_states(response)
    except SourceStateError as exc:
        raise HorusExchangeError(f"source-absence taxonomy violation: {exc}") from exc

    if response["status"] == "GATHERED":
        _require(not unfilled, "GATHERED response may not contain unfilled_requests")
    elif response["status"] == "NOT_GATHERED":
        _require(not returned, "NOT_GATHERED response may not claim returned findings")
        _require(bool(unfilled), "NOT_GATHERED response must state what remained unfilled")
    else:
        _require(bool(returned) and bool(unfilled), "PARTIALLY_GATHERED must contain both returned and unfilled records")

    provenance = response.get("provenance")
    _require(isinstance(provenance, dict), "response provenance is required")
    hcommit = provenance.get("horus_repository_commit", "")
    _require(isinstance(hcommit, str) and len(hcommit) == 40 and all(c in "0123456789abcdef" for c in hcommit), "provenance.horus_repository_commit must be a 40-character lowercase git SHA")
    _require(isinstance(provenance.get("generated_at"), str) and provenance["generated_at"].strip(), "provenance.generated_at is required")
    return response

def required_horus_call(query: Dict[str, Any], horus_gather: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    validate_query(query)
    response = horus_gather(json.loads(json.dumps(query)))
    return validate_response(query, response)

def exchange_digest(query: Dict[str, Any], response: Dict[str, Any]) -> str:
    validate_response(query, response)
    payload = json.dumps({"query": query, "response": response}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def write_exchange(root: Path, query: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, str]:
    validate_response(query, response)
    directory = Path(root) / query["inquiry_id"] / query["minister_id"]
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / f"{query['query_id']}.request.json"
    response_path = directory / f"{query['query_id']}.response.json"
    request_path.write_text(json.dumps(query, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    response_path.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"request": str(request_path), "response": str(response_path), "sha256": exchange_digest(query, response)}
