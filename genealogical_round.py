#!/usr/bin/env python3
"""Forward reasoned round with mandatory proposition-level evidence genealogy.

This wrapper preserves sovereign_round.py as the v1.3 predecessor runtime. It may
execute that runtime only as an internal stage against the preserved v1.3 spec.
The resulting free-form final draft is not authoritative. A final structured
minister call must convert the judgment into a typed package whose substantive
propositions resolve to exact documentary ground. Only after genealogy validation
does Sanctum render the readable report that remains on disk.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import harness
import secretary_gate
import sovereign_round
from evidence_genealogy import GenealogyError, render_report, validate_genealogy_package, write_genealogy_record
from minister_ground_files import validate_minister_ground_files

SPEC_PATH = "standards/assembly-spec.yaml"
PREDECESSOR_SPEC_PATH = "standards/assembly-spec.v1.3.0.yaml"
FINAL_PACKAGE_CONTRACT = "contracts/final-judgment-package.schema.json"


class GenealogicalRoundError(RuntimeError):
    pass


def _json_object(text: str, label: str) -> dict:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GenealogicalRoundError(f"{label} did not return valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise GenealogicalRoundError(f"{label} must return one JSON object")
    return value


def _load_json(path: str | Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GenealogicalRoundError(f"expected object at {path}")
    return value


def _exchange_records(round_record: dict) -> list[dict]:
    output = []
    for binding in round_record.get("horus_exchanges", []):
        request = _load_json(binding["request_path"])
        response = _load_json(binding["response_path"])
        output.append({
            "exchange_kind": binding["exchange_kind"],
            "query_id": binding["query_id"],
            "exchange_sha256": binding["exchange_sha256"],
            "request": request,
            "response": response,
        })
    if len(output) != 2:
        raise GenealogicalRoundError("genealogical round requires exactly two prior Horus exchanges")
    return output


def _genealogy_prompt(draft: str, round_record: dict, exchanges: list[dict],
                      inquiry_id: str, minister_id: str, repository_name: str,
                      repository_commit: str) -> str:
    disclosed_sources = []
    for exchange in exchanges:
        response = exchange["response"]
        disclosed_sources.append({
            "exchange_kind": exchange["exchange_kind"],
            "query_id": exchange["query_id"],
            "exchange_sha256": exchange["exchange_sha256"],
            "sources_used": response.get("sources_used", []),
            "records_returned": response.get("records_returned", []),
            "unfilled_requests": response.get("unfilled_requests", []),
        })
    return (
        "You are at the FINAL GENEALOGY GATE. The draft judgment below is not yet an "
        "authoritative Ministerial Report. Return ONE JSON object only conforming to "
        f"{FINAL_PACKAGE_CONTRACT}.\n\n"
        f"Set inquiry_id={inquiry_id!r}, minister_id={minister_id!r}, "
        f"repository.full_name={repository_name!r}, and "
        f"repository.git_commit={repository_commit!r}.\n\n"
        "Convert the judgment into explicit propositions. Every substantive proposition "
        "(documented_finding, supported_inference, working_hypothesis) MUST carry one or "
        "more genealogy entries. Do not use a generic bibliography.\n\n"
        "For Horus-derived ground, cite only a source in sources_used below and copy its "
        "query_id, exchange_sha256, source_ref, document_identity, relevant_locator as "
        "locator, and sha256 if Horus recorded one. A source that was only searched or "
        "rejected is not ground.\n\n"
        "For ground from your own sovereign repository, use origin=minister_repository "
        "and give the exact witness_id, source_id, pinned repository_commit, repository "
        "path, and a precise locator. Do not invent a witness or source identity. The "
        "runtime will verify that the cited witness_id and source_id occur in the file.\n\n"
        "Preserve the effect of the adversarial round with provisional_disposition: "
        "retained, qualified, withdrawn, left_unresolved, or new_after_adversarial_ground. "
        "Withdrawn propositions may be recorded as unresolved_uncertainty rather than "
        "asserted as substantive findings.\n\n"
        "If adequate ground cannot be identified, downgrade the proposition to an "
        "unresolved_uncertainty or omit it. Do not fabricate genealogy merely to pass.\n\n"
        "=== NON-AUTHORITATIVE FINAL DRAFT ===\n"
        + draft
        + "\n\n=== DISCLOSED HORUS GROUND ===\n"
        + json.dumps(disclosed_sources, indent=2, sort_keys=True)
    )


def _run_predecessor(args) -> int:
    """Execute v1.3 only as an internal stage of the governing v1.4 runner.

    The declared sequence is swapped the same way the spec path is: this wrapper
    makes a sixth call, so the Secretary is told about it before the first one.
    """
    previous_spec = sovereign_round.SPEC_PATH
    previous_sequence = sovereign_round.DECLARED_SEQUENCE
    sovereign_round.SPEC_PATH = PREDECESSOR_SPEC_PATH
    sovereign_round.DECLARED_SEQUENCE = list(secretary_gate.REQUIRED_SEQUENCE) + ["genealogy_finalization"]
    try:
        return sovereign_round.run(args)
    finally:
        sovereign_round.SPEC_PATH = previous_spec
        sovereign_round.DECLARED_SEQUENCE = previous_sequence


def run(args) -> int:
    config = harness.load_config(Path(args.config).expanduser())
    estate = Path(config["estate"]).expanduser()
    hub = estate / "Sanctum"
    governing = harness.yaml_load((hub / SPEC_PATH).read_text(encoding="utf-8"))
    if str(governing.get("version")) != "1.4.0":
        raise GenealogicalRoundError("genealogical finalization requires governing ASSEMBLY-SPEC-001 v1.4.0")

    result = _run_predecessor(args)
    if result != 0:
        return result

    stamp = (dt.date.fromisoformat(args.date) if args.date else dt.date.today()).isoformat()
    report_dir = hub / "reports" / args.board
    report_path = report_dir / f"{args.minister}-{stamp}.md"
    round_path = report_dir / f"{args.minister}-{stamp}.round.json"
    package_path = report_dir / f"{args.minister}-{stamp}.final.json"
    genealogy_path = report_dir / f"{args.minister}-{stamp}.genealogy.json"

    draft = report_path.read_text(encoding="utf-8")
    round_record = _load_json(round_path)
    inquiry_id = round_record["inquiry_id"]
    repository_commit = round_record["minister_repository_commit"]
    house = config["ministers"][args.minister]["house"]
    repository_name = house
    exchanges = _exchange_records(round_record)

    call_config = dict(config["model"])
    if args.provider:
        call_config["provider"] = args.provider

    gate_binding = round_record.get("secretary_gate") or {}
    try:
        pass_token = _load_json(gate_binding["token_path"])
        ledger = secretary_gate.StageLedger.resume(pass_token, gate_binding.get("stages_completed") or [])
        stage_receipt = ledger.enter("genealogy_finalization")
    except (KeyError, OSError, secretary_gate.SecretaryGateError) as exc:
        raise GenealogicalRoundError(
            f"the genealogy call has no Secretary stage receipt to make it under: {exc}") from exc

    print("\nCALL 6 — FINAL PROPOSITION GENEALOGY")
    final_call = harness.call(
        call_config,
        _genealogy_prompt(
            draft,
            round_record,
            exchanges,
            inquiry_id,
            args.minister,
            repository_name,
            repository_commit,
        ),
        pass_token=pass_token,
        stage_receipt=stage_receipt,
    )
    package = _json_object(final_call["text"], "final genealogy call")
    if package.get("inquiry_id") != inquiry_id or package.get("minister_id") != args.minister:
        raise GenealogicalRoundError("final judgment package identity mismatch")
    if package.get("repository", {}).get("git_commit") != repository_commit:
        raise GenealogicalRoundError("final judgment package changed the pinned minister commit")

    try:
        validation = validate_genealogy_package(package, exchanges)
        validate_minister_ground_files(package, estate)
    except GenealogyError as exc:
        raise GenealogicalRoundError(f"genealogy gate rejected final judgment: {exc}") from exc

    package_text = json.dumps(package, indent=2, sort_keys=True) + "\n"
    package_path.write_text(package_text, encoding="utf-8")
    write_genealogy_record(genealogy_path, package, validation)
    report_path.write_text(render_report(package), encoding="utf-8")

    package_sha = hashlib.sha256(
        json.dumps(package, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    round_record["record_type"] = "sovereign_genealogical_round"
    round_record["assembly_spec"] = {"path": SPEC_PATH, "version": "1.4.0"}
    round_record["predecessor_assembly_spec"] = {"path": PREDECESSOR_SPEC_PATH, "version": "1.3.0"}
    round_record["final_judgment_package"] = {
        "path": str(package_path),
        "sha256": package_sha,
        "proposition_count": len(package["propositions"]),
        "contract": FINAL_PACKAGE_CONTRACT,
    }
    round_record["proposition_evidence_genealogy"] = {
        "path": str(genealogy_path),
        "status": validation["status"],
        "proposition_count": validation["proposition_count"],
        "minister_repository_files_resolved": True,
    }
    round_record["model"]["genealogy_model_returned"] = final_call.get("model")
    round_record["secretary_gate"]["stages_completed"] = ledger.stages_completed()
    round_record["outputs"]["final_judgment_package"] = str(package_path)
    round_record["outputs"]["proposition_evidence_genealogy"] = str(genealogy_path)
    round_record["certification"] = "NONE_SELF_CERTIFICATION_PROHIBITED"
    round_path.write_text(json.dumps(round_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"  genealogy validated: {genealogy_path}")
    print(f"  authoritative structured judgment: {package_path}")
    print(f"  rendered report: {report_path}")
    print("  No truth or completeness certification was performed.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run reasoned Assembly round with mandatory proposition genealogy.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--board", required=True)
    parser.add_argument("--minister", required=True)
    parser.add_argument("--horus-command", required=True)
    parser.add_argument("--inquiry-id")
    parser.add_argument("--question-file")
    parser.add_argument("--date")
    parser.add_argument("--provider")
    parser.add_argument("--carry-mark", action="store_true")
    parser.add_argument("--no-pull", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (GenealogicalRoundError, GenealogyError, sovereign_round.RoundError) as exc:
        print(f"GENEALOGICAL ROUND ABORTED: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
