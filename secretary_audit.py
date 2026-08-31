#!/usr/bin/env python3
"""Independent Secretary audit for forward Sanctum reasoned runs.

The Secretary does not reason for a minister and does not certify truth. It verifies
that the artifacts already produced by the Assembly satisfy the governing structural,
identity, hash, provenance, genealogy, and sovereign-file requirements. The audit is
performed from disk, not from model assurances or a minister's prose.

Under SECRETARY-CHARTER-001 the office also audits the dispatch itself — voices held
distinct, provenance flagged per principal, the judgment labelled as the minister's
own and placed after the parties' positions, and the counterfeit and invented-ground
scans. Those checks are structural too: they read markers, never merit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import harness
import secretary_gate
from evidence_genealogy import GenealogyError, validate_genealogy_package
from ministerial_silence import STATES as SILENCE_STATES
from minister_ground_files import validate_minister_ground_files

SPEC_PATH = "standards/assembly-spec.yaml"
REQUIRED_SPEC_VERSION = "1.5.0"

# The audit markers required by offices/secretary/charter.md. They exist because a
# condensed dispatch and a distinct one read alike from the inside; only a seam a
# machine can find survives a fluent narrator.
POSITION_HEADING = re.compile(r"^#{1,6}\s*POSITION\s*[—-]\s*(?P<name>.+?)\s*\[(?P<id>[^\]]+)\]\s*$")
PROVENANCE_LINE = re.compile(r"^PROVENANCE:\s*(?P<flag>[A-Z_]+)\s*[—-]\s*(?P<language>.+?)\s*$")
SILENCE_LINE = re.compile(r"^SILENCE:\s*(?P<state>[A-Z_]+)\s*$")
JUDGMENT_HEADING = re.compile(r"^#{1,6}\s*MINISTERIAL JUDGMENT\s*[—-]\s*(?P<minister>.+?)\s*$")
SYNTHESIS_VOICES = ("president", "synthesis", "synthesizer", "secretary")

COUNTERFEIT_FRAME_CAPTURE = "FRAME_CAPTURE_VIA_SUBJECT_SELF_DESCRIPTION"
COUNTERFEIT_CONDENSED_VOICES = "CONDENSED_VOICES_ONE_NARRATOR"
VOID_STATUS = secretary_gate.VOID_STATUS


class SecretaryAuditError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SecretaryAuditError(message)


def _load_json(path: Path) -> dict:
    _require(path.is_file(), f"required artifact missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SecretaryAuditError(f"invalid JSON at {path}: {exc}") from exc
    _require(isinstance(value, dict), f"expected JSON object at {path}")
    return value


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_sha256(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _inside(base: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _artifact_path(hub: Path, recorded: str, fallback: Path) -> Path:
    if not recorded:
        return fallback
    path = Path(recorded)
    if not path.is_absolute():
        path = hub / path
    _require(_inside(hub, path), f"recorded artifact escapes Sanctum: {recorded}")
    return path


def _exchange_records(round_record: dict, hub: Path) -> list[dict]:
    bindings = round_record.get("horus_exchanges")
    _require(isinstance(bindings, list) and len(bindings) == 2,
             "Secretary requires exactly two recorded Horus exchanges")
    output = []
    for binding in bindings:
        _require(isinstance(binding, dict), "Horus exchange binding must be an object")
        for field in ("exchange_kind", "query_id", "exchange_sha256", "request_path", "response_path"):
            _require(isinstance(binding.get(field), str) and binding[field],
                     f"Horus exchange binding missing {field}")
        request_path = _artifact_path(hub, binding["request_path"], hub / "__missing_request__")
        response_path = _artifact_path(hub, binding["response_path"], hub / "__missing_response__")
        request = _load_json(request_path)
        response = _load_json(response_path)
        query_id = binding["query_id"]
        _require(request.get("query_id") == query_id, f"{query_id} request identity mismatch")
        _require(response.get("query_id") == query_id, f"{query_id} response identity mismatch")
        # Preserve the runtime's binding algorithm: the stored exchange hash is the
        # canonical hash of request+response, not a hash of filesystem formatting.
        calculated = _canonical_sha256({"request": request, "response": response})
        _require(calculated == binding["exchange_sha256"],
                 f"{query_id} exchange hash does not match request/response artifacts")
        output.append({
            "exchange_kind": binding["exchange_kind"],
            "query_id": query_id,
            "exchange_sha256": binding["exchange_sha256"],
            "request": request,
            "response": response,
        })
    return output


def _dispatch_blocks(text: str) -> tuple[list, dict | None]:
    """Read the dispatch's audit markers. No sentence of it is interpreted."""
    blocks: list[dict] = []
    judgment: dict | None = None
    current: dict | None = None
    for number, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        heading = POSITION_HEADING.match(stripped)
        if heading:
            current = {
                "principal_id": heading.group("id").strip(),
                "name": heading.group("name").strip(),
                "line": number,
                "provenance_flag": None,
                "language": None,
                "silence_state": None,
            }
            blocks.append(current)
            continue
        judged = JUDGMENT_HEADING.match(stripped)
        if judged:
            judgment = {"minister": judged.group("minister").strip(), "line": number}
            current = None
            continue
        if current is None:
            continue
        provenance = PROVENANCE_LINE.match(stripped)
        if provenance:
            current["provenance_flag"] = provenance.group("flag")
            current["language"] = provenance.group("language").strip()
            continue
        silence = SILENCE_LINE.match(stripped)
        if silence:
            current["silence_state"] = silence.group("state")
    return blocks, judgment


