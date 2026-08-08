#!/usr/bin/env python3
"""The mandatory investigative round for reasoned Assembly runs.

Sequence:
    1. Build the same common context the Sovereign Harness would give the minister.
    2. CALL the minister for an investigative request only.
    3. CALL Horus through an explicit gather command; validate the full source trail.
    4. Inject the exact request and response into the context.
    5. CALL the minister for final judgment.
    6. WRITE the exchange, report, and round manifest.

A direct one-shot reasoned call that skips steps 2-4 is non-conforming under
ASSEMBLY-SPEC-001 v1.2.0.  This runner does not gather for Horus and does not judge
for the minister.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import harness
from minister_horus import (
    HorusExchangeError,
    exchange_digest,
    required_horus_call,
    validate_query,
    write_exchange,
)

SPEC_PATH = "standards/assembly-spec.yaml"
QUERY_CONTRACT_PATH = "contracts/minister-horus-query.schema.json"


class RoundError(RuntimeError):
    pass


def _json_object(text: str, label: str) -> dict:
    """Parse a model/tool response as one JSON object; no prose fallback."""
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RoundError(f"{label} did not return valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RoundError(f"{label} must return one JSON object")
    return value


def _run_horus_command(command: str, query: dict) -> dict:
    """Invoke the Horus gatherer as a hard subprocess boundary."""
    process = subprocess.run(
        command,
        input=json.dumps(query),
        text=True,
        shell=True,
        capture_output=True,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip() or "no detail"
        raise RoundError(f"HORUS CALL failed with exit {process.returncode}: {detail[:500]}")
    return _json_object(process.stdout, "Horus gatherer")


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
          "final judgment. Return ONE JSON object only. The request must comply with "
          f"{QUERY_CONTRACT_PATH}.\n\n"
        + f"Set inquiry_id to {inquiry_id!r}, minister_id to {minister_id!r}, and "
          f"provenance.repository_commit to {commit!r}. Create a stable query_id beginning "
          "with MHQ-. State information_needed, source_requirements with rationale, any "
          "specific document requests, relevant scope, disallowed substitutions, and "
          "reason_for_request.\n\n"
        + "You may specify what would count as adequate evidence. Except for an explicit "
          "document request, you may NOT select the sources Horus must use. Set "
          "source_selection_rule exactly to "
          "HORUS_RETAINS_SOURCE_SELECTION_INDEPENDENCE_EXCEPT_EXPLICIT_DOCUMENT_REQUESTS."
    )


def _final_prompt(common_context: str, query: dict, response: dict) -> str:
    exchange = json.dumps({"minister_query": query, "horus_response": response}, indent=2, sort_keys=True)
    return (
        common_context
        + "\n\n"
        + "=" * 72
        + "\nMANDATORY MINISTER-HORUS EXCHANGE\n"
        + "=" * 72
        + "\n\n"
        + exchange
        + "\n\n"
        + "=" * 72
        + "\nFINAL JUDGMENT ROUND\n"
        + "=" * 72
        + "\n\n"
        + "Now give the final ministerial judgment under the standing report requirements. "
          "The exchange above is part of the evidentiary record. You must state every "
          "material unfilled Horus request as a limitation; NOT_GATHERED never means that "
          "the thing does not exist. Do not conceal disagreement between your initial "
          "attention and what Horus actually returned."
    )


def _source_head(repo_state: list[dict], house: str) -> str:
    for item in repo_state:
        if item.get("repository") == house:
            head = item.get("head", "")
            if len(head) == 40:
                return head
    raise RoundError(f"cannot determine exact commit for minister house {house}")


def run(args) -> int:
    config = harness.load_config(Path(args.config).expanduser())
    estate = Path(config["estate"]).expanduser()
    hub = estate / "Sanctum"
    horus = estate / "Horus"
    as_of = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    stamp = as_of.isoformat()

    spec = harness.yaml_load((hub / SPEC_PATH).read_text(encoding="utf-8"))
    if str(spec.get("version")) != "1.2.0":
        raise RoundError("mandatory investigative runner requires ASSEMBLY-SPEC-001 v1.2.0")

    ministers = config["ministers"]
    if args.minister not in ministers:
        raise RoundError(f"minister {args.minister!r} is not configured")
    house = ministers[args.minister]["house"]

    print("PULL")
    repo_state = harness.pull(estate, config["repositories"], not args.no_pull)
    minister_commit = _source_head(repo_state, house)

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
            "This investigative round crossed a parity HOLD by explicit owner override. "
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
    query = _json_object(first["text"], "minister query call")
    validate_query(query)

    print("\nCALL 2 — HORUS GATHER")
    try:
        response = required_horus_call(query, lambda q: _run_horus_command(args.horus_command, q))
    except HorusExchangeError as exc:
        raise RoundError(f"Horus exchange contract violation: {exc}") from exc

    print("\nCALL 3 — FINAL MINISTER JUDGMENT")
    final_context = _final_prompt(common_context, query, response)
    final = harness.call(call_config, final_context)

    print("\nWRITE")
    exchange_root = hub / "exchanges"
    paths = write_exchange(exchange_root, query, response)
    report_dir = hub / "reports" / args.board
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{args.minister}-{stamp}.md"
    manifest_path = report_dir / f"{args.minister}-{stamp}.round.json"
    report_path.write_text(final["text"].rstrip() + "\n", encoding="utf-8")

    round_record = {
        "record_type": "sovereign_investigative_round",
        "assembly_spec": {"path": SPEC_PATH, "version": "1.2.0"},
        "inquiry_id": inquiry_id,
        "board": args.board,
        "minister": args.minister,
        "minister_repository_commit": minister_commit,
        "common_context_sha256": hashlib.sha256(common_context.encode("utf-8")).hexdigest(),
        "final_context_sha256": hashlib.sha256(final_context.encode("utf-8")).hexdigest(),
        "parity": {
            "verdict": parity_record["verdict"],
            "gap_count": parity_record["gap_count"],
            "carried_across_hold": carried["carried"],
        },
        "horus_exchange": {
            "query_id": query["query_id"],
            "request_path": paths["request"],
            "response_path": paths["response"],
            "exchange_sha256": exchange_digest(query, response),
            "response_status": response["status"],
            "unfilled_request_count": len(response["unfilled_requests"]),
        },
        "model": {
            "provider": call_config["provider"],
            "model_requested": call_config.get("model"),
            "query_model_returned": first.get("model"),
            "final_model_returned": final.get("model"),
        },
        "outputs": {"report": str(report_path), "round_manifest": str(manifest_path)},
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }
    manifest_path.write_text(json.dumps(round_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  {report_path}")
    print(f"  {manifest_path}")
    print(f"  exchange sha256: {round_record['horus_exchange']['exchange_sha256']}")
    print("\nNothing was certified. Final judgment is now auditable through the mandatory Horus exchange.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a mandatory Minister -> Horus -> Minister round.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--board", required=True)
    parser.add_argument("--minister", required=True)
    parser.add_argument("--horus-command", required=True,
                        help="command that reads one query JSON object on stdin and returns one Horus response JSON object on stdout")
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
