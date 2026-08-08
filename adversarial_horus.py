#!/usr/bin/env python3
"""Mandatory adversarial Minister -> Horus call.

A reasoned minister first forms a provisional judgment.  Every provisional
proposition must state what documentary information could weaken, qualify, or
overturn it.  This module deterministically turns those stated vulnerabilities
into a distinct adversarial Horus query, validates the return, and preserves the
same source-selection wall as the ordinary investigative call.

The hub does not invent an objection for the minister and Horus does not judge.
The minister names the vulnerability; Horus gathers qualifying ground; the
minister must confront that ground before final judgment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable

from minister_horus import HorusExchangeError, SOURCE_SELECTION_RULE, TIERS

PROVISIONAL_RECORD_TYPE = "minister_provisional_judgment"
ADVERSARIAL_QUERY_RECORD_TYPE = "minister_horus_adversarial_query"
RESPONSE_RECORD_TYPE = "horus_query_response"
RESPONSE_STATUSES = {"GATHERED", "PARTIALLY_GATHERED", "NOT_GATHERED"}
PROPOSITION_KINDS = {"documented_finding", "supported_inference", "working_hypothesis"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HorusExchangeError(message)


def _git_sha(value: Any, field: str) -> str:
    _require(isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value),
             f"{field} must be a 40-character lowercase git SHA")
    return value


def validate_provisional_judgment(record: Dict[str, Any]) -> Dict[str, Any]:
    _require(isinstance(record, dict), "provisional judgment must be an object")
    _require(record.get("record_type") == PROVISIONAL_RECORD_TYPE,
             f"record_type must be {PROVISIONAL_RECORD_TYPE}")
    for field in ("inquiry_id", "minister_id"):
        _require(isinstance(record.get(field), str) and record[field].strip(), f"{field} is required")

    propositions = record.get("propositions")
    _require(isinstance(propositions, list) and propositions,
             "provisional judgment must contain at least one proposition")
    seen = set()
    for index, proposition in enumerate(propositions):
        _require(isinstance(proposition, dict), f"propositions[{index}] must be an object")
        pid = proposition.get("proposition_id")
        _require(isinstance(pid, str) and pid.startswith("P-") and pid.strip(),
                 f"propositions[{index}].proposition_id is invalid")
        _require(pid not in seen, f"duplicate provisional proposition_id: {pid}")
        seen.add(pid)
        _require(isinstance(proposition.get("claim"), str) and proposition["claim"].strip(),
                 f"propositions[{index}].claim is required")
        _require(proposition.get("kind") in PROPOSITION_KINDS,
                 f"propositions[{index}].kind is invalid")
        _require(isinstance(proposition.get("disconfirmation_need"), str)
                 and proposition["disconfirmation_need"].strip(),
                 f"propositions[{index}].disconfirmation_need is required")
        _require(isinstance(proposition.get("why_it_matters"), str)
                 and proposition["why_it_matters"].strip(),
                 f"propositions[{index}].why_it_matters is required")
        tiers = proposition.get("acceptable_tiers", [])
        _require(isinstance(tiers, list) and all(t in TIERS for t in tiers),
                 f"propositions[{index}].acceptable_tiers contains an invalid tier")

    provenance = record.get("provenance")
    _require(isinstance(provenance, dict), "provisional provenance is required")
    _require(provenance.get("produced_by") == record["minister_id"],
             "provisional provenance.produced_by must equal minister_id")
    _git_sha(provenance.get("repository_commit"), "provisional provenance.repository_commit")
    return record


def build_adversarial_query(provisional: Dict[str, Any]) -> Dict[str, Any]:
    """Build the adversarial query deterministically from minister-stated vulnerabilities."""
    validate_provisional_judgment(provisional)
    propositions = provisional["propositions"]
    digest_seed = json.dumps(
        {
            "inquiry_id": provisional["inquiry_id"],
            "minister_id": provisional["minister_id"],
            "propositions": propositions,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    short = hashlib.sha256(digest_seed).hexdigest()[:12].upper()
    query = {
        "record_type": ADVERSARIAL_QUERY_RECORD_TYPE,
        "query_id": f"MHAQ-{short}",
        "inquiry_id": provisional["inquiry_id"],
        "minister_id": provisional["minister_id"],
        "provisional_propositions": [
            {
                "proposition_id": p["proposition_id"],
                "claim": p["claim"],
                "kind": p["kind"],
            }
            for p in propositions
        ],
        "information_needed": [p["disconfirmation_need"] for p in propositions],
        "source_requirements": [
            {
                "proposition_id": p["proposition_id"],
                "requirement": p["disconfirmation_need"],
                "rationale": p["why_it_matters"],
                "acceptable_tiers": p.get("acceptable_tiers", []),
                "original_language_required": bool(p.get("original_language_required", False)),
            }
            for p in propositions
        ],
        "specific_document_requests": [],
        "reason_for_request": (
            "Seek documentary ground capable of weakening, qualifying, or overturning "
            "the minister's stated provisional propositions before final judgment."
        ),
        "source_selection_rule": SOURCE_SELECTION_RULE,
        "provenance": dict(provisional["provenance"]),
    }
    return validate_adversarial_query(query)


def validate_adversarial_query(query: Dict[str, Any]) -> Dict[str, Any]:
    _require(isinstance(query, dict), "adversarial query must be an object")
    _require(query.get("record_type") == ADVERSARIAL_QUERY_RECORD_TYPE,
             f"record_type must be {ADVERSARIAL_QUERY_RECORD_TYPE}")
    _require(isinstance(query.get("query_id"), str) and query["query_id"].startswith("MHAQ-"),
             "adversarial query_id must begin MHAQ-")
    for field in ("inquiry_id", "minister_id", "reason_for_request"):
        _require(isinstance(query.get(field), str) and query[field].strip(), f"{field} is required")
    _require(query.get("source_selection_rule") == SOURCE_SELECTION_RULE,
             "adversarial call may not transfer source-selection authority from Horus")

    props = query.get("provisional_propositions")
    _require(isinstance(props, list) and props, "provisional_propositions must be non-empty")
    prop_ids = set()
    for index, prop in enumerate(props):
        _require(isinstance(prop, dict), f"provisional_propositions[{index}] must be an object")
        pid = prop.get("proposition_id")
        _require(isinstance(pid, str) and pid.startswith("P-"),
                 f"provisional_propositions[{index}].proposition_id is invalid")
        _require(pid not in prop_ids, f"duplicate provisional proposition_id: {pid}")
        prop_ids.add(pid)
        _require(isinstance(prop.get("claim"), str) and prop["claim"].strip(),
                 f"provisional_propositions[{index}].claim is required")
        _require(prop.get("kind") in PROPOSITION_KINDS,
                 f"provisional_propositions[{index}].kind is invalid")

    needs = query.get("information_needed")
    _require(isinstance(needs, list) and len(needs) == len(props)
             and all(isinstance(v, str) and v.strip() for v in needs),
             "information_needed must contain one non-empty disconfirmation need per proposition")

    requirements = query.get("source_requirements")
    _require(isinstance(requirements, list) and len(requirements) == len(props),
             "source_requirements must contain one entry per provisional proposition")
    requirement_ids = set()
    for index, req in enumerate(requirements):
        _require(isinstance(req, dict), f"source_requirements[{index}] must be an object")
        pid = req.get("proposition_id")
        _require(pid in prop_ids, f"source_requirements[{index}] references an unknown proposition")
        _require(pid not in requirement_ids, f"duplicate adversarial requirement for proposition {pid}")
        requirement_ids.add(pid)
        for field in ("requirement", "rationale"):
            _require(isinstance(req.get(field), str) and req[field].strip(),
                     f"source_requirements[{index}].{field} is required")
        tiers = req.get("acceptable_tiers", [])
        _require(isinstance(tiers, list) and all(t in TIERS for t in tiers),
                 f"source_requirements[{index}].acceptable_tiers contains an invalid tier")
    _require(requirement_ids == prop_ids,
             "every provisional proposition must receive exactly one adversarial source requirement")

    provenance = query.get("provenance")
    _require(isinstance(provenance, dict), "adversarial provenance is required")
    _require(provenance.get("produced_by") == query["minister_id"],
             "adversarial provenance.produced_by must equal minister_id")
    _git_sha(provenance.get("repository_commit"), "adversarial provenance.repository_commit")
    return query


def validate_adversarial_response(query: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the Horus source trail for a distinct adversarial query."""
    validate_adversarial_query(query)
    _require(isinstance(response, dict), "Horus adversarial response must be an object")
    _require(response.get("record_type") == RESPONSE_RECORD_TYPE,
             f"response.record_type must be {RESPONSE_RECORD_TYPE}")
    _require(response.get("query_id") == query["query_id"],
             "Horus adversarial response query_id does not match the request")
    _require(response.get("requesting_minister") == query["minister_id"],
             "Horus adversarial response requesting_minister does not match the request")
    _require(response.get("status") in RESPONSE_STATUSES, "Horus response status is invalid")
    _require(response.get("completeness") == "PENDING_PROBE",
             "Horus may not self-certify adversarial completeness")

    searched = response.get("sources_searched")
    used = response.get("sources_used")
    rejected = response.get("sources_rejected")
    _require(isinstance(searched, list), "sources_searched must be a list")
    _require(isinstance(used, list), "sources_used must be a list")
    _require(isinstance(rejected, list), "sources_rejected must be a list")

    def refs(records: Iterable[Dict[str, Any]], label: str) -> set[str]:
        found = set()
        for index, source in enumerate(records):
            _require(isinstance(source, dict), f"{label}[{index}] must be an object")
            for field in ("source_ref", "document_identity", "issuer", "source_tier", "retrieval_date"):
                _require(source.get(field) not in (None, ""), f"{label}[{index}].{field} is required")
            _require(source["source_tier"] in TIERS, f"{label}[{index}].source_tier is invalid")
            ref = source["source_ref"]
            _require(ref not in found, f"duplicate {label} source_ref: {ref}")
            found.add(ref)
        return found

    searched_refs = refs(searched, "sources_searched")
    used_refs = refs(used, "sources_used")
    rejected_refs = refs(rejected, "sources_rejected")
    _require(used_refs <= searched_refs, "every adversarial source used must be disclosed as searched")
    _require(rejected_refs <= searched_refs, "every adversarial source rejected must be disclosed as searched")
    for index, source in enumerate(rejected):
        _require(isinstance(source.get("rejection_reason"), str) and source["rejection_reason"].strip(),
                 f"sources_rejected[{index}].rejection_reason is required")

    returned = response.get("records_returned")
    unfilled = response.get("unfilled_requests")
    _require(isinstance(returned, list), "records_returned must be a list")
    _require(isinstance(unfilled, list), "unfilled_requests must be a list")
    for index, record in enumerate(returned):
        _require(isinstance(record, dict), f"records_returned[{index}] must be an object")
        _require(isinstance(record.get("information_need"), str) and record["information_need"].strip(),
                 f"records_returned[{index}].information_need is required")
        source_refs = record.get("source_refs")
        _require(isinstance(source_refs, list) and source_refs,
                 f"records_returned[{index}].source_refs must be non-empty")
        _require(set(source_refs) <= used_refs,
                 f"records_returned[{index}] cites a source Horus did not record as used")
    for index, missing in enumerate(unfilled):
        _require(isinstance(missing, dict), f"unfilled_requests[{index}] must be an object")
        _require(isinstance(missing.get("information_need"), str) and missing["information_need"].strip(),
                 f"unfilled_requests[{index}].information_need is required")
        _require(isinstance(missing.get("reason"), str) and missing["reason"].strip(),
                 f"unfilled_requests[{index}].reason is required")

    if response["status"] == "GATHERED":
        _require(not unfilled, "GATHERED adversarial response may not contain unfilled_requests")
    elif response["status"] == "PARTIALLY_GATHERED":
        _require(bool(returned) and bool(unfilled),
                 "PARTIALLY_GATHERED adversarial response requires returned and unfilled records")
    else:
        _require(not returned and bool(unfilled),
                 "NOT_GATHERED adversarial response must contain only explicit unfilled requests")

    provenance = response.get("provenance")
    _require(isinstance(provenance, dict), "response provenance is required")
    _git_sha(provenance.get("horus_repository_commit"), "response provenance.horus_repository_commit")
    _require(isinstance(provenance.get("generated_at"), str) and provenance["generated_at"].strip(),
             "response provenance.generated_at is required")
    return response


def required_adversarial_horus_call(
    provisional: Dict[str, Any],
    horus_gather: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Hard seam: no final judgment may bypass this call in a reasoned run."""
    query = build_adversarial_query(provisional)
    response = horus_gather(json.loads(json.dumps(query)))
    return query, validate_adversarial_response(query, response)


def adversarial_exchange_digest(query: Dict[str, Any], response: Dict[str, Any]) -> str:
    validate_adversarial_response(query, response)
    payload = json.dumps({"query": query, "response": response}, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_adversarial_exchange(root: Path, query: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, str]:
    validate_adversarial_response(query, response)
    directory = Path(root) / query["inquiry_id"] / query["minister_id"]
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / f"{query['query_id']}.request.json"
    response_path = directory / f"{query['query_id']}.response.json"
    request_path.write_text(json.dumps(query, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    response_path.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "request": str(request_path),
        "response": str(response_path),
        "sha256": adversarial_exchange_digest(query, response),
    }
