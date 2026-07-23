from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import ContractSet
from .errors import SanctumFederationError
from .git_snapshot import GitSnapshot
from .integrity import (
    iso8601,
    object_sha256_without_integrity,
    read_json,
    verify_object_integrity,
    write_json_exclusive,
    utc_now,
)
from .registry import MinisterEntry, RegistrySnapshot
from .secretary import SecretaryValidator


MAX_REPORT_BYTES = 5_000_000
PLACEHOLDERS = {
    "{repository_root}",
    "{repository_commit}",
    "{envelope_path}",
    "{output_dir}",
}


@dataclass(frozen=True)
class AdapterSpec:
    minister_id: str
    repository_full_name: str
    repository_root: Path
    command: tuple[str, ...]
    report_relative_path: str
    timeout_seconds: int

    def render_command(
        self,
        entry: MinisterEntry,
        envelope_path: Path,
        output_dir: Path,
    ) -> list[str]:
        replacements = {
            "{repository_root}": str(self.repository_root),
            "{repository_commit}": entry.repository_commit,
            "{envelope_path}": str(envelope_path),
            "{output_dir}": str(output_dir),
        }
        rendered: list[str] = []
        for argument in self.command:
            if argument in replacements:
                rendered.append(replacements[argument])
            elif "{" in argument or "}" in argument:
                raise SanctumFederationError(
                    "Dispatch command placeholders must occupy a complete "
                    f"argument; unsupported argument: {argument}"
                )
            else:
                rendered.append(argument)
        return rendered


@dataclass(frozen=True)
class DispatchConfig:
    adapters: tuple[AdapterSpec, ...]

    @classmethod
    def load(
        cls,
        path: Path,
        contracts: ContractSet,
    ) -> "DispatchConfig":
        config_path = path.expanduser().resolve()
        value, _ = read_json(config_path, "Dispatch Config")
        contracts.validate_dispatch_config(value)
        adapters: list[AdapterSpec] = []
        for item in value["adapters"]:
            command = tuple(item["command"])
            present = {argument for argument in command if argument in PLACEHOLDERS}
            missing = sorted(PLACEHOLDERS.difference(present))
            if missing:
                raise SanctumFederationError(
                    f"Adapter {item['minister_id']} command is missing "
                    "required placeholders: "
                    + ", ".join(missing)
                )
            root = Path(item["repository_root"]).expanduser()
            if not root.is_absolute():
                root = config_path.parent / root
            adapters.append(
                AdapterSpec(
                    minister_id=item["minister_id"],
                    repository_full_name=item["repository_full_name"],
                    repository_root=root.resolve(),
                    command=command,
                    report_relative_path=item["report_relative_path"],
                    timeout_seconds=item["timeout_seconds"],
                )
            )
        minister_ids = [item.minister_id for item in adapters]
        if len(minister_ids) != len(set(minister_ids)):
            raise SanctumFederationError(
                "Dispatch Config repeats a minister_id"
            )
        return cls(tuple(adapters))

    def adapter(self, minister_id: str) -> AdapterSpec:
        matches = [
            adapter
            for adapter in self.adapters
            if adapter.minister_id == minister_id
        ]
        if len(matches) != 1:
            raise SanctumFederationError(
                f"No unique local adapter is configured for {minister_id}"
            )
        return matches[0]


