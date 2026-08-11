#!/usr/bin/env python3
"""The mandatory investigative and adversarial round for reasoned Assembly runs.

Sequence:
    1. Build the same common context the Sovereign Harness would give the minister.
    2. CALL the minister for an investigative request only.
    3. CALL the pinned Horus repository through its canonical acquisition runtime.
    4. CALL the minister for a provisional judgment that names what could weaken it.
    5. Deterministically build and CALL the adversarial Horus request.
    6. Inject both complete exchanges and the provisional judgment.
    7. CALL the minister for final judgment.
    8. WRITE both exchanges, report, and round manifest.

A direct one-shot reasoned call, a run that substitutes an arbitrary Horus command,
or a run that forms a provisional judgment but skips its adversarial test is
non-conforming under ASSEMBLY-SPEC-001 v1.3.0. This runner does not gather for
Horus and does not judge for the minister.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

import harness
from adversarial_horus import (
    adversarial_exchange_digest,
    required_adversarial_horus_call,
    validate_provisional_judgment,
    write_adversarial_exchange,
)
from minister_horus import (
    HorusExchangeError,
    exchange_digest,
    required_horus_call,
    validate_query,
    write_exchange,
)

SPEC_PATH = "standards/assembly-spec.yaml"
QUERY_CONTRACT_PATH = "contracts/minister-horus-query.schema.json"
PROVISIONAL_CONTRACT_PATH = "contracts/provisional-judgment.schema.json"
ADVERSARIAL_QUERY_CONTRACT_PATH = "contracts/minister-horus-adversarial-query.schema.json"
CANONICAL_HORUS_RUNTIME = "runtime/gather.py"
ACQUISITION_PROTOCOL = "HORUS-ACQUISITION-1.0"


class RoundError(RuntimeError):
    pass


def _json_object(text: str, label: str) -> dict:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RoundError(f"{label} did not return valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RoundError(f"{label} must return one JSON object")
    return value


def _run_horus_command(command: list[str], query: dict) -> dict:
    """Invoke the canonical Horus gatherer as a hard subprocess boundary."""
    process = subprocess.run(
        command,
        input=json.dumps(query),
        text=True,
        shell=False,
        capture_output=True,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip() or "no detail"
        raise RoundError(f"HORUS CALL failed with exit {process.returncode}: {detail[:500]}")
    return _json_object(process.stdout, "Horus gatherer")


def _resolve_horus_command(horus: Path, args) -> list[str]:
    canonical = (horus / CANONICAL_HORUS_RUNTIME).resolve()
    if args.horus_command:
        if not args.allow_horus_command_override:
            raise RoundError(
                "--horus-command is test-only; production rounds must use the canonical pinned Horus runtime. "
                "Use --allow-horus-command-override only for explicit fixture tests."
            )
        command = shlex.split(args.horus_command)
        if not command:
            raise RoundError("test Horus command override is empty")
        return command
    if not canonical.exists():
        raise RoundError(f"canonical Horus acquisition runtime is missing: {canonical}")
    return [sys.executable, str(canonical)]


def _require_horus_commit(response: dict, expected_commit: str) -> None:
    provenance = response.get("provenance") or {}
    actual = provenance.get("horus_repository_commit")
    if actual != expected_commit:
        raise RoundError(
            "Horus response provenance does not match the exact Horus commit pulled for this round: "
            f"expected {expected_commit}, got {actual}"
        )


def _query_prompt(common_context: str, inquiry_id: str, minister_id: str, commit: str) -> str:
    return (
        common_context
        + "\n\n"
        + "=" * 72
        + "\nMANDATORY INVESTIGATIVE QUERY ROUND\n"
        + "=" * 72
        + "\n\n"
        + "Do not give final judgment yet. Read the common ground through your own "
          "ministerial method and identify what additional information you need before "
          "judgment. Return ONE JSON object only. The request must comply with "
          f"{QUERY_CONTRACT_PATH}.\n\n"
        + f"Set inquiry_id to {inquiry_id!r}, minister_id to {minister_id!r}, and "
          f"provenance.repository_commit to {commit!r}. Create a stable query_id beginning "
          "with MHQ-. State information_needed, source_requirements with rationale, any "
          "specific document requests, relevant scope, disallowed substitutions, and "
          "reason_for_request.\n\n"
        + "If original-language T1 is required, principal_scope must explicitly name every "
          "principal for whom that language requirement applies; Horus resolves language, "
          "timezone, local calendar and first-party channels from its pinned source registry. "
          "You may specify what would count as adequate evidence. Except for an explicit "
          "document request, you may NOT select the sources Horus must use. Set "
          "source_selection_rule exactly to "
          "HORUS_RETAINS_SOURCE_SELECTION_INDEPENDENCE_EXCEPT_EXPLICIT_DOCUMENT_REQUESTS."
    )


def _provisional_prompt(common_context: str, query: dict, response: dict,
                        inquiry_id: str, minister_id: str, commit: str) -> str:
    exchange = json.dumps({"minister_query": query, "horus_response": response},
                          indent=2, sort_keys=True)
    return (
        common_context
        + "\n\n"
        + "=" * 72
        + "\nVALIDATED INVESTIGATIVE EXCHANGE\n"
        + "=" * 72
        + "\n\n"
        + exchange
        + "\n\n"
        + "=" * 72
        + "\nPROVISIONAL JUDGMENT — NOT FINAL\n"
        + "=" * 72
        + "\n\n"
        + "Form your strongest present judgment, but do not finalize it. Return ONE JSON "
          f"object only, conforming to {PROVISIONAL_CONTRACT_PATH}. Set inquiry_id to "
          f"{inquiry_id!r}, minister_id and provenance.produced_by to {minister_id!r}, and "
          f"provenance.repository_commit to {commit!r}.\n\n"
        + "For every substantive provisional proposition, state exactly what documentary "
          "information could weaken, qualify, or overturn it, and why that possible "
          "disconfirmation matters. Do not write an unfalsifiable proposition merely to "
          "survive this gate. Only documented_finding, supported_inference, and "
          "working_hypothesis belong in the provisional set."
    )


def _final_prompt(common_context: str, investigative_query: dict, investigative_response: dict,
                  provisional: dict, adversarial_query: dict, adversarial_response: dict) -> str:
    record = json.dumps(
        {
            "investigative_exchange": {
                "minister_query": investigative_query,
                "horus_response": investigative_response,
            },
            "provisional_judgment": provisional,
            "adversarial_exchange": {
                "minister_query": adversarial_query,
                "horus_response": adversarial_response,
            },
        },
        indent=2,
        sort_keys=True,
    )
    return (
        common_context
        + "\n\n"
        + "=" * 72
        + "\nMANDATORY INVESTIGATIVE + ADVERSARIAL RECORD\n"
        + "=" * 72
        + "\n\n"
        + record
        + "\n\n"
        + "=" * 72
        + "\nFINAL JUDGMENT ROUND\n"
        + "=" * 72
        + "\n\n"
        + "Now give the final ministerial judgment under the standing report requirements. "
          "You must confront the adversarial Horus return proposition by proposition. "
          "State whether each provisional proposition was retained, qualified, withdrawn, "
          "or left unresolved, and explain the evidentiary reason. Every material unfilled "
          "Horus request remains a limitation. NOT_GATHERED never means that the thing does "
          "not exist. Do not conceal a change from provisional to final judgment."
    )


def _source_head(repo_state: list[dict], house: str) -> str:
    for item in repo_state:
        if item.get("repository") == house:
            head = item.get("head", "")
            if len(head) == 40:
                return head
    raise RoundError(f"cannot determine exact commit for repository {house}")


def run(args) -> int:
    config = harness.load_config(Path(args.config).expanduser())
    estate = Path(config["estate"]).expanduser()
    hub = estate / "Sanctum"
    horus = estate / "Horus"
    as_of = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    stamp = as_of.isoformat()

    spec = harness.yaml_load((hub / SPEC_PATH).read_text(encoding="utf-8"))
    if str(spec.get("version")) != "1.3.0":
        raise RoundError("adversarial runner requires ASSEMBLY-SPEC-001 v1.3.0")

    ministers = config["ministers"]
    if args.minister not in ministers:
        raise RoundError(f"minister {args.minister!r} is not configured")
    house = ministers[args.minister]["house"]

    print("PULL")
    repo_state = harness.pull(estate, config["repositories"], not args.no_pull)
    minister_commit = _source_head(repo_state, house)
    horus_commit = _source_head(repo_state, "Horus")
    horus_command = _resolve_horus_command(horus, args)

    board = harness.yaml_load((horus / "boards" / f"{args.board}.yaml").read_text(encoding="utf-8"))
    manifest = harness.yaml_load((estate / house / "manifest.yaml").read_text(encoding="utf-8"))

    print("\nGATE")
    parity_record = harness.parity(estate, board, as_of)
    if parity_record["verdict"] == "HOLD" and not args.carry_mark:
        print("  THE GATE HOLDS. No minister query or judgment was called.")
        return 2

    carried = {"carried": False, "manifest_file": f"{args.board}-{stamp}.yaml", "text": ""}
    if parity_record["verdict"] == "HOLD":
        carried["carried"] = True
        carried["text"] = (
            "This adversarial round crossed a parity HOLD by explicit owner override. "
            f"The board carries {parity_record['gap_count']} named gaps."
        )

    question = Path(args.question_file).expanduser().resolve() if args.question_file else (
        hub / "boards" / args.board / f"{stamp}-question.md"
    )
    if not question.exists():
        raise RoundError(f"no board question at {question}")

    ctx = harness.assemble(estate, spec, house, args.minister, board, manifest, question, carried)
    common_context = ctx.text()
    inquiry_id = args.inquiry_id or f"{args.board}-{stamp}"

    call_config = dict(config["model"])
    if args.provider:
        call_config["provider"] = args.provider

    print("\nCALL 1 — MINISTER INVESTIGATIVE QUERY")
    first = harness.call(call_config, _query_prompt(common_context, inquiry_id, args.minister, minister_commit))
    investigative_query = _json_object(first["text"], "minister query call")
    validate_query(investigative_query)

    print("\nCALL 2 — HORUS INVESTIGATIVE GATHER")
    try:
        investigative_response = required_horus_call(
            investigative_query,
            lambda q: _run_horus_command(horus_command, q),
        )
    except HorusExchangeError as exc:
        raise RoundError(f"Horus investigative exchange contract violation: {exc}") from exc
    _require_horus_commit(investigative_response, horus_commit)

    print("\nCALL 3 — MINISTER PROVISIONAL JUDGMENT")
    provisional_call = harness.call(
        call_config,
        _provisional_prompt(
            common_context,
            investigative_query,
            investigative_response,
            inquiry_id,
            args.minister,
            minister_commit,
        ),
    )
    provisional = _json_object(provisional_call["text"], "minister provisional judgment call")
    validate_provisional_judgment(provisional)
    if provisional["inquiry_id"] != inquiry_id or provisional["minister_id"] != args.minister:
        raise RoundError("provisional judgment identity does not match this round")
    if provisional["provenance"]["repository_commit"] != minister_commit:
        raise RoundError("provisional judgment repository commit does not match the pinned minister")

    print("\nCALL 4 — HORUS ADVERSARIAL GATHER")
    try:
        adversarial_query, adversarial_response = required_adversarial_horus_call(
            provisional,
            lambda q: _run_horus_command(horus_command, q),
            investigative_query=investigative_query,
        )
    except HorusExchangeError as exc:
        raise RoundError(f"Horus adversarial exchange contract violation: {exc}") from exc
    _require_horus_commit(adversarial_response, horus_commit)

    print("\nCALL 5 — FINAL MINISTER JUDGMENT")
    final_context = _final_prompt(
        common_context,
        investigative_query,
        investigative_response,
        provisional,
        adversarial_query,
        adversarial_response,
    )
    final = harness.call(call_config, final_context)

    print("\nWRITE")
    exchange_root = hub / "exchanges"
    investigative_paths = write_exchange(exchange_root, investigative_query, investigative_response)
    adversarial_paths = write_adversarial_exchange(exchange_root, adversarial_query, adversarial_response)
    report_dir = hub / "reports" / args.board
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{args.minister}-{stamp}.md"
    manifest_path = report_dir / f"{args.minister}-{stamp}.round.json"
    provisional_path = report_dir / f"{args.minister}-{stamp}.provisional.json"
    report_path.write_text(final["text"].rstrip() + "\n", encoding="utf-8")
    provisional_path.write_text(json.dumps(provisional, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    round_record = {
        "record_type": "sovereign_adversarial_round",
        "assembly_spec": {"path": SPEC_PATH, "version": "1.3.0"},
        "inquiry_id": inquiry_id,
        "board": args.board,
        "minister": args.minister,
        "minister_repository_commit": minister_commit,
        "horus_repository_commit": horus_commit,
        "horus_runtime": CANONICAL_HORUS_RUNTIME if not args.horus_command else "TEST_OVERRIDE",
        "horus_acquisition_protocol": ACQUISITION_PROTOCOL,
        "common_context_sha256": hashlib.sha256(common_context.encode("utf-8")).hexdigest(),
        "final_context_sha256": hashlib.sha256(final_context.encode("utf-8")).hexdigest(),
        "parity": {
            "verdict": parity_record["verdict"],
            "gap_count": parity_record["gap_count"],
            "carried_across_hold": carried["carried"],
        },
        "horus_exchanges": [
            {
                "exchange_kind": "investigative",
                "query_id": investigative_query["query_id"],
                "request_path": investigative_paths["request"],
                "response_path": investigative_paths["response"],
                "exchange_sha256": exchange_digest(investigative_query, investigative_response),
                "response_status": investigative_response["status"],
                "unfilled_request_count": len(investigative_response["unfilled_requests"]),
            },
            {
                "exchange_kind": "adversarial",
                "query_id": adversarial_query["query_id"],
                "request_path": adversarial_paths["request"],
                "response_path": adversarial_paths["response"],
                "exchange_sha256": adversarial_exchange_digest(adversarial_query, adversarial_response),
                "response_status": adversarial_response["status"],
                "unfilled_request_count": len(adversarial_response["unfilled_requests"]),
            },
        ],
        "provisional_judgment": {
            "path": str(provisional_path),
            "proposition_count": len(provisional["propositions"]),
            "sha256": hashlib.sha256(
                json.dumps(provisional, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
        "model": {
            "provider": call_config["provider"],
            "model_requested": call_config.get("model"),
            "query_model_returned": first.get("model"),
            "provisional_model_returned": provisional_call.get("model"),
            "final_model_returned": final.get("model"),
        },
        "outputs": {
            "report": str(report_path),
            "provisional_judgment": str(provisional_path),
            "round_manifest": str(manifest_path),
        },
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }
    manifest_path.write_text(json.dumps(round_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  {report_path}")
    print(f"  {provisional_path}")
    print(f"  {manifest_path}")
    print(f"  investigative exchange sha256: {round_record['horus_exchanges'][0]['exchange_sha256']}")
    print(f"  adversarial exchange sha256: {round_record['horus_exchanges'][1]['exchange_sha256']}")
    print("\nNothing was certified. Final judgment followed a recorded adversarial evidence call.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run mandatory investigative and adversarial Minister -> Horus -> Minister rounds."
    )
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--board", required=True)
    parser.add_argument("--minister", required=True)
    parser.add_argument(
        "--horus-command",
        help="TEST ONLY: alternate command that reads query JSON on stdin and emits a Horus response. Production uses <estate>/Horus/runtime/gather.py.",
    )
    parser.add_argument(
        "--allow-horus-command-override",
        action="store_true",
        help="explicitly allow --horus-command for fixture tests; never use for a proving or certified Assembly run",
    )
    parser.add_argument("--inquiry-id")
    parser.add_argument("--question-file")
    parser.add_argument("--date")
    parser.add_argument("--provider")
    parser.add_argument("--carry-mark", action="store_true")
    parser.add_argument("--no-pull", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (RoundError, HorusExchangeError) as exc:
        print(f"ROUND ABORTED: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
