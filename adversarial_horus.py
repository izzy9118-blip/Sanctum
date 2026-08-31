#!/usr/bin/env python3
"""Mandatory adversarial Minister -> Horus call."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable

from minister_horus import (
    ACQUISITION_PROTOCOL,
    CANONICAL_ACQUISITION_ENGINE,
    CANONICAL_ACQUISITION_PATH,
    HorusExchangeError,
    SOURCE_SELECTION_RULE,
    TIERS,
)
from source_absence import SourceStateError, validate_source_states

PROVISIONAL_RECORD_TYPE = "minister_provisional_judgment"
ADVERSARIAL_QUERY_RECORD_TYPE = "minister_horus_adversarial_query"
RESPONSE_RECORD_TYPE = "horus_query_response"
RESPONSE_STATUSES = {"GATHERED", "PARTIALLY_GATHERED", "NOT_GATHERED"}
PROPOSITION_KINDS = {"documented_finding", "supported_inference", "working_hypothesis"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HorusExchangeError(message)


def _git_sha(value: Any, field: str) -> str:
    _require(isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value), f"{field} must be a 40-character lowercase git SHA")
    return value


def validate_provisional_judgment(record: Dict[str, Any]) -> Dict[str, Any]:
    _require(isinstance(record, dict), "provisional judgment must be an object")
    _require(record.get("record_type") == PROVISIONAL_RECORD_TYPE, f"record_type must be {PROVISIONAL_RECORD_TYPE}")
    for field in ("inquiry_id", "minister_id"):
        _require(isinstance(record.get(field), str) and record[field].strip(), f"{field} is required")
    propositions = record.get("propositions")
    _require(isinstance(propositions, list) and propositions, "provisional judgment must contain at least one proposition")
    seen = set()
    for i, p in enumerate(propositions):
        _require(isinstance(p, dict), f"propositions[{i}] must be an object")
        pid = p.get("proposition_id")
        _require(isinstance(pid, str) and pid.startswith("P-") and pid.strip(), f"propositions[{i}].proposition_id is invalid")
        _require(pid not in seen, f"duplicate provisional proposition_id: {pid}")
        seen.add(pid)
        _require(isinstance(p.get("claim"), str) and p["claim"].strip(), f"propositions[{i}].claim is required")
        _require(p.get("kind") in PROPOSITION_KINDS, f"propositions[{i}].kind is invalid")
        _require(isinstance(p.get("disconfirmation_need"), str) and p["disconfirmation_need"].strip(), f"propositions[{i}].disconfirmation_need is required")
        _require(isinstance(p.get("why_it_matters"), str) and p["why_it_matters"].strip(), f"propositions[{i}].why_it_matters is required")
        tiers = p.get("acceptable_tiers", [])
        _require(isinstance(tiers, list) and all(t in TIERS for t in tiers), f"propositions[{i}].acceptable_tiers contains an invalid tier")
    provenance = record.get("provenance")
    _require(isinstance(provenance, dict), "provisional provenance is required")
    _require(provenance.get("produced_by") == record["minister_id"], "provisional provenance.produced_by must equal minister_id")
    _git_sha(provenance.get("repository_commit"), "provisional provenance.repository_commit")
    return record


def build_adversarial_query(provisional: Dict[str, Any], investigative_query: Dict[str, Any] | None = None) -> Dict[str, Any]:
    validate_provisional_judgment(provisional)
    propositions = provisional["propositions"]
    investigative_original_t1 = any(
        item.get("original_language_required") is True
        and (not item.get("acceptable_tiers") or "T1" in item.get("acceptable_tiers", []))
        for item in (investigative_query or {}).get("source_requirements", [])
        if isinstance(item, dict)
    )
    seed = json.dumps({
        "inquiry_id": provisional["inquiry_id"],
        "minister_id": provisional["minister_id"],
        "propositions": propositions,
        "principal_scope": list((investigative_query or {}).get("principal_scope") or []),
        "time_scope": dict((investigative_query or {}).get("time_scope") or {}),
    }, sort_keys=True, separators=(",", ":")).encode()
    short = hashlib.sha256(seed).hexdigest()[:12].upper()
    query = {
        "record_type": ADVERSARIAL_QUERY_RECORD_TYPE,
        "query_id": f"MHAQ-{short}",
        "inquiry_id": provisional["inquiry_id"],
        "minister_id": provisional["minister_id"],
        "provisional_propositions": [{"proposition_id": p["proposition_id"], "claim": p["claim"], "kind": p["kind"]} for p in propositions],
        "information_needed": [p["disconfirmation_need"] for p in propositions],
        "source_requirements": [{"proposition_id": p["proposition_id"], "requirement": p["disconfirmation_need"], "rationale": p["why_it_matters"], "acceptable_tiers": p.get("acceptable_tiers", []), "original_language_required": bool(p.get("original_language_required", False) or investigative_original_t1)} for p in propositions],
        "specific_document_requests": [],
        "principal_scope": list((investigative_query or {}).get("principal_scope") or []),
        "time_scope": dict((investigative_query or {}).get("time_scope") or {}),
        "reason_for_request": "Seek documentary ground capable of weakening, qualifying, or overturning the minister's stated provisional propositions before final judgment.",
        "source_selection_rule": SOURCE_SELECTION_RULE,
        "source_absence_taxonomy": "HORUS-SOURCE-STATE-1.0",
        "provenance": dict(provisional["provenance"]),
    }
    return validate_adversarial_query(query)


def validate_adversarial_query(query: Dict[str, Any]) -> Dict[str, Any]:
    _require(isinstance(query, dict), "adversarial query must be an object")
    _require(query.get("record_type") == ADVERSARIAL_QUERY_RECORD_TYPE, f"record_type must be {ADVERSARIAL_QUERY_RECORD_TYPE}")
    _require(isinstance(query.get("query_id"), str) and query["query_id"].startswith("MHAQ-"), "adversarial query_id must begin MHAQ-")
    for field in ("inquiry_id", "minister_id", "reason_for_request"):
        _require(isinstance(query.get(field), str) and query[field].strip(), f"{field} is required")
    _require(query.get("source_selection_rule") == SOURCE_SELECTION_RULE, "adversarial call may not transfer source-selection authority from Horus")
    query["source_absence_taxonomy"] = "HORUS-SOURCE-STATE-1.0"
    props = query.get("provisional_propositions")
    _require(isinstance(props, list) and props, "provisional_propositions must be non-empty")
    prop_ids = set()
    for i, p in enumerate(props):
        _require(isinstance(p, dict), f"provisional_propositions[{i}] must be an object")
        pid = p.get("proposition_id")
        _require(isinstance(pid, str) and pid.startswith("P-"), f"provisional_propositions[{i}].proposition_id is invalid")
        _require(pid not in prop_ids, f"duplicate provisional proposition_id: {pid}")
        prop_ids.add(pid)
        _require(isinstance(p.get("claim"), str) and p["claim"].strip(), f"provisional_propositions[{i}].claim is required")
        _require(p.get("kind") in PROPOSITION_KINDS, f"provisional_propositions[{i}].kind is invalid")
    needs = query.get("information_needed")
    _require(isinstance(needs, list) and len(needs) == len(props) and all(isinstance(v, str) and v.strip() for v in needs), "information_needed must contain one non-empty disconfirmation need per proposition")
    requirements = query.get("source_requirements")
    _require(isinstance(requirements, list) and len(requirements) == len(props), "source_requirements must contain one entry per provisional proposition")
    requirement_ids = set()
    original_t1 = False
    for i, req in enumerate(requirements):
        _require(isinstance(req, dict), f"source_requirements[{i}] must be an object")
        pid = req.get("proposition_id")
        _require(pid in prop_ids and pid not in requirement_ids, f"source_requirements[{i}] proposition binding invalid")
        requirement_ids.add(pid)
        for field in ("requirement", "rationale"):
            _require(isinstance(req.get(field), str) and req[field].strip(), f"source_requirements[{i}].{field} is required")
        tiers = req.get("acceptable_tiers", [])
        _require(isinstance(tiers, list) and all(t in TIERS for t in tiers), f"source_requirements[{i}].acceptable_tiers contains an invalid tier")
        if req.get("original_language_required") is True and (not tiers or "T1" in tiers):
            original_t1 = True
    _require(requirement_ids == prop_ids, "every provisional proposition must receive exactly one adversarial source requirement")
    principal_scope = query.get("principal_scope", [])
    _require(isinstance(principal_scope, list) and all(isinstance(x, str) and x.strip() for x in principal_scope), "principal_scope must be a string list")
    _require(len(set(principal_scope)) == len(principal_scope), "principal_scope must not contain duplicates")
    if original_t1:
        _require(bool(principal_scope), "original-language T1 adversarial acquisition requires principal_scope inherited from the investigative query")
    time_scope = query.get("time_scope", {})
    _require(isinstance(time_scope, dict), "time_scope must be an object")
    provenance = query.get("provenance")
    _require(isinstance(provenance, dict), "adversarial provenance is required")
    _require(provenance.get("produced_by") == query["minister_id"], "adversarial provenance.produced_by must equal minister_id")
    _git_sha(provenance.get("repository_commit"), "adversarial provenance.repository_commit")
    return query


def _validate_acquisition(response: Dict[str, Any]) -> None:
    acquisition = response.get("acquisition")
    _require(isinstance(acquisition, dict), "Horus adversarial response requires acquisition receipt")
    _require(acquisition.get("protocol") == ACQUISITION_PROTOCOL, f"acquisition.protocol must be {ACQUISITION_PROTOCOL}")
    digest = acquisition.get("plan_sha256", "")
    _require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "acquisition.plan_sha256 must be a lowercase sha256")
    for field in ("principal_profiles", "date_normalizations", "search_attempts", "requirements"):
        _require(isinstance(acquisition.get(field), list), f"acquisition.{field} must be a list")
    runtime = acquisition.get("runtime")
    _require(isinstance(runtime, dict), "acquisition.runtime is required")
    _require(runtime.get("engine") == CANONICAL_ACQUISITION_ENGINE, "Horus adversarial response was not produced by the canonical acquisition engine")
    _require(runtime.get("engine_path") == CANONICAL_ACQUISITION_PATH, "Horus adversarial response acquisition engine path is not canonical")
    _require(runtime.get("mode") in {"LIVE", "FIXTURE"}, "acquisition.runtime.mode must be LIVE or FIXTURE")


def validate_adversarial_response(query: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    validate_adversarial_query(query)
    _require(isinstance(response, dict), "Horus adversarial response must be an object")
    _require(response.get("record_type") == RESPONSE_RECORD_TYPE, f"response.record_type must be {RESPONSE_RECORD_TYPE}")
    _require(response.get("query_id") == query["query_id"], "Horus adversarial response query_id does not match the request")
    _require(response.get("requesting_minister") == query["minister_id"], "Horus adversarial response requesting_minister does not match the request")
    _require(response.get("request_as_received") == query, "Horus adversarial response must preserve the request exactly as received")
    _require(response.get("status") in RESPONSE_STATUSES, "Horus response status is invalid")
    _require(response.get("source_absence_taxonomy") == "HORUS-SOURCE-STATE-1.0", "Horus adversarial response must declare source-absence taxonomy HORUS-SOURCE-STATE-1.0")
    _require(response.get("completeness") == "PENDING_PROBE", "Horus may not self-certify adversarial completeness")
    _validate_acquisition(response)

    searched, used, rejected = response.get("sources_searched"), response.get("sources_used"), response.get("sources_rejected")
    _require(isinstance(searched, list) and isinstance(used, list) and isinstance(rejected, list), "Horus source trails must be lists")
    def refs(records: Iterable[Dict[str, Any]], label: str) -> set[str]:
        found = set()
        for i, source in enumerate(records):
            _require(isinstance(source, dict), f"{label}[{i}] must be an object")
            for field in ("source_ref", "document_identity", "issuer", "source_tier", "retrieval_date"):
                _require(source.get(field) not in (None, ""), f"{label}[{i}].{field} is required")
            _require(source["source_tier"] in TIERS, f"{label}[{i}].source_tier is invalid")
            ref = source["source_ref"]
            _require(ref not in found, f"duplicate {label} source_ref: {ref}")
            found.add(ref)
        return found
    searched_refs, used_refs, rejected_refs = refs(searched, "sources_searched"), refs(used, "sources_used"), refs(rejected, "sources_rejected")
    _require(used_refs <= searched_refs, "every adversarial source used must be disclosed as searched")
    _require(rejected_refs <= searched_refs, "every adversarial source rejected must be disclosed as searched")
    for i, source in enumerate(rejected):
        _require(isinstance(source.get("rejection_reason"), str) and source["rejection_reason"].strip(), f"sources_rejected[{i}].rejection_reason is required")
    returned, unfilled = response.get("records_returned"), response.get("unfilled_requests")
    _require(isinstance(returned, list) and isinstance(unfilled, list), "records_returned and unfilled_requests must be lists")
    try:
        validate_source_states(response)
    except SourceStateError as exc:
        raise HorusExchangeError(f"source-absence taxonomy violation: {exc}") from exc
    if response["status"] == "GATHERED":
        _require(not unfilled, "GATHERED adversarial response may not contain unfilled_requests")
    elif response["status"] == "PARTIALLY_GATHERED":
        _require(bool(returned) and bool(unfilled), "PARTIALLY_GATHERED adversarial response requires returned and unfilled records")
    else:
        _require(not returned and bool(unfilled), "NOT_GATHERED adversarial response must contain only explicit unfilled requests")
    provenance = response.get("provenance")
    _require(isinstance(provenance, dict), "response provenance is required")
    _git_sha(provenance.get("horus_repository_commit"), "response provenance.horus_repository_commit")
    _require(isinstance(provenance.get("generated_at"), str) and provenance["generated_at"].strip(), "response provenance.generated_at is required")
    return response


def required_adversarial_horus_call(provisional: Dict[str, Any], horus_gather: Callable[[Dict[str, Any]], Dict[str, Any]], investigative_query: Dict[str, Any] | None = None) -> tuple[Dict[str, Any], Dict[str, Any]]:
    query = build_adversarial_query(provisional, investigative_query=investigative_query)
    response = horus_gather(json.loads(json.dumps(query)))
    return query, validate_adversarial_response(query, response)


def adversarial_exchange_digest(query: Dict[str, Any], response: Dict[str, Any]) -> str:
    validate_adversarial_response(query, response)
    payload = json.dumps({"query": query, "response": response}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_adversarial_exchange(root: Path, query: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, str]:
    validate_adversarial_response(query, response)
    directory = Path(root) / query["inquiry_id"] / query["minister_id"]
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / f"{query['query_id']}.request.json"
    response_path = directory / f"{query['query_id']}.response.json"
    request_path.write_text(json.dumps(query, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    response_path.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"request": str(request_path), "response": str(response_path), "sha256": adversarial_exchange_digest(query, response)}
