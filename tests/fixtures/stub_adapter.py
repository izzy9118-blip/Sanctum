from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVIDENCE_COMMIT = "55a9a75a7857a91f6db19a323668d20da3c83af3"
EVIDENCE_PATH = "records/inquiry-architecture/IAR-000000001.yaml"
MANIFEST_PATH = "manifests/cognitive-memory/MAN-000000001.json"


def git_bytes(root: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def build_report(
    repo_root: Path,
    release_commit: str,
    envelope: dict[str, Any],
    *,
    tamper_evidence: bool = False,
    failed: bool = False,
) -> dict[str, Any]:
    selection = envelope["routing"]["selected_ministers"][0]
    source = git_bytes(repo_root, EVIDENCE_COMMIT, EVIDENCE_PATH).decode(
        "utf-8"
    )
    excerpt = "".join(source.splitlines(keepends=True)[:3]).encode("utf-8")
    evidence_sha = hashlib.sha256(excerpt).hexdigest()
    if tamper_evidence:
        evidence_sha = "0" * 64
    manifest_raw = git_bytes(repo_root, release_commit, MANIFEST_PATH)
    manifest = json.loads(manifest_raw)
    manifest_blob = git_text(
        repo_root,
        "rev-parse",
        f"{release_commit}:{MANIFEST_PATH}",
    )
    now = datetime.now(timezone.utc).isoformat()
    evidence = {
        "evidence_id": "EVR-FED-000000001",
        "canonical_id": "IAR-000000001",
        "repository_full_name": selection["repository_full_name"],
        "git_commit": EVIDENCE_COMMIT,
        "path": EVIDENCE_PATH,
        "sha256": evidence_sha,
        "locator": (
            "IAR-000000001 identity and title; lines 1-3 "
            "(1-based, inclusive)"
        ),
        "direct_or_derived": "DIRECT",
        "source_classification": "REPOSITORY_GOVERNANCE",
        "support_summary": (
            "Identifies the bounded inquiry architecture fixture."
        ),
        "verified": True,
    }
    if failed:
        findings: list[dict[str, Any]] = []
        uncertainties = [
            {
                "uncertainty_id": "UNC-000000001",
                "statement": "The stub minister terminated before conclusion.",
                "effect": "PREVENTS_CONCLUSION",
                "resolvability": "UNKNOWN",
                "evidence_refs": [],
            }
        ]
        termination = {
            "status": "FAILED",
            "code": "STUB_EXECUTION_FAILED",
            "reason": "The stub produced a bounded failed report.",
            "retryable": True,
            "unresolved_items": ["UNC-000000001"],
            "error_code": "STUB_EXECUTION_FAILED",
        }
    else:
        findings = [
            {
                "finding_id": "FND-FED-000000001",
                "classification": "SUPPORTED_INFERENCE",
                "statement": (
                    "The evidence identifies a governed inquiry architecture."
                ),
                "rationale": (
                    "The cited lines supply the record identity and title."
                ),
                "confidence": "MODERATE",
                "evidence_refs": ["EVR-FED-000000001"],
                "uncertainty_refs": [],
                "dissent_refs": [],
            }
        ]
        uncertainties = []
        termination = {
            "status": "COMPLETED",
            "code": "COMPLETED_AUTHORIZED_UNIT",
            "reason": "The bounded stub unit completed.",
            "retryable": False,
            "unresolved_items": [],
        }
    report: dict[str, Any] = {
        "contract_version": "1.0.0",
        "report_id": (
            f"MREP-{envelope['envelope_id']}-{selection['minister_id']}"
        ),
        "report_status": "SUBMITTED",
        "secretary_validation_status": "NOT_YET_VALIDATED",
        "created_at": now,
        "inquiry": {
            "envelope_id": envelope["envelope_id"],
            "envelope_version": envelope["envelope_version"],
            "envelope_sha256": envelope["integrity"]["envelope_sha256"],
            "question_sha256": hashlib.sha256(
                envelope["question"]["text"].encode("utf-8")
            ).hexdigest(),
        },
        "minister": {
            "minister_id": selection["minister_id"],
            "manifest_id": selection["manifest_id"],
            "manifest_version": selection["manifest_version"],
            "name": "Leo Strauss",
            "office": "Minister of Political Philosophy",
        },
        "repository": {
            "full_name": selection["repository_full_name"],
            "git_commit": release_commit,
            "canonical_authority": "GIT",
        },
        "governing_manifest": {
            "id": manifest["manifest_id"],
            "version": manifest["version"],
            "path": MANIFEST_PATH,
            "sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "git_blob_sha": manifest_blob,
            "declared_repository_commit": manifest["repository_commit"],
        },
        "execution": {
            "run_id": (
                f"RUN-FED-{envelope['envelope_id']}-"
                f"{selection['minister_id']}"
            ),
            "started_at": now,
            "completed_at": now,
            "isolated_context": True,
            "engine": {
                "name": "Strict Stub Minister",
                "version": "1.0.0",
            },
            "procedure_ids": ["PROC-STUB-1"],
            "reasoner": {
                "provider": "TEST",
                "model": "STRICT-STUB",
                "prompt_id": "PROMPT-STUB",
                "prompt_version": "1.0",
            },
            "cache": {
                "status": "BYPASSED"
            },
        },
        "evidence": [evidence],
        "findings": findings,
        "uncertainties": uncertainties,
        "dissent": [],
        "termination": termination,
    }
    report["integrity"] = {
        "hash_algorithm": "SHA-256",
        "canonicalization": "RFC8785",
        "report_sha256": hashlib.sha256(canonical_bytes(report)).hexdigest(),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--envelope", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tamper-evidence", action="store_true")
    parser.add_argument("--failed", action="store_true")
    parser.add_argument("--exit-code", type=int, default=0)
    args = parser.parse_args()
    if args.exit_code:
        return args.exit_code
    envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
    report = build_report(
        Path(args.repo_root),
        args.release_commit,
        envelope,
        tamper_evidence=args.tamper_evidence,
        failed=args.failed,
    )
    output = Path(args.output)
    output.mkdir()
    (output / "ministerial-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
