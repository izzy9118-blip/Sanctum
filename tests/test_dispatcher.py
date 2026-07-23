from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from sanctum_federation.contracts import ContractSet
from sanctum_federation.dispatcher import AssemblyDispatcher
from sanctum_federation.registry import RegistrySnapshot

from .helpers import (
    SANCTUM_ROOT,
    custos_root,
    envelope,
    write_json,
)


STUB_ADAPTER = Path(__file__).parent / "fixtures" / "stub_adapter.py"


def _config(tmp_path: Path, *extra: str) -> Path:
    value = {
        "config_version": "1.0.0",
        "adapters": [
            {
                "minister_id": "MIN-000000001",
                "repository_full_name": "izzy9118-blip/custos",
                "repository_root": str(custos_root()),
                "command": [
                    sys.executable,
                    str(STUB_ADAPTER),
                    "--repo-root",
                    "{repository_root}",
                    "--release-commit",
                    "{repository_commit}",
                    "--envelope",
                    "{envelope_path}",
                    "--output",
                    "{output_dir}",
                    *extra,
                ],
                "report_relative_path": "ministerial-report.json",
                "timeout_seconds": 60,
            }
        ],
    }
    path = tmp_path / "dispatch-config.json"
    write_json(path, value)
    return path


def _envelope_path(tmp_path: Path) -> Path:
    contracts = ContractSet.load(SANCTUM_ROOT)
    registry = RegistrySnapshot.load(SANCTUM_ROOT, contracts)
    path = tmp_path / "inquiry-envelope.json"
    write_json(path, envelope(registry))
    return path


def _dispatch(
    tmp_path: Path,
    *,
    extra: tuple[str, ...] = (),
) -> Path:
    return AssemblyDispatcher(
        sanctum_root=SANCTUM_ROOT,
        secretary_actor_id="SANCTUM-CONSTITUTIONAL-SECRETARY",
        max_workers=4,
        verify_checkouts=False,
    ).dispatch(
        envelope_path=_envelope_path(tmp_path),
        adapter_config_path=_config(tmp_path, *extra),
        output_dir=tmp_path / "dispatch-record",
    )


def test_dispatcher_preserves_only_bounded_assembly_records(tmp_path):
    output = _dispatch(tmp_path)
    receipt = json.loads(
        (output / "dispatch-receipt.json").read_text(encoding="utf-8")
    )
    validation = json.loads(
        (
            output
            / "ministers/MIN-000000001/secretary-validation.json"
        ).read_text(encoding="utf-8")
    )

    assert receipt["status"] == "COMPLETED_VALIDATED"
    assert receipt["minister_results"][0]["status"] == "VALIDATED"
    assert validation["outcome"] == "VALIDATED"
    assert validation["certification_status"] == "NOT_CERTIFIED"
    assert (output / "inquiry-envelope.json").is_file()
    assert (
        output / "ministers/MIN-000000001/ministerial-report.json"
    ).is_file()
    assert not list(output.rglob("phase_reasoning_records.json"))
    assert not list(output.rglob("evidence-bundle.json"))
    assert not list(output.rglob("adapter-output"))


def test_dispatcher_quarantines_report_with_false_evidence(tmp_path):
    output = _dispatch(tmp_path, extra=("--tamper-evidence",))
    receipt = json.loads(
        (output / "dispatch-receipt.json").read_text(encoding="utf-8")
    )
    validation = json.loads(
        (
            output
            / "ministers/MIN-000000001/secretary-validation.json"
        ).read_text(encoding="utf-8")
    )

    assert receipt["status"] == "REJECTED_REPORTS"
    assert receipt["minister_results"][0]["status"] == (
        "VALIDATION_REJECTED"
    )
    assert validation["outcome"] == "REJECTED"


def test_dispatcher_records_nonzero_adapter_exit_without_fabricating_report(
    tmp_path,
):
    output = _dispatch(tmp_path, extra=("--exit-code", "7"))
    receipt = json.loads(
        (output / "dispatch-receipt.json").read_text(encoding="utf-8")
    )

    assert receipt["status"] == "DISPATCH_FAILED"
    assert receipt["minister_results"][0]["status"] == "EXECUTION_FAILED"
    assert not (
        output / "ministers/MIN-000000001/ministerial-report.json"
    ).exists()


def test_valid_failed_minister_report_is_preserved_as_limitation(tmp_path):
    output = _dispatch(tmp_path, extra=("--failed",))
    receipt = json.loads(
        (output / "dispatch-receipt.json").read_text(encoding="utf-8")
    )

    assert receipt["status"] == "COMPLETED_WITH_MINISTER_LIMITATIONS"
    result = receipt["minister_results"][0]
    assert result["status"] == "VALIDATED_WITH_MINISTER_LIMITATION"
    assert result["secretary_outcome"] == "VALIDATED"
    assert result["report_termination_status"] == "FAILED"


def test_dispatch_output_is_append_only(tmp_path):
    output = _dispatch(tmp_path)
    dispatcher = AssemblyDispatcher(
        sanctum_root=SANCTUM_ROOT,
        secretary_actor_id="SANCTUM-CONSTITUTIONAL-SECRETARY",
        verify_checkouts=False,
    )
    with pytest.raises(FileExistsError):
        dispatcher.dispatch(
            envelope_path=_envelope_path(tmp_path),
            adapter_config_path=_config(tmp_path),
            output_dir=output,
        )