_PROVENANCE_RANK = {"NOT_GATHERED": 0, "FILLED_FROM_ELSEWHERE": 1, "HEARD_IN_OWN_WORDS": 2}


def audit_dispatch(checklist: dict, dispatch_text: str) -> dict:
    """The post-run audit of a dispatch. Procedure only: markers, never merit."""
    secretary_gate.validate_checklist(checklist)
    blocks, judgment = _dispatch_blocks(dispatch_text)
    roster = {entry["principal_id"]: entry for entry in checklist["roster"]}
    enumerated = [entry for entry in checklist["roster"] if entry["roster_state"] == "ENUMERATED"]
    attributed = [block["principal_id"] for block in blocks]

    failures: list[str] = []
    counterfeits: list[str] = []

    missing = sorted(entry["principal_id"] for entry in enumerated if entry["principal_id"] not in attributed)
    if missing:
        failures.append("voices not held distinct: no attributed position for " + ", ".join(missing))
    if any(secretary_gate._is_population(roster[pid]["type"]) for pid in missing):
        counterfeits.append(COUNTERFEIT_FRAME_CAPTURE)
    if len(set(attributed)) < 2 <= len(enumerated):
        counterfeits.append(COUNTERFEIT_CONDENSED_VOICES)

    invented = sorted({pid for pid in attributed if pid not in roster})
    if invented:
        failures.append("invented ground: the dispatch attributes a position to a principal who is not on "
                        "the frozen board: " + ", ".join(invented))

    for block in blocks:
        who = block["principal_id"]
        identity = f"{who} (line {block['line']})"
        if who.lower() == checklist["minister_id"].lower() or \
                any(voice in who.lower() or voice in block["name"].lower() for voice in SYNTHESIS_VOICES):
            failures.append(f"the synthesis authors a party's view: a POSITION block is attributed to {identity}")
        if block["provenance_flag"] not in _PROVENANCE_RANK:
            failures.append(f"no provenance flag for {identity}")
            continue
        recorded = roster.get(who, {}).get("provenance_flag")
        if recorded in _PROVENANCE_RANK and _PROVENANCE_RANK[block["provenance_flag"]] > _PROVENANCE_RANK[recorded]:
            failures.append(
                f"{identity} is flagged {block['provenance_flag']} in the dispatch and {recorded} on the frozen "
                "board; no judgment about a principal rises above the tier at which that principal was heard")
        if block["provenance_flag"] == "NOT_GATHERED" and block["silence_state"] not in SILENCE_STATES:
            failures.append(f"{identity} was not gathered and its silence is untyped; "
                            "MINISTERIAL-SILENCE-001 states are required")

    if judgment is None:
        failures.append("the judgment is not labelled: no MINISTERIAL JUDGMENT marker naming the minister")
    else:
        if judgment["minister"].lower() != checklist["minister_id"].lower():
            failures.append(f"the judgment is labelled {judgment['minister']!r}, not the minister of this run "
                            f"({checklist['minister_id']})")
        last_position = max((block["line"] for block in blocks), default=0)
        if judgment["line"] < last_position:
            failures.append("the judgment is placed before the parties' positions; it stands after them")

    status = VOID_STATUS if failures else "SECRETARY_DISPATCH_AUDIT_PASS_NOT_TRUTH_CERTIFICATION"
    return {
        "record_type": "secretary_dispatch_audit",
        "gate_standard": secretary_gate.GATE_STANDARD,
        "charter": secretary_gate.CHARTER_PATH,
        "checklist_id": checklist["checklist_id"],
        "checklist_sha256": secretary_gate.checklist_digest(checklist),
        "inquiry_id": checklist["inquiry_id"],
        "board": checklist["board"],
        "minister_id": checklist["minister_id"],
        "room": checklist["room"],
        "status": status,
        "checks": {
            "voices_held_distinct": "FAIL" if missing else "PASS",
            "provenance_flag_per_principal": "PASS" if not any(
                block["provenance_flag"] not in _PROVENANCE_RANK for block in blocks) else "FAIL",
            "ministerial_silence_typed": "PASS" if not any(
                block["provenance_flag"] == "NOT_GATHERED" and block["silence_state"] not in SILENCE_STATES
                for block in blocks) else "FAIL",
            "judgment_labelled_and_placed_after_positions": "PASS" if judgment and not any(
                f.startswith("the judgment") for f in failures) else "FAIL",
            "counterfeit_scan": "FLAGGED" if counterfeits else "PASS",
            "invented_ground_scan": "FAIL" if invented else "PASS",
        },
        "attributed_principals": sorted(set(attributed)),
        "unattributed_principals": missing,
        "counterfeits_triggered": sorted(set(counterfeits)),
        "failures": failures,
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }


