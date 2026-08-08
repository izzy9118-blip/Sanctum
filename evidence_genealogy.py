#!/usr/bin/env python3
"""Hard proposition-level evidence genealogy for forward Assembly reports.

Every substantive proposition must resolve to documentary ground. Ground may come
from a sovereign minister repository or from a validated Horus exchange. Horus-
derived ground is accepted only when the cited source_ref was actually recorded as
used and was attached to a returned record. Minister-repository ground is accepted
only at the exact pinned commit and must identify witness, source, path, and locator.

The validator proves linkage and provenance structure. It does not certify truth.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROP_KINDS = {
    "documented_finding",
    "supported_inference",
    "working_hypothesis",
    "comparative_question",
    "unresolved_uncertainty",
}
SUBSTANTIVE_KINDS = {
    "documented_finding",
    "supported_inference",
    "working_hypothesis",
}
GROUND_ORIGINS = {"horus_exchange", "minister_repository"}


class GenealogyError(ValueError):
    """Raised when a proposition cannot be resolved to its documentary ground."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GenealogyError(message)


def _sha256_object(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _exchange_index(exchanges: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for exchange in exchanges:
        _require(isinstance(exchange, dict), "exchange records must be objects")
        query_id = exchange.get("query_id")
        _require(isinstance(query_id, str) and query_id, "exchange query_id is required")
        _require(query_id not in index, f"duplicate exchange query_id {query_id}")
        response = exchange.get("response")
        _require(isinstance(response, dict), f"exchange {query_id} response is required")
        _require(response.get("query_id") == query_id,
                 f"exchange {query_id} response identity mismatch")
        index[query_id] = exchange
    return index


def _validate_horus_ground(ground: dict, exchanges: dict[str, dict]) -> dict:
    query_id = ground.get("query_id")
    source_ref = ground.get("source_ref")
    _require(isinstance(query_id, str) and query_id, "horus ground query_id is required")
    _require(isinstance(source_ref, str) and source_ref, "horus ground source_ref is required")
    _require(query_id in exchanges, f"horus ground references unknown exchange {query_id}")
    exchange = exchanges[query_id]
    response = exchange["response"]

    used = {
        source.get("source_ref"): source
        for source in response.get("sources_used", [])
        if isinstance(source, dict) and source.get("source_ref")
    }
    _require(source_ref in used,
             f"{query_id}/{source_ref} was not disclosed among Horus sources_used")

    returned_records = response.get("records_returned", [])
    matching_records = [
        record for record in returned_records
        if isinstance(record, dict) and source_ref in (record.get("source_refs") or [])
    ]
    _require(matching_records,
             f"{query_id}/{source_ref} was used but supports no returned Horus record")

    source = used[source_ref]
    locator = source.get("relevant_locator")
    repository_path = source.get("repository_path")
    url = source.get("url")
    _require(bool(locator), f"{query_id}/{source_ref} lacks relevant_locator")
    _require(bool(repository_path) or bool(url),
             f"{query_id}/{source_ref} lacks both repository_path and url")

    expected_exchange_sha = ground.get("exchange_sha256")
    actual_exchange_sha = exchange.get("exchange_sha256")
    _require(isinstance(expected_exchange_sha, str) and len(expected_exchange_sha) == 64,
             "horus ground exchange_sha256 is required")
    _require(expected_exchange_sha == actual_exchange_sha,
             f"{query_id} exchange sha256 does not match the bound round record")

    expected_source_identity = ground.get("document_identity")
    _require(expected_source_identity == source.get("document_identity"),
             f"{query_id}/{source_ref} document_identity mismatch")
    expected_locator = ground.get("locator")
    _require(expected_locator == locator,
             f"{query_id}/{source_ref} locator mismatch")

    source_sha = ground.get("source_sha256")
    recorded_sha = source.get("sha256")
    if recorded_sha:
        _require(source_sha == recorded_sha,
                 f"{query_id}/{source_ref} source_sha256 mismatch")
    else:
        _require(source_sha in (None, ""),
                 f"{query_id}/{source_ref} claims a source hash Horus did not record")

    return {
        "origin": "horus_exchange",
        "query_id": query_id,
        "source_ref": source_ref,
        "document_identity": source.get("document_identity"),
        "locator": locator,
        "source_record_sha256": _sha256_object(source),
    }


def _validate_minister_ground(ground: dict, minister_repository: dict) -> dict:
    for field in ("witness_id", "source_id", "repository_commit", "path", "locator"):
        _require(isinstance(ground.get(field), str) and ground[field].strip(),
                 f"minister_repository ground {field} is required")
    commit = ground["repository_commit"]
    _require(len(commit) == 40 and all(ch in "0123456789abcdef" for ch in commit),
             "minister_repository ground repository_commit must be a lowercase 40-char git SHA")
    expected_commit = minister_repository.get("git_commit")
    _require(commit == expected_commit,
             "minister_repository ground commit does not match report repository.git_commit")
    return {
        "origin": "minister_repository",
        "witness_id": ground["witness_id"],
        "source_id": ground["source_id"],
        "repository_commit": commit,
        "path": ground["path"],
        "locator": ground["locator"],
    }


def validate_genealogy_package(package: dict, exchanges: list[dict]) -> dict:
    """Validate all proposition-to-source paths in a final judgment package."""
    _require(isinstance(package, dict), "final judgment package must be an object")
    _require(package.get("record_type") == "final_judgment_package",
             "record_type must be final_judgment_package")
    for field in ("inquiry_id", "minister_id"):
        _require(isinstance(package.get(field), str) and package[field].strip(),
                 f"{field} is required")
    repo = package.get("repository")
    _require(isinstance(repo, dict), "repository is required")
    _require(isinstance(repo.get("full_name"), str) and repo["full_name"],
             "repository.full_name is required")
    commit = repo.get("git_commit", "")
    _require(isinstance(commit, str) and len(commit) == 40 and all(c in "0123456789abcdef" for c in commit),
             "repository.git_commit must be a lowercase 40-char git SHA")

    propositions = package.get("propositions")
    _require(isinstance(propositions, list) and propositions,
             "propositions must be a non-empty list")
    exchange_map = _exchange_index(exchanges)
    seen_ids: set[str] = set()
    resolved: list[dict] = []

    for index, proposition in enumerate(propositions):
        _require(isinstance(proposition, dict), f"propositions[{index}] must be an object")
        proposition_id = proposition.get("proposition_id")
        _require(isinstance(proposition_id, str) and proposition_id.startswith("PROP-"),
                 f"propositions[{index}].proposition_id must begin PROP-")
        _require(proposition_id not in seen_ids, f"duplicate proposition_id {proposition_id}")
        seen_ids.add(proposition_id)
        kind = proposition.get("kind")
        _require(kind in PROP_KINDS, f"{proposition_id} has invalid kind {kind!r}")
        _require(isinstance(proposition.get("claim"), str) and proposition["claim"].strip(),
                 f"{proposition_id}.claim is required")

        grounds = proposition.get("genealogy")
        if kind in SUBSTANTIVE_KINDS:
            _require(isinstance(grounds, list) and grounds,
                     f"{proposition_id} substantive proposition has no genealogy")
        else:
            _require(isinstance(grounds, list), f"{proposition_id}.genealogy must be a list")

        resolved_grounds = []
        for gindex, ground in enumerate(grounds):
            _require(isinstance(ground, dict),
                     f"{proposition_id}.genealogy[{gindex}] must be an object")
            origin = ground.get("origin")
            _require(origin in GROUND_ORIGINS,
                     f"{proposition_id}.genealogy[{gindex}] has invalid origin {origin!r}")
            if origin == "horus_exchange":
                resolved_grounds.append(_validate_horus_ground(ground, exchange_map))
            else:
                resolved_grounds.append(_validate_minister_ground(ground, repo))
        resolved.append({"proposition_id": proposition_id, "grounds": resolved_grounds})

    return {
        "status": "GENEALOGY_STRUCTURALLY_VALIDATED_NOT_TRUTH_CERTIFIED",
        "proposition_count": len(propositions),
        "resolved": resolved,
        "package_sha256": _sha256_object(package),
    }


def render_report(package: dict) -> str:
    """Render readable output only after the structured package has been validated."""
    lines = [f"# Ministerial Report — {package['minister_id']}", ""]
    summary = package.get("summary")
    if isinstance(summary, str) and summary.strip():
        lines += [summary.strip(), ""]
    lines += ["## Propositions", ""]
    for proposition in package["propositions"]:
        lines.append(f"### {proposition['proposition_id']} — {proposition['kind']}")
        lines.append(proposition["claim"].strip())
        disposition = proposition.get("provisional_disposition")
        if disposition:
            lines.append(f"\nProvisional disposition: `{disposition}`")
        lines.append("")
    uncertainties = package.get("uncertainties") or []
    if uncertainties:
        lines += ["## Uncertainties", ""]
        lines += [f"- {item}" for item in uncertainties]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_genealogy_record(path: Path, package: dict, validation: dict) -> None:
    record = {
        "record_type": "proposition_evidence_genealogy",
        "final_judgment_package_sha256": validation["package_sha256"],
        "proposition_count": validation["proposition_count"],
        "resolved": validation["resolved"],
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }
    Path(path).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