class AssemblyDispatcher:
    def __init__(
        self,
        *,
        sanctum_root: Path,
        secretary_actor_id: str,
        max_workers: int = 4,
        verify_checkouts: bool = True,
    ) -> None:
        if max_workers < 1 or max_workers > 100:
            raise SanctumFederationError(
                "max_workers must be between 1 and 100"
            )
        self.sanctum_root = sanctum_root.expanduser().resolve()
        self.secretary_actor_id = secretary_actor_id
        self.max_workers = max_workers
        self.verify_checkouts = verify_checkouts

    def dispatch(
        self,
        *,
        envelope_path: Path,
        adapter_config_path: Path,
        output_dir: Path,
    ) -> Path:
        contracts = ContractSet.load(self.sanctum_root)
        envelope, envelope_raw = read_json(
            envelope_path,
            "Inquiry Envelope",
        )
        contracts.validate_envelope(envelope)
        verify_object_integrity(
            envelope,
            "envelope_sha256",
            "Inquiry Envelope",
        )
        registry = RegistrySnapshot.load(self.sanctum_root, contracts)
        sanctum_commit = registry.verify_checkout_and_envelope(
            envelope,
            verify_checkout=self.verify_checkouts,
        )
        entries = registry.selected_entries(envelope)
        config = DispatchConfig.load(adapter_config_path, contracts)
        specs: dict[str, AdapterSpec] = {}
        repository_roots: dict[str, Path] = {}
        for entry in entries:
            spec = config.adapter(entry.minister_id)
            if spec.repository_full_name != entry.repository_full_name:
                raise SanctumFederationError(
                    f"Dispatch Config repository does not match registry for "
                    f"{entry.minister_id}"
                )
            GitSnapshot(spec.repository_root).verify_clean_head(
                entry.repository_commit
            )
            specs[entry.minister_id] = spec
            repository_roots[entry.repository_full_name] = (
                spec.repository_root
            )

        secretary = SecretaryValidator(
            contracts,
            registry,
            secretary_actor_id=self.secretary_actor_id,
            repository_roots=repository_roots,
            sanctum_commit=sanctum_commit,
            verify_repository_checkouts=self.verify_checkouts,
        )
        destination = output_dir.expanduser().resolve()
        if destination.exists():
            raise FileExistsError(
                f"Dispatch output directory already exists: {destination}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(
            tempfile.mkdtemp(
                prefix=".sanctum-dispatch-",
                dir=destination.parent,
            )
        )
        execution_parent = Path(
            tempfile.mkdtemp(
                prefix=".sanctum-minister-execution-",
                dir=destination.parent,
            )
        )
        try:
            self._write_bytes_exclusive(
                temporary_root / "inquiry-envelope.json",
                envelope_raw,
            )
            worker_count = min(self.max_workers, len(entries))
            results_by_minister: dict[str, dict[str, Any]] = {}
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_map = {
                    executor.submit(
                        self._execute_one,
                        entry=entry,
                        spec=specs[entry.minister_id],
                        envelope=envelope,
                        envelope_raw=envelope_raw,
                        secretary=secretary,
                        final_root=temporary_root,
                        execution_parent=execution_parent,
                    ): entry.minister_id
                    for entry in entries
                }
                for future in as_completed(future_map):
                    minister_id = future_map[future]
                    try:
                        results_by_minister[minister_id] = future.result()
                    except Exception as exc:
                        entry = registry.entry(minister_id)
                        results_by_minister[minister_id] = (
                            self._unexpected_failure(entry, exc)
                        )

            results = [
                results_by_minister[entry.minister_id] for entry in entries
            ]
            receipt = self._receipt(
                envelope=envelope,
                registry=registry,
                sanctum_commit=sanctum_commit,
                worker_count=worker_count,
                results=results,
            )
            contracts.validate_dispatch_receipt(receipt)
            write_json_exclusive(
                temporary_root / "dispatch-receipt.json",
                receipt,
            )
            os.replace(temporary_root, destination)
        except Exception:
            shutil.rmtree(temporary_root, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(execution_parent, ignore_errors=True)
        return destination

    def _execute_one(
        self,
        *,
        entry: MinisterEntry,
        spec: AdapterSpec,
        envelope: dict[str, Any],
        envelope_raw: bytes,
        secretary: SecretaryValidator,
        final_root: Path,
        execution_parent: Path,
    ) -> dict[str, Any]:
        execution_root = Path(
            tempfile.mkdtemp(
                prefix=f"{entry.minister_id}-",
                dir=execution_parent,
            )
        )
        envelope_path = execution_root / "inquiry-envelope.json"
        adapter_output = execution_root / "adapter-output"
        self._write_bytes_exclusive(envelope_path, envelope_raw)
        command = spec.render_command(
            entry,
            envelope_path,
            adapter_output,
        )
        executable = shutil.which(command[0])
        if executable is None:
            return self._execution_failure(
                entry,
                executable_label=command[0],
                error=f"Adapter executable was not found: {command[0]}",
            )

        started = utc_now()
        try:
            completed = subprocess.run(
                command,
                cwd=execution_root,
                check=False,
                capture_output=True,
                timeout=spec.timeout_seconds,
            )
            completed_at = utc_now()
            exit_code = completed.returncode
            stdout = completed.stdout or b""
            stderr = completed.stderr or b""
        except subprocess.TimeoutExpired as exc:
            completed_at = utc_now()
            stdout = self._timeout_bytes(exc.stdout)
            stderr = self._timeout_bytes(exc.stderr)
            return self._execution_failure(
                entry,
                executable_label=Path(executable).name,
                error=(
                    f"Adapter exceeded its {spec.timeout_seconds}-second timeout"
                ),
                started_at=started,
                completed_at=completed_at,
                exit_code=-1,
                stdout=stdout,
                stderr=stderr,
            )

        adapter_record = self._adapter_record(
            started,
            completed_at,
            Path(executable).name,
            exit_code,
            stdout,
            stderr,
        )
        if exit_code != 0:
            return {
                "minister_id": entry.minister_id,
                "repository_full_name": entry.repository_full_name,
                "repository_commit": entry.repository_commit,
                "status": "EXECUTION_FAILED",
                "adapter": adapter_record,
                "error": (
                    f"Adapter exited with nonzero status {exit_code}"
                ),
            }

        report_path = (adapter_output / spec.report_relative_path).resolve()
        if not report_path.is_relative_to(adapter_output.resolve()):
            return {
                "minister_id": entry.minister_id,
                "repository_full_name": entry.repository_full_name,
                "repository_commit": entry.repository_commit,
                "status": "EXECUTION_FAILED",
                "adapter": adapter_record,
                "error": "Adapter report path escaped its isolated output directory",
            }
        if not report_path.is_file():
            return {
                "minister_id": entry.minister_id,
                "repository_full_name": entry.repository_full_name,
                "repository_commit": entry.repository_commit,
                "status": "EXECUTION_FAILED",
                "adapter": adapter_record,
                "error": (
                    "Adapter did not produce the configured Ministerial Report"
                ),
            }
        if report_path.stat().st_size > MAX_REPORT_BYTES:
            return {
                "minister_id": entry.minister_id,
                "repository_full_name": entry.repository_full_name,
                "repository_commit": entry.repository_commit,
                "status": "EXECUTION_FAILED",
                "adapter": adapter_record,
                "error": (
                    f"Ministerial Report exceeds {MAX_REPORT_BYTES} bytes"
                ),
            }

        GitSnapshot(spec.repository_root).verify_clean_head(
            entry.repository_commit
        )
        report_raw = report_path.read_bytes()
        validation = secretary.validate_report_bytes(
            envelope,
            report_raw,
            entry,
        )
        minister_root = final_root / "ministers" / entry.minister_id
        final_report = minister_root / "ministerial-report.json"
        final_validation = minister_root / "secretary-validation.json"
        self._write_bytes_exclusive(final_report, report_raw)
        write_json_exclusive(final_validation, validation.record)
        termination = validation.record["report_termination_status"]
        if validation.validated:
            status = (
                "VALIDATED"
                if termination == "COMPLETED"
                else "VALIDATED_WITH_MINISTER_LIMITATION"
            )
        else:
            status = "VALIDATION_REJECTED"
        return {
            "minister_id": entry.minister_id,
            "repository_full_name": entry.repository_full_name,
            "repository_commit": entry.repository_commit,
            "status": status,
            "adapter": adapter_record,
            "report_path": (
                f"ministers/{entry.minister_id}/ministerial-report.json"
            ),
            "validation_record_path": (
                f"ministers/{entry.minister_id}/secretary-validation.json"
            ),
            "report_file_sha256": validation.record["subject"][
                "report_file_sha256"
            ],
            "secretary_outcome": validation.record["outcome"],
            "report_termination_status": termination,
        }

    @staticmethod
    def _timeout_bytes(value: str | bytes | None) -> bytes:
        if value is None:
            return b""
        if isinstance(value, bytes):
            return value
        return value.encode("utf-8", errors="replace")

    @staticmethod
    def _adapter_record(
        started_at: Any,
        completed_at: Any,
        executable: str,
        exit_code: int,
        stdout: bytes,
        stderr: bytes,
    ) -> dict[str, Any]:
        return {
            "started_at": iso8601(started_at),
            "completed_at": iso8601(completed_at),
            "executable": executable[:1000],
            "exit_code": exit_code,
            "stdout_bytes": len(stdout),
            "stderr_bytes": len(stderr),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        }

    def _execution_failure(
        self,
        entry: MinisterEntry,
        *,
        executable_label: str,
        error: str,
        started_at: Any | None = None,
        completed_at: Any | None = None,
        exit_code: int = -1,
        stdout: bytes = b"",
        stderr: bytes = b"",
    ) -> dict[str, Any]:
        started = started_at or utc_now()
        completed = completed_at or utc_now()
        return {
            "minister_id": entry.minister_id,
            "repository_full_name": entry.repository_full_name,
            "repository_commit": entry.repository_commit,
            "status": "EXECUTION_FAILED",
            "adapter": self._adapter_record(
                started,
                completed,
                executable_label,
                exit_code,
                stdout,
                stderr,
            ),
            "error": error[:10000],
        }

    def _unexpected_failure(
        self,
        entry: MinisterEntry,
        error: Exception,
    ) -> dict[str, Any]:
        return self._execution_failure(
            entry,
            executable_label="UNKNOWN",
            error=(
                f"Unexpected dispatcher failure: {type(error).__name__}: "
                f"{str(error).strip() or 'no detail'}"
            ),
        )

    def _receipt(
        self,
        *,
        envelope: dict[str, Any],
        registry: RegistrySnapshot,
        sanctum_commit: str,
        worker_count: int,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        statuses = {item["status"] for item in results}
        if "EXECUTION_FAILED" in statuses:
            overall = "DISPATCH_FAILED"
        elif "VALIDATION_REJECTED" in statuses:
            overall = "REJECTED_REPORTS"
        elif "VALIDATED_WITH_MINISTER_LIMITATION" in statuses:
            overall = "COMPLETED_WITH_MINISTER_LIMITATIONS"
        else:
            overall = "COMPLETED_VALIDATED"
        receipt: dict[str, Any] = {
            "contract_version": "1.0.0",
            "dispatch_id": (
                f"DSP-{envelope['envelope_id']}-"
                f"{envelope['integrity']['envelope_sha256'][:12]}"
            ),
            "created_at": iso8601(utc_now()),
            "inquiry": {
                "envelope_id": envelope["envelope_id"],
                "envelope_sha256": envelope["integrity"][
                    "envelope_sha256"
                ],
            },
            "registry_snapshot": registry.receipt_snapshot(sanctum_commit),
            "execution_policy": {
                "same_envelope_for_all": True,
                "isolated_context_required": True,
                "parallel_execution": "PREFERRED_WHERE_AVAILABLE",
                "max_workers": worker_count,
            },
            "status": overall,
            "minister_results": results,
        }
        receipt["integrity"] = {
            "hash_algorithm": "SHA-256",
            "canonicalization": "RFC8785",
            "receipt_sha256": object_sha256_without_integrity(receipt),
        }
        return receipt

    @staticmethod
    def _write_bytes_exclusive(path: Path, raw: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(raw)
