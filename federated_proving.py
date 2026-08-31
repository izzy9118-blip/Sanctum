#!/usr/bin/env python3
"""Canonical end-to-end proving transaction for the federated Sanctum harness.

The transaction is intentionally narrow. It proves that one immutable inquiry can be
materialized against the exact constitutional environment, fanned out to every
established sovereign minister through the same universal adapter protocol, passed
through investigative and adversarial Horus calls, finalized into proposition-level
genealogy, validated by the minister adapter, and independently audited by the
Secretary. It performs no presidential synthesis and no owner certification.

`--fixture` is a deterministic CI-only model substitute. It never claims substantive
judgment; it deliberately ends in explicit unresolved uncertainty after canonical Horus
returns NOT_GATHERED. Production execution uses the configured model provider.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

import harness
import secretary_gate
import universal_dispatch
from adversarial_horus import required_adversarial_horus_call, validate_provisional_judgment
from constitutional_environment import write_manifest
from evidence_genealogy import render_report, validate_genealogy_package, write_genealogy_record
from minister_ground_files import validate_minister_ground_files
from minister_horus import required_horus_call, validate_query
from secretary_audit import audit_run, write_audit

BASE = Path(__file__).resolve().parent
ASSEMBLY_SPEC = "standards/assembly-spec.yaml"
FINAL_CONTRACT = "contracts/final-judgment-package.schema.v1.1.0.json"
HORUS_RUNTIME = "runtime/gather.py"
CERTIFICATION = "NONE_SELF_CERTIFICATION_PROHIBITED"


class FederatedProvingError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FederatedProvingError(message)


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _json_object(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FederatedProvingError(f"{label} returned invalid JSON: {exc}") from exc
    _require(isinstance(value, dict), f"{label} must return one JSON object")
    return value


def _git_head(repo: Path) -> str:
    proc = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    value = proc.stdout.strip()
    _require(proc.returncode == 0 and len(value) == 40, f"cannot resolve exact commit for {repo}")
    return value


def _briefing(inquiry: dict[str, Any]) -> dict[str, Any]:
    briefing = inquiry.get("common_briefing")
    _require(isinstance(briefing, dict), "common_briefing is required")
    content = briefing.get("content")
    _require(isinstance(content, str), "common_briefing.content must be a string")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    recorded = briefing.get("sha256")
    if recorded is None:
        briefing = dict(briefing)
        briefing["sha256"] = digest
    else:
        _require(recorded == digest, "common_briefing.sha256 does not match immutable briefing content")
    return briefing


def _call_model(config: dict[str, Any], prompt: str, *, fixture: bool, stage: str,
                minister: dict[str, Any], inquiry: dict[str, Any],
                prepared: dict[str, Any], exchanges: list[dict[str, Any]],
                pass_token: dict[str, Any], stage_receipt: dict[str, Any]) -> dict[str, Any]:
    # The deterministic fixture exercises the same constitutional boundary as a
    # live provider. A fixture may replace a model; it may not replace procedure.
    secretary_gate.verify_stage_receipt(pass_token, stage_receipt)
    if fixture:
        return {
            "text": json.dumps(_fixture_output(stage, minister, inquiry, prepared, exchanges), sort_keys=True),
            "model": "sanctum-deterministic-proving-fixture",
            "usage": {},
        }
    return harness.call(config, prompt, pass_token=pass_token, stage_receipt=stage_receipt)


def _fixture_output(stage: str, minister: dict[str, Any], inquiry: dict[str, Any],
                    prepared: dict[str, Any], exchanges: list[dict[str, Any]]) -> dict[str, Any]:
    minister_id = minister["minister_id"]
    commit = prepared["repository_commit"]
    inquiry_id = inquiry["inquiry_id"]
    suffix = minister_id.upper().replace("-", "_")
    if stage == "investigative_query":
        principal_scope = [
            item["principal_id"] for item in inquiry["board"]["roster"]
            if item.get("roster_state", "ENUMERATED") == "ENUMERATED"
        ]
        return {
            "record_type": "minister_horus_query",
            "query_id": f"MHQ-PROOF-{suffix}",
            "inquiry_id": inquiry_id,
            "minister_id": minister_id,
            "information_needed": ["Documentary ground sufficient to test whether this bounded proving inquiry warrants any substantive conclusion."],
            "source_requirements": [{
                "requirement": "Return qualifying documentary ground if available; otherwise preserve the exact source-state failure.",
                "rationale": "The proving inquiry must demonstrate that missing acquisition remains explicit rather than being reasoned across.",
                "acceptable_tiers": ["T1", "T2", "T3", "T4", "T5"],
                "original_language_required": False,
            }],
            "specific_document_requests": [],
            "principal_scope": principal_scope,
            "disallowed_substitutions": ["Do not convert NOT_SEARCHED or NOT_GATHERED into evidence of absence."],
            "reason_for_request": "Exercise the mandatory investigative Horus boundary before provisional judgment.",
            "source_selection_rule": "HORUS_RETAINS_SOURCE_SELECTION_INDEPENDENCE_EXCEPT_EXPLICIT_DOCUMENT_REQUESTS",
            "source_absence_taxonomy": "HORUS-SOURCE-STATE-1.0",
            "provenance": {"produced_by": minister_id, "repository_commit": commit},
        }
    if stage == "provisional":
        return {
            "record_type": "minister_provisional_judgment",
            "inquiry_id": inquiry_id,
            "minister_id": minister_id,
            "propositions": [{
                "proposition_id": f"P-PROOF-{suffix}",
                "claim": "A substantive conclusion should remain provisional until the requested documentary ground is actually acquired.",
                "kind": "working_hypothesis",
                "disconfirmation_need": "Documentary ground showing that a substantive conclusion is warranted despite the present acquisition state.",
                "why_it_matters": "Such ground could overturn the provisional decision to withhold substantive judgment.",
                "acceptable_tiers": ["T1", "T2", "T3", "T4", "T5"],
                "original_language_required": False,
            }],
            "provenance": {"produced_by": minister_id, "repository_commit": commit},
        }
    if stage == "final_package":
        return {
            "record_type": "final_judgment_package",
            "inquiry_id": inquiry_id,
            "minister_id": minister_id,
            "repository": {"full_name": minister["repository"], "git_commit": commit},
            "summary": "Harness proving fixture only: no substantive ministerial conclusion is asserted because the canonical acquisition stages returned no gathered documentary ground.",
            "propositions": [{
                "proposition_id": f"PROP-PROOF-{suffix}",
                "kind": "unresolved_uncertainty",
                "claim": "The bounded proving inquiry remains unresolved; the harness preserves the unfilled investigative and adversarial evidence requests rather than reasoning across them.",
                "provisional_disposition": "left_unresolved",
                "genealogy": [],
            }],
            "uncertainties": ["The fixture intentionally supplies no external documentary acquisition and therefore cannot support a substantive historical or political judgment."],
            "silence_semantics_standard": "MINISTERIAL-SILENCE-001",
            "issue_register": [{"issue_id": f"ISSUE-PROOF-{suffix}", "issue": "Whether the bounded proving inquiry warrants a substantive conclusion."}],
            "issue_states": [{
                "issue_id": f"ISSUE-PROOF-{suffix}",
                "state": "UNCERTAIN",
                "proposition_refs": [f"PROP-PROOF-{suffix}"],
                "uncertainty_ref": 0,
                "basis": "Both mandatory Horus acquisition stages returned explicit unfilled requests in the proving fixture.",
            }],
        }
    if stage == "native_report":
        evidence = _fixture_evidence(minister_id, prepared)
        return {
            "record_type": "ministerial_report",
            "id": f"REPORT-PROOF-{suffix}",
            "report_id": f"REPORT-PROOF-{suffix}",
            "report_status": "DRAFT_PENDING_MINISTER_REPOSITORY_VALIDATION",
            "inquiry_ref": {"id": inquiry_id},
            "minister": {"actor": minister_id, "manifest_commit": commit},
            "mode": "reasoned",
            "repository": {"full_name": minister["repository"], "git_commit": commit},
            "governing_manifest": {"path": "manifest.yaml", "version": str(prepared.get("manifest_version", "UNRECORDED"))},
            "evidence": evidence,
            "propositions": [{
                "kind": "unresolved_uncertainty",
                "claim": "No substantive judgment is asserted by the deterministic proving fixture.",
                "grounds": [],
            }],
            "uncertainties": ["This report is a transport/validation fixture, not a substantive ministerial judgment."],
            "termination": {"status": "PROVING_FIXTURE_COMPLETE_WITHOUT_SUBSTANTIVE_JUDGMENT"},
            "provenance": {"runtime": "federated_proving.py", "fixture": True},
            "certification_status": "PENDING_OWNER_CERTIFICATION",
        }
    raise FederatedProvingError(f"unknown fixture stage {stage}")


def _fixture_evidence(minister_id: str, prepared: dict[str, Any]) -> list[dict[str, Any]]:
    commit = prepared["repository_commit"]
    if minister_id == "xenophon":
        sources = prepared.get("context", {}).get("corpus_index", {}).get("sources", [])
        if sources:
            source = sources[0]
            witness_ids = source.get("witness_ids") or []
            if witness_ids:
                return [{
                    "witness_id": witness_ids[0],
                    "source_id": source["id"],
                    "repository_commit": commit,
                    "path": source.get("record", "corpus/index.yaml"),
                }]
    return [{
        "witness_id": "STRAUSS-WIT-PROOF",
        "source_id": "STRAUSS-SRC-PROOF",
        "repository_commit": commit,
        "path": "manifest.yaml",
    }]


def _prompt(stage: str, prepared: dict[str, Any], inquiry: dict[str, Any], exchanges: list[dict[str, Any]]) -> str:
    rules = {
        "investigative_query": "Return one minister_horus_query JSON object only. Do not give final judgment.",
        "provisional": "Return one minister_provisional_judgment JSON object only. State what could weaken each provisional proposition.",
        "final_package": "Return one final_judgment_package JSON object only. Preserve all unfilled Horus requests as limitations and use proposition-level genealogy for every substantive proposition.",
        "native_report": "Return one sovereign ministerial_report JSON object only for adapter validation. Do not claim owner certification.",
    }
    return (
        rules[stage] + "\n\n"
        + "=== IMMUTABLE INQUIRY ===\n" + json.dumps(inquiry, indent=2, sort_keys=True) + "\n\n"
        + "=== SOVEREIGN PREPARED CONTEXT ===\n" + json.dumps(prepared, indent=2, sort_keys=True, default=str) + "\n\n"
        + "=== VALIDATED PRIOR EXCHANGES ===\n" + json.dumps(exchanges, indent=2, sort_keys=True, default=str)
    )


def _run_horus(horus: Path, query: dict[str, Any], *, fixture: bool,
               pass_token: dict[str, Any], stage_receipt: dict[str, Any]) -> dict[str, Any]:
    secretary_gate.verify_stage_receipt(pass_token, stage_receipt)
    runtime = horus / HORUS_RUNTIME
    _require(runtime.is_file(), f"canonical Horus runtime missing: {runtime}")
    env = os.environ.copy()
    if fixture:
        env["PYTEST_CURRENT_TEST"] = "federated_proving_fixture"
    proc = subprocess.run([sys.executable, str(runtime)], cwd=horus, input=json.dumps(query), text=True,
                          capture_output=True, check=False, shell=False, timeout=120, env=env)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "no detail"
        raise FederatedProvingError(f"canonical Horus call failed: {detail[:500]}")
    return _json_object(proc.stdout, "Horus")


def _write_exchange(hub: Path, inquiry_id: str, minister_id: str, kind: str,
                    query: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    directory = hub / "exchanges" / inquiry_id / minister_id
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / f"{query['query_id']}.request.json"
    response_path = directory / f"{query['query_id']}.response.json"
    request_path.write_text(json.dumps(query, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    response_path.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = _canonical_sha({"request": query, "response": response})
    return {
        "exchange_kind": kind,
        "query_id": query["query_id"],
        "exchange_sha256": digest,
        "request_path": str(request_path.relative_to(hub)),
        "response_path": str(response_path.relative_to(hub)),
        "request": query,
        "response": response,
    }


def _validate_final_package(package: dict[str, Any]) -> None:
    schema = json.loads((BASE / FINAL_CONTRACT).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(package), key=lambda e: list(e.path))
    if errors:
        raise FederatedProvingError("final package contract violation: " + "; ".join(e.message for e in errors))


def _adapter_validate(repo: Path, entrypoint: str, report: dict[str, Any]) -> dict[str, Any]:
    return universal_dispatch._invoke(repo, entrypoint, "validate-report", report)


def _secretary_gate_for_minister(*, hub: Path, inquiry: dict[str, Any], inquiry_path: Path,
                                 minister_id: str) -> tuple[dict[str, Any], dict[str, Any], secretary_gate.StageLedger, Path, Path]:
    """Materialize the minister-specific pre-run gate from the immutable inquiry.

    The inquiry owns the roster and language/provenance declarations. The runner
    merely records them and binds the gate to the exact inquiry bytes; it does not
    add principals or grade their documentary standing.
    """
    board = inquiry.get("board")
    _require(isinstance(board, dict), "inquiry.board is required by the Secretary pre-run gate")
    roster = board.get("roster")
    _require(isinstance(roster, list) and roster, "inquiry.board.roster must enumerate the principals")
    frozen_at = board.get("frozen_at")
    _require(isinstance(frozen_at, str) and frozen_at, "inquiry.board.frozen_at is required")

    gate_roster = []
    query_plan = []
    for item in roster:
        _require(isinstance(item, dict), "every inquiry.board.roster entry must be an object")
        principal_id = item.get("principal_id")
        state = item.get("roster_state", "ENUMERATED")
        entry = {
            "principal_id": principal_id,
            "name": item.get("name"),
            "type": item.get("type"),
            "roster_state": state,
            "language": item.get("language"),
            "language_state": item.get("language_state"),
            "provenance_flag": item.get("provenance_flag"),
        }
        if state == "ABSENT_DECLARED":
            entry["absence_reason"] = item.get("absence_reason")
        else:
            query_plan.append({
                "plan_id": f"QP-{principal_id}",
                "principals": [principal_id],
                "information_sought": "Documentary ground bearing on the immutable inquiry for this principal.",
                "language": item.get("language"),
            })
        gate_roster.append(entry)

    checklist = {
        "record_type": secretary_gate.CHECKLIST_RECORD_TYPE,
        "gate_standard": secretary_gate.GATE_STANDARD,
        "checklist_id": f"SPC-{inquiry['inquiry_id']}-{minister_id}",
        "inquiry_id": inquiry["inquiry_id"],
        "board": board.get("board_id"),
        "board_type": board.get("board_type"),
        "minister_id": minister_id,
        "room": "harness",
        "board_manifest": {
            "path": str(inquiry_path),
            "sha256": hashlib.sha256(inquiry_path.read_bytes()).hexdigest(),
            "frozen": True,
            "frozen_at": frozen_at,
        },
        "roster": gate_roster,
        "query_plan": query_plan,
        "query_plan_rule": secretary_gate.QUERY_PLAN_RULE,
        "sequence": list(secretary_gate.REQUIRED_SEQUENCE + secretary_gate.OPTIONAL_TRAILING_STAGES),
        "one_shot_dispatch": "NON_CONFORMING",
        "enumeration_precedes_gathering": True,
        "timestamps": {
            "enumerated_at": frozen_at,
            "query_plan_recorded_at": frozen_at,
            "board_frozen_at": frozen_at,
            "submitted_at": secretary_gate.utc_now(),
        },
        "certification": secretary_gate.CERTIFICATION,
    }
    token = secretary_gate.open_gate(checklist)
    gate_dir = hub / "inquiries" / inquiry["inquiry_id"] / "secretary-gate" / minister_id
    checklist_path = gate_dir / "checklist.json"
    token_path = gate_dir / "pass-token.json"
    secretary_gate.write_json(checklist_path, checklist)
    secretary_gate.write_json(token_path, token)
    return checklist, token, secretary_gate.StageLedger(token), checklist_path, token_path


def _render_auditable_dispatch(checklist: dict[str, Any], package: dict[str, Any], minister_id: str) -> str:
    """Render structural seams the Secretary can audit without reading substance."""
    lines = ["# Documentary positions", ""]
    for principal in checklist["roster"]:
        if principal["roster_state"] != "ENUMERATED":
            continue
        lines.extend([
            f"## POSITION — {principal['name']} [{principal['principal_id']}]",
            f"PROVENANCE: {principal['provenance_flag']} — {principal['language']}",
        ])
        if principal["provenance_flag"] == "NOT_GATHERED":
            lines.append("SILENCE: UNCERTAIN")
        lines.extend(["", "The documentary position is preserved at the frozen board's recorded provenance state.", ""])
    lines.extend([f"# MINISTERIAL JUDGMENT — {minister_id}", "", render_report(package)])
    return "\n".join(lines)


def _run_minister(*, estate: Path, hub: Path, horus: Path, inquiry: dict[str, Any],
                  prepared: dict[str, Any], minister: dict[str, Any], binding: dict[str, Any],
                  repo: Path, model_config: dict[str, Any], fixture: bool, date: str,
                  inquiry_path: Path) -> dict[str, Any]:
    minister_id = minister["minister_id"]
    runtime_commit = binding["runtime_overlay_commit"]
    _require(prepared["repository_commit"] == runtime_commit, f"{minister_id} prepared runtime commit mismatch")
    exchanges: list[dict[str, Any]] = []
    checklist, pass_token, ledger, checklist_path, token_path = _secretary_gate_for_minister(
        hub=hub, inquiry=inquiry, inquiry_path=inquiry_path, minister_id=minister_id
    )

    investigative_receipt = ledger.enter("investigative_query")
    first = _call_model(model_config, _prompt("investigative_query", prepared, inquiry, exchanges), fixture=fixture,
                        stage="investigative_query", minister=minister, inquiry=inquiry, prepared=prepared, exchanges=exchanges,
                        pass_token=pass_token, stage_receipt=investigative_receipt)
    query = _json_object(first["text"], f"{minister_id} investigative query")
    validate_query(query)
    secretary_gate.require_roster_coverage(checklist, query.get("principal_scope"))
    _require(query["inquiry_id"] == inquiry["inquiry_id"] and query["minister_id"] == minister_id, "investigative query identity mismatch")
    _require(query["provenance"]["repository_commit"] == runtime_commit, "investigative query runtime commit mismatch")
    response = required_horus_call(query, lambda q: _run_horus(
        horus, q, fixture=fixture, pass_token=pass_token, stage_receipt=investigative_receipt))
    _require(response.get("provenance", {}).get("horus_repository_commit") == _git_head(horus), "investigative Horus provenance mismatch")
    exchanges.append(_write_exchange(hub, inquiry["inquiry_id"], minister_id, "investigative", query, response))

    provisional_receipt = ledger.enter("provisional_judgment")
    provisional_call = _call_model(model_config, _prompt("provisional", prepared, inquiry, exchanges), fixture=fixture,
                                   stage="provisional", minister=minister, inquiry=inquiry, prepared=prepared, exchanges=exchanges,
                                   pass_token=pass_token, stage_receipt=provisional_receipt)
    provisional = _json_object(provisional_call["text"], f"{minister_id} provisional judgment")
    validate_provisional_judgment(provisional)
    _require(provisional["inquiry_id"] == inquiry["inquiry_id"] and provisional["minister_id"] == minister_id, "provisional identity mismatch")
    _require(provisional["provenance"]["repository_commit"] == runtime_commit, "provisional runtime commit mismatch")

    adversarial_receipt = ledger.enter("adversarial_pass")
    adversarial_query, adversarial_response = required_adversarial_horus_call(
        provisional, lambda q: _run_horus(
            horus, q, fixture=fixture, pass_token=pass_token, stage_receipt=adversarial_receipt),
        investigative_query=query
    )
    _require(adversarial_response.get("provenance", {}).get("horus_repository_commit") == _git_head(horus), "adversarial Horus provenance mismatch")
    exchanges.append(_write_exchange(hub, inquiry["inquiry_id"], minister_id, "adversarial", adversarial_query, adversarial_response))

    final_receipt = ledger.enter("final_judgment")
    final_call = _call_model(model_config, _prompt("final_package", prepared, inquiry, exchanges), fixture=fixture,
                             stage="final_package", minister=minister, inquiry=inquiry, prepared=prepared, exchanges=exchanges,
                             pass_token=pass_token, stage_receipt=final_receipt)
    package = _json_object(final_call["text"], f"{minister_id} final package")
    _validate_final_package(package)
    _require(package["inquiry_id"] == inquiry["inquiry_id"] and package["minister_id"] == minister_id, "final package identity mismatch")
    _require(package["repository"]["git_commit"] == runtime_commit, "final package runtime commit mismatch")

    genealogy_exchanges = [{
        "exchange_kind": item["exchange_kind"],
        "query_id": item["query_id"],
        "exchange_sha256": item["exchange_sha256"],
        "request": item["request"],
        "response": item["response"],
    } for item in exchanges]
    validation = validate_genealogy_package(package, genealogy_exchanges)
    validate_minister_ground_files(package, estate)

    genealogy_receipt = ledger.enter("genealogy_finalization")
    native_call = _call_model(model_config, _prompt("native_report", prepared, inquiry, exchanges), fixture=fixture,
                              stage="native_report", minister=minister, inquiry=inquiry, prepared=prepared, exchanges=exchanges,
                              pass_token=pass_token, stage_receipt=genealogy_receipt)
    native_report = _json_object(native_call["text"], f"{minister_id} native report")
    adapter_validation = _adapter_validate(repo, binding["entrypoint"], native_report)
    universal_dispatch._validate_contract(adapter_validation)
    _require(adapter_validation.get("repository_commit") == runtime_commit, "adapter report validation runtime commit mismatch")

    report_dir = hub / "reports" / "harness-proof"
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{minister_id}-{date}"
    package_path = report_dir / f"{stem}.final.json"
    genealogy_path = report_dir / f"{stem}.genealogy.json"
    report_path = report_dir / f"{stem}.md"
    native_path = report_dir / f"{stem}.native-report.json"
    round_path = report_dir / f"{stem}.round.json"
    provisional_path = report_dir / f"{stem}.provisional.json"

    package_path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_genealogy_record(genealogy_path, package, validation)
    report_path.write_text(_render_auditable_dispatch(checklist, package, minister_id), encoding="utf-8")
    native_path.write_text(json.dumps(native_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    provisional_path.write_text(json.dumps(provisional, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    round_record = {
        "record_type": "sovereign_genealogical_round",
        "governing_assembly_spec": {"path": ASSEMBLY_SPEC, "version": "1.5.0"},
        "assembly_spec": {"path": "standards/assembly-spec.v1.4.0.yaml", "version": "1.4.0"},
        "inquiry_id": inquiry["inquiry_id"],
        "board": "harness-proof",
        "minister": minister_id,
        "minister_id": minister_id,
        "minister_repository_commit": runtime_commit,
        "certified_minister_base_commit": minister["pinned_commit"],
        "runtime_adapter_overlay_commit": runtime_commit,
        "horus_repository_commit": _git_head(horus),
        "common_briefing_sha256": inquiry["common_briefing"]["sha256"],
        "horus_exchanges": [{k: v for k, v in item.items() if k not in {"request", "response"}} for item in exchanges],
        "final_judgment_package": {
            "path": str(package_path.relative_to(hub)),
            "sha256": _canonical_sha(package),
            "proposition_count": len(package["propositions"]),
            "contract": FINAL_CONTRACT,
        },
        "proposition_evidence_genealogy": {
            "path": str(genealogy_path.relative_to(hub)),
            "status": validation["status"],
            "proposition_count": validation["proposition_count"],
            "minister_repository_files_resolved": True,
        },
        "adapter_validation": adapter_validation,
        "model": {
            "fixture": fixture,
            "investigative_model_returned": first.get("model"),
            "provisional_model_returned": provisional_call.get("model"),
            "final_model_returned": final_call.get("model"),
            "native_report_model_returned": native_call.get("model"),
        },
        "secretary_gate": {
            "checklist_path": str(checklist_path.relative_to(hub)),
            "checklist_sha256": secretary_gate.checklist_digest(checklist),
            "token_path": str(token_path.relative_to(hub)),
            "token_sha256": pass_token["token_sha256"],
            "stages_completed": ledger.stages_completed(),
            "dispatch_path": str(report_path.relative_to(hub)),
            "dispatch_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        },
        "outputs": {
            "final_judgment_package": str(package_path.relative_to(hub)),
            "proposition_evidence_genealogy": str(genealogy_path.relative_to(hub)),
            "rendered_report": str(report_path.relative_to(hub)),
            "native_report": str(native_path.relative_to(hub)),
            "provisional_judgment": str(provisional_path.relative_to(hub)),
        },
        "certification": CERTIFICATION,
    }
    round_path.write_text(json.dumps(round_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    audit = audit_run(estate=estate, board="harness-proof", minister=minister_id, date=date)
    audit_path = report_dir / f"{stem}.secretary-audit.json"
    write_audit(audit_path, audit)
    return {
        "minister_id": minister_id,
        "certified_base_commit": minister["pinned_commit"],
        "runtime_overlay_commit": runtime_commit,
        "investigative_query_id": query["query_id"],
        "investigative_horus_status": response["status"],
        "adversarial_query_id": adversarial_query["query_id"],
        "adversarial_horus_status": adversarial_response["status"],
        "final_package": str(package_path.relative_to(hub)),
        "adapter_validation_status": adapter_validation["status"],
        "secretary_audit_status": audit["status"],
        "certification": CERTIFICATION,
    }


def run(args) -> int:
    config = harness.load_config(Path(args.config).expanduser())
    estate = Path(config["estate"]).expanduser().resolve()
    hub, horus = estate / "Sanctum", estate / "Horus"
    inquiry_path = Path(args.inquiry).expanduser().resolve()
    inquiry = json.loads(inquiry_path.read_text(encoding="utf-8"))
    _require(isinstance(inquiry, dict), "inquiry must be one JSON object")
    _require(isinstance(inquiry.get("inquiry_id"), str) and inquiry["inquiry_id"], "inquiry_id is required")
    _require(isinstance(inquiry.get("question"), str) and inquiry["question"].strip(), "question is required")
    inquiry["common_briefing"] = _briefing(inquiry)

    spec = harness.yaml_load((hub / ASSEMBLY_SPEC).read_text(encoding="utf-8"))
    _require(str(spec.get("version")) == "1.5.0", "federated proving transaction requires governing ASSEMBLY-SPEC-001 v1.5.0")

    environment_path = write_manifest(estate=estate, inquiry_id=inquiry["inquiry_id"])
    prepared_doc = universal_dispatch.prepare(estate, inquiry)
    prepared_by_id = {item["minister_id"]: item for item in prepared_doc["prepared"]}
    plan = universal_dispatch.binding_plan(estate)
    _require(len(plan) == prepared_doc["prepared_count"], "prepared minister count differs from universal dispatch plan")

    model_config = dict(config.get("model") or {})
    if args.provider:
        model_config["provider"] = args.provider
    date = args.date or dt.date.today().isoformat()
    results = []
    for minister, binding, repo in plan:
        _require(minister["minister_id"] in prepared_by_id, f"missing prepared context for {minister['minister_id']}")
        results.append(_run_minister(
            estate=estate, hub=hub, horus=horus, inquiry=inquiry,
            prepared=prepared_by_id[minister["minister_id"]], minister=minister,
            binding=binding, repo=repo, model_config=model_config,
            fixture=args.fixture, date=date, inquiry_path=inquiry_path,
        ))

    expected = {minister["minister_id"] for minister, _, _ in plan}
    _require({item["minister_id"] for item in results} == expected, "fan-in does not account for every established minister")
    fanin = {
        "record_type": "sanctum_federated_proving_inquiry",
        "inquiry_id": inquiry["inquiry_id"],
        "question": inquiry["question"],
        "common_briefing_sha256": inquiry["common_briefing"]["sha256"],
        "constitutional_environment": str(environment_path.relative_to(hub)),
        "governing_assembly_spec": {"path": ASSEMBLY_SPEC, "version": "1.5.0"},
        "mode": "DETERMINISTIC_FIXTURE_NO_SUBSTANTIVE_JUDGMENT" if args.fixture else "LIVE_MODEL_PROVING_INQUIRY",
        "expected_ministers": sorted(expected),
        "completed_ministers": sorted(item["minister_id"] for item in results),
        "results": results,
        "presidential_synthesis": "NOT_RUN_PROVING_UNIT_BOUNDARY",
        "owner_certification": "NOT_REQUESTED",
        "status": "END_TO_END_PROVING_TRANSACTION_COMPLETE_NOT_TRUTH_CERTIFICATION",
        "certification": CERTIFICATION,
    }
    target = hub / "inquiries" / inquiry["inquiry_id"] / "federated-proving-result.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(fanin, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(fanin, indent=2, sort_keys=True))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--inquiry", required=True)
    parser.add_argument("--date")
    parser.add_argument("--provider")
    parser.add_argument("--fixture", action="store_true", help="CI-only deterministic model substitute; never a substantive judgment")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as exc:  # fail closed at the top-level transaction boundary
        print(f"FEDERATED PROVING ABORTED: {exc}", file=sys.stderr)
        return 7


if __name__ == "__main__":
    raise SystemExit(main())