def require_conforming_dispatch(checklist: dict, dispatch_text: str) -> dict:
    audit = audit_dispatch(checklist, dispatch_text)
    if audit["failures"]:
        detail = "; ".join(audit["failures"])
        if audit["counterfeits_triggered"]:
            detail += " | counterfeits: " + ", ".join(audit["counterfeits_triggered"])
        raise SecretaryAuditError(f"dispatch audit failed: {detail}")
    return audit


def _gate_record(round_record: dict, hub: Path) -> dict:
    """Re-verify from disk that this run passed the pre-run gate before it called."""
    binding = round_record.get("secretary_gate")
    _require(isinstance(binding, dict),
             "round record carries no secretary_gate binding: the run was never gated")
    checklist_path = _artifact_path(hub, binding.get("checklist_path", ""), hub / "__missing_checklist__")
    token_path = _artifact_path(hub, binding.get("token_path", ""), hub / "__missing_token__")
    checklist = _load_json(checklist_path)
    token = _load_json(token_path)
    try:
        secretary_gate.verify_token(token, checklist=checklist)
    except secretary_gate.SecretaryGateError as exc:
        raise SecretaryAuditError(f"pre-run gate re-verification failed: {exc}") from exc
    completed = list(binding.get("stages_completed") or [])
    _require(completed[:len(secretary_gate.REQUIRED_SEQUENCE)] == list(secretary_gate.REQUIRED_SEQUENCE),
             f"recorded stages {completed} do not perform the constitutional sequence")
    _require(binding.get("checklist_sha256") == secretary_gate.checklist_digest(checklist),
             "round record checklist hash does not match the recorded checklist")

    dispatch_path = _artifact_path(hub, binding.get("dispatch_path", ""), hub / "__missing_dispatch__")
    _require(dispatch_path.is_file(), f"audited dispatch missing: {dispatch_path}")
    dispatch_text = dispatch_path.read_text(encoding="utf-8")
    _require(hashlib.sha256(dispatch_text.encode("utf-8")).hexdigest() == binding.get("dispatch_sha256"),
             "the dispatch on disk is not the dispatch the round recorded")
    dispatch_audit = require_conforming_dispatch(checklist, dispatch_text)
    return {
        "checklist": checklist,
        "token": token,
        "checklist_path": checklist_path,
        "token_path": token_path,
        "dispatch_path": dispatch_path,
        "dispatch_audit": dispatch_audit,
    }


