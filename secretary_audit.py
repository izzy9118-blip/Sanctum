#!/usr/bin/env python3
"""Independent Secretary audit for forward Sanctum reasoned runs.

The Secretary does not reason for a minister and does not certify truth. It verifies
that the artifacts already produced by the Assembly satisfy the governing structural,
identity, hash, provenance, genealogy, and sovereign-file requirements. The audit is
performed from disk, not from model assurances or a minister's prose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import harness
from evidence_genealogy import GenealogyError, validate_genealogy_package
from minister_ground_files import validate_minister_ground_files

SPEC_PATH = "standards/assembly-spec.yaml"
REQUIRED_SPEC_VERSION = "1.5.0"


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
        "bindings": {
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run independent Secretary structural/provenance audit.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--board", required=True)
    parser.add_argument("--minister", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    try:
        config = harness.load_config(Path(args.config).expanduser())
        estate = Path(config["estate"]).expanduser()
        audit = audit_run(estate=estate, board=args.board, minister=args.minister, date=args.date)
        path = estate / "Sanctum" / "reports" / args.board / f"{args.minister}-{args.date}.secretary-audit.json"
        write_audit(path, audit)
        print(f"SECRETARY AUDIT PASS: {path}")
        print("No truth or completeness certification was performed.")
        return 0
    except (SecretaryAuditError, OSError, ValueError) as exc:
        print(f"SECRETARY AUDIT FAIL: {exc}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
