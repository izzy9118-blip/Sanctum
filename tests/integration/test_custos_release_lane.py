from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from sanctum_federation.contracts import ContractSet
from sanctum_federation.dispatcher import AssemblyDispatcher
from sanctum_federation.git_snapshot import GitSnapshot
from sanctum_federation.integrity import object_sha256_without_integrity
from sanctum_federation.registry import RegistrySnapshot

from tests.helpers import (
    SANCTUM_ROOT,
    custos_root,
    envelope,
    write_json,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_CUSTOS_INTEGRATION") != "1",
        reason="Set RUN_CUSTOS_INTEGRATION=1 for the released Custos lane",
    ),
]

GOVERNED_COMMIT = "55a9a75a7857a91f6db19a323668d20da3c83af3"
EVIDENCE_PATH = "records/inquiry-architecture/IAR-000000001.yaml"


def _evidence_bundle(repo_root: Path) -> dict:
    source = GitSnapshot(repo_root).read_text(
        GOVERNED_COMMIT,
        EVIDENCE_PATH,
    )
    excerpt = "".join(source.splitlines(keepends=True)[:3])
    value = {
        "contract_version": "1.0.0",
        "bundle_id": "EVB-FEDERATION-INTEGRATION",
        "bundle_version": "1.0.0",
        "created_at": "2026-07-23T12:01:00-05:00",
        "repository_full_name": "izzy9118-blip/custos",
        "items": [
            {
                "evidence_id": "EVR-FED-000000001",
                "canonical_id": "IAR-000000001",
                "git_commit": GOVERNED_COMMIT,
                "path": EVIDENCE_PATH,
                "start_line": 1,
                "end_line": 3,
                "sha256": hashlib.sha256(
                    excerpt.encode("utf-8")
                ).hexdigest(),
                "source_role": "REPOSITORY_CONTEXT",
                "source_classification": "REPOSITORY_GOVERNANCE",
                "direct_or_derived": "DIRECT",
                "citation": "IAR-000000001 identity and title",
                "support_summary": (
                    "Identifies the governing inquiry architecture used by "
                    "the release integration fixture."
                ),
            }
        ],
    }
    value["integrity"] = {
        "hash_algorithm": "SHA-256",
        "canonicalization": "RFC8785",
        "bundle_sha256": object_sha256_without_integrity(value),
    }
    return value


def _reasoner(path: Path) -> None:
    path.write_text(
        """import json
import sys

request = json.load(sys.stdin)
phase = request["phase_number"]
print(json.dumps({
    "run_id": request["run_id"],
    "state": request["state"],
    "completed": True,
    "summary": f"Completed released federation phase {phase}.",
    "candidate_statements": [{
        "candidate_id": f"CAND-FED-{phase:02d}",
        "text": f"A source-bounded candidate statement from phase {phase}.",
        "epistemic_classification": (
            "WORKING_HYPOTHESIS" if phase == 7 else "SUPPORTED_INFERENCE"
        ),
        "evidence_record_ids": ["EVR-FED-000000001"],
        "limitations": (
            ["The fixture establishes no documentary truth."]
            if phase == 10
            else []
        ),
    }],
}))
""",
        encoding="utf-8",
    )


def test_released_custos_adapter_dispatches_and_validates_end_to_end(
    tmp_path,
    monkeypatch,
):
    repo_root = custos_root()
    contracts = ContractSet.load(SANCTUM_ROOT)
    registry = RegistrySnapshot.load(SANCTUM_ROOT, contracts)
    entry = registry.entries[0]
    assert GitSnapshot(repo_root).head() == entry.repository_commit

    envelope_path = tmp_path / "inquiry-envelope.json"
    evidence_path = tmp_path / "evidence-bundle.json"
    reasoner_path = tmp_path / "reasoner.py"
    config_path = tmp_path / "dispatch-config.json"
    write_json(envelope_path, envelope(registry))
    write_json(evidence_path, _evidence_bundle(repo_root))
    _reasoner(reasoner_path)

    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    custos_source = str(repo_root / "inquiry_engine/src")
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join(
            item
            for item in (custos_source, existing_pythonpath)
            if item
        ),
    )
    config = {
        "config_version": "1.0.0",
        "adapters": [
            {
                "minister_id": entry.minister_id,
                "repository_full_name": entry.repository_full_name,
                "repository_root": str(repo_root),
                "command": [
                    sys.executable,
                    "-m",
                    "custos_engine.cli",
                    "federation-run",
                    "--repo-root",
                    "{repository_root}",
                    "--release-commit",
                    "{repository_commit}",
                    "--envelope",
                    "{envelope_path}",
                    "--evidence-bundle",
                    str(evidence_path),
                    "--output",
                    "{output_dir}",
                    "--reasoner-command",
                    f"{sys.executable} {reasoner_path}",
                    "--reasoner-timeout-seconds",
                    "30",
                    "--reasoner-provider",
                    "TEST",
                    "--reasoner-model",
                    "STRICT-STUB",
                    "--reasoner-model-revision",
                    "1",
                    "--prompt-id",
                    "PROMPT-FEDERATION-INTEGRATION",
                    "--prompt-version",
                    "1.0",
                ],
                "report_relative_path": "ministerial-report.json",
                "timeout_seconds": 300,
            }
        ],
    }
    write_json(config_path, config)

    output = AssemblyDispatcher(
        sanctum_root=SANCTUM_ROOT,
        secretary_actor_id="SANCTUM-CONSTITUTIONAL-SECRETARY",
        verify_checkouts=False,
    ).dispatch(
        envelope_path=envelope_path,
        adapter_config_path=config_path,
        output_dir=tmp_path / "release-dispatch",
    )
    receipt = json.loads(
        (output / "dispatch-receipt.json").read_text(encoding="utf-8")
    )
    report = json.loads(
        (
            output
            / "ministers/MIN-000000001/ministerial-report.json"
        ).read_text(encoding="utf-8")
    )
    validation = json.loads(
        (
            output
            / "ministers/MIN-000000001/secretary-validation.json"
        ).read_text(encoding="utf-8")
    )

    assert receipt["status"] == "COMPLETED_WITH_MINISTER_LIMITATIONS"
    assert report["repository"]["git_commit"] == entry.repository_commit
    assert len(report["findings"]) == 10
    assert report["secretary_validation_status"] == "NOT_YET_VALIDATED"
    assert validation["outcome"] == "VALIDATED"
    assert validation["certification_status"] == "NOT_CERTIFIED"