def audit_run(*, estate: Path, board: str, minister: str, date: str) -> dict:
    hub = estate / "Sanctum"
    _require(hub.is_dir(), f"Sanctum house missing: {hub}")
    spec = harness.yaml_load((hub / SPEC_PATH).read_text(encoding="utf-8"))
    _require(str(spec.get("version")) == REQUIRED_SPEC_VERSION,
             f"Secretary audit requires governing ASSEMBLY-SPEC-001 v{REQUIRED_SPEC_VERSION}")

    report_dir = hub / "reports" / board
    stem = f"{minister}-{date}"
    round_path = report_dir / f"{stem}.round.json"
    package_path = report_dir / f"{stem}.final.json"
    genealogy_path = report_dir / f"{stem}.genealogy.json"
    report_path = report_dir / f"{stem}.md"

    round_record = _load_json(round_path)
    _require(round_record.get("record_type") == "sovereign_genealogical_round",
             "round record is not a sovereign genealogical round")
    _require(round_record.get("minister_id") in (None, minister), "round minister identity mismatch")
    _require(round_record.get("assembly_spec", {}).get("version") == "1.4.0",
             "audited round was not produced by genealogy-governed v1.4")

    outputs = round_record.get("outputs") or {}
    package_path = _artifact_path(hub, outputs.get("final_judgment_package", ""), package_path)
    genealogy_path = _artifact_path(hub, outputs.get("proposition_evidence_genealogy", ""), genealogy_path)
    _require(report_path.is_file(), f"rendered Ministerial Report missing: {report_path}")

    package = _load_json(package_path)
    genealogy = _load_json(genealogy_path)
    _require(package.get("minister_id") == minister, "final package minister identity mismatch")
    inquiry_id = round_record.get("inquiry_id")
    _require(package.get("inquiry_id") == inquiry_id, "final package inquiry identity mismatch")

    repository_commit = round_record.get("minister_repository_commit")
    _require(package.get("repository", {}).get("git_commit") == repository_commit,
             "final package minister commit differs from round pin")

    package_binding = round_record.get("final_judgment_package") or {}
    package_sha = _canonical_sha256(package)
    _require(package_binding.get("sha256") == package_sha,
             "round record final judgment package hash mismatch")
    _require(package_binding.get("proposition_count") == len(package.get("propositions", [])),
             "round record proposition count mismatch")

    gate = _gate_record(round_record, hub)
    dispatch_audit = gate["dispatch_audit"]

    exchanges = _exchange_records(round_record, hub)
    try:
        validation = validate_genealogy_package(package, exchanges)
        validate_minister_ground_files(package, estate)
    except GenealogyError as exc:
        raise SecretaryAuditError(f"genealogy re-validation failed: {exc}") from exc

    _require(genealogy.get("record_type") == "proposition_evidence_genealogy",
             "genealogy artifact record_type mismatch")
    _require(genealogy.get("final_judgment_package_sha256") == package_sha,
             "genealogy artifact is not bound to the final judgment package")
    _require(genealogy.get("proposition_count") == validation["proposition_count"],
             "genealogy artifact proposition count mismatch")
    _require(genealogy.get("resolved") == validation["resolved"],
             "genealogy artifact differs from independent re-resolution")
    _require(genealogy.get("certification") == "NONE_SELF_CERTIFICATION_PROHIBITED",
             "genealogy artifact certification law mismatch")
    _require(round_record.get("certification") == "NONE_SELF_CERTIFICATION_PROHIBITED",
             "round record certification law mismatch")

    checks = {
        "governing_secretary_spec": "PASS",
        "secretary_pre_run_gate": "PASS",
        "dispatch_voices_and_placement": "PASS",
        "artifact_presence": "PASS",
        "round_identity": "PASS",
        "pinned_minister_commit": "PASS",
        "final_package_hash": "PASS",
        "horus_exchange_bindings": "PASS",
        "proposition_genealogy_reresolution": "PASS",
        "sovereign_minister_files": "PASS",
        "genealogy_artifact_binding": "PASS",
        "no_self_certification": "PASS",
    }
    return {
        "record_type": "secretary_audit",
        "inquiry_id": inquiry_id,
        "board": board,
        "minister_id": minister,
        "date": date,
        "status": "SECRETARY_STRUCTURAL_AUDIT_PASS_NOT_TRUTH_CERTIFICATION",
        "checks": checks,
        "dispatch_audit": dispatch_audit,
        "bindings": {
            "checklist_path": str(gate["checklist_path"]),
            "checklist_sha256": secretary_gate.checklist_digest(gate["checklist"]),
            "pass_token_path": str(gate["token_path"]),
            "pass_token_sha256": gate["token"]["token_sha256"],
            "audited_dispatch_path": str(gate["dispatch_path"]),
            "round_path": str(round_path),
            "round_sha256": _sha256_file(round_path),
            "final_package_path": str(package_path),
            "final_package_sha256": package_sha,
            "genealogy_path": str(genealogy_path),
            "genealogy_sha256": _sha256_file(genealogy_path),
            "rendered_report_path": str(report_path),
            "rendered_report_sha256": _sha256_file(report_path),
            "minister_repository_commit": repository_commit,
            "horus_exchange_sha256": [item["exchange_sha256"] for item in exchanges],
        },
        "certification": "NONE_SELF_CERTIFICATION_PROHIBITED",
    }


def write_audit(path: Path, audit: dict) -> None:
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _dispatch_only(args) -> int:
    """Audit a dispatch produced in any room, including a chat run logged afterwards."""
    checklist = json.loads(Path(args.checklist).expanduser().read_text(encoding="utf-8"))
    text = Path(args.dispatch).expanduser().read_text(encoding="utf-8")
    audit = audit_dispatch(checklist, text)
    if args.audit_out:
        write_audit(Path(args.audit_out).expanduser(), audit)
    if audit["failures"]:
        print(json.dumps(audit, indent=2, sort_keys=True))
        print(f"\nSECRETARY DISPATCH AUDIT: {VOID_STATUS}", file=sys.stderr)
        print("The run may be preserved as history. It may not enter reports/, the ledger, or "
              "synthesis. Escalation is to the owner only.", file=sys.stderr)
        return 6
    print(json.dumps(audit, indent=2, sort_keys=True))
    print("\nSECRETARY DISPATCH AUDIT PASS. Procedure only; no substance was graded.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run independent Secretary structural/provenance audit.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--board")
    parser.add_argument("--minister")
    parser.add_argument("--date")
    parser.add_argument("--checklist", help="post-run dispatch audit: the recorded pre-run checklist")
    parser.add_argument("--dispatch", help="post-run dispatch audit: the rendered dispatch to audit")
    parser.add_argument("--audit-out", help="where to write the dispatch audit record")
    args = parser.parse_args(argv)
    if args.checklist or args.dispatch:
        if not (args.checklist and args.dispatch):
            print("SECRETARY AUDIT FAIL: --checklist and --dispatch are given together", file=sys.stderr)
            return 2
        try:
            return _dispatch_only(args)
        except (SecretaryAuditError, secretary_gate.SecretaryGateError, OSError, ValueError) as exc:
            print(f"SECRETARY AUDIT FAIL: {exc}", file=sys.stderr)
            return 5
    if not (args.board and args.minister and args.date):
        print("SECRETARY AUDIT FAIL: --board, --minister and --date are required for a run audit",
              file=sys.stderr)
        return 2
    try:
        config = harness.load_config(Path(args.config).expanduser())
        estate = Path(config["estate"]).expanduser()
        audit = audit_run(estate=estate, board=args.board, minister=args.minister, date=args.date)
        path = estate / "Sanctum" / "reports" / args.board / f"{args.minister}-{args.date}.secretary-audit.json"
        write_audit(path, audit)
        print(f"SECRETARY AUDIT PASS: {path}")
        print("No truth or completeness certification was performed.")
        return 0
    except (SecretaryAuditError, secretary_gate.SecretaryGateError, OSError, ValueError) as exc:
        print(f"SECRETARY AUDIT FAIL: {exc}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
