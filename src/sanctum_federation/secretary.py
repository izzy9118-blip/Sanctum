from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .contracts import ContractSet
from .errors import SanctumFederationError
from .git_snapshot import GitSnapshot
from .integrity import (
    iso8601,
    object_sha256_without_integrity,
    parse_datetime,
    parse_json_bytes,
    raw_sha256,
    schema_errors,
    text_sha256,
    utc_now,
    verify_object_integrity,
)
from .registry import MinisterEntry, RegistrySnapshot


LINE_LOCATOR = re.compile(
    r"; lines ([1-9][0-9]*)-([1-9][0-9]*) "
    r"\(1-based, inclusive\)$"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ValidationResult:
    report: dict[str, Any] | None
    record: dict[str, Any]

    @property
    def validated(self) -> bool:
        return self.record["outcome"] == "VALIDATED"


class SecretaryValidator:
    """Validate Assembly provenance without judging ministerial substance."""

    CHECK_IDS = (
        "REPORT_JSON",
        "REPORT_SCHEMA",
        "REPORT_INTEGRITY",
        "ENVELOPE_INTEGRITY",
        "ENVELOPE_BINDING",
        "REGISTRY_BINDING",
        "MINISTER_REGISTRY_BINDING",
        "GOVERNING_MANIFEST_FIXITY",
        "EXECUTION_CHRONOLOGY",
        "REFERENCE_INTEGRITY",
        "EVIDENCE_GIT_FIXITY",
        "TERMINATION_CONSISTENCY",
        "CONSTITUTIONAL_BOUNDARY",
    )

    def __init__(
        self,
        contracts: ContractSet,
        registry: RegistrySnapshot,
        *,
        secretary_actor_id: str,
        repository_roots: dict[str, Path],
        sanctum_commit: str,
        verify_repository_checkouts: bool = True,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if not secretary_actor_id.strip():
            raise SanctumFederationError(
                "Secretary actor identifier must not be empty"
            )
        self.contracts = contracts
        self.registry = registry
        self.secretary_actor_id = secretary_actor_id
        self.repository_roots = {
            name: path.expanduser().resolve()
            for name, path in repository_roots.items()
        }
        self.sanctum_commit = sanctum_commit
        self.verify_repository_checkouts = verify_repository_checkouts
        self.clock = clock
        self._git_cache: dict[str, GitSnapshot] = {}
        self._git_cache_lock = threading.Lock()

    def validate_report_bytes(
        self,
        envelope: dict[str, Any],
        report_raw: bytes,
        entry: MinisterEntry,
    ) -> ValidationResult:
        checks: list[dict[str, Any]] = []
        report: dict[str, Any] | None
        try:
            report = parse_json_bytes(report_raw, "Ministerial Report")
        except SanctumFederationError as exc:
            report = None
            checks.append(self._check("REPORT_JSON", "FAIL", str(exc)))
            for check_id in self.CHECK_IDS[1:]:
                checks.append(
                    self._check(
                        check_id,
                        "SKIPPED",
                        "The submitted report was not a parseable JSON object.",
                    )
                )
            return ValidationResult(
                report=None,
                record=self._record(
                    envelope,
                    report_raw,
                    report,
                    entry,
                    checks,
                ),
            )

        checks.append(
            self._check(
                "REPORT_JSON",
                "PASS",
                "The submitted report is a unique-key UTF-8 JSON object.",
            )
        )
        self._run_check(
            checks,
            "REPORT_SCHEMA",
            lambda: self._assert_report_schema(report),
            "The report conforms to the Ministerial Report v1.0 schema.",
        )
        self._run_check(
            checks,
            "REPORT_INTEGRITY",
            lambda: verify_object_integrity(
                report,
                "report_sha256",
                "Ministerial Report",
            ),
            "The declared report SHA-256 matches its canonical content.",
        )
        self._run_check(
            checks,
            "ENVELOPE_INTEGRITY",
            lambda: self._assert_envelope_integrity(envelope),
            "The Inquiry Envelope schema and self-hash are valid.",
        )
        self._run_check(
            checks,
            "ENVELOPE_BINDING",
            lambda: self._assert_envelope_binding(envelope, report),
            "The report is bound to the exact envelope and question.",
        )
        self._run_check(
            checks,
            "REGISTRY_BINDING",
            lambda: self._assert_registry_binding(envelope),
            "The envelope names the exact pinned Sanctum registry snapshot.",
        )
        self._run_check(
            checks,
            "MINISTER_REGISTRY_BINDING",
            lambda: self._assert_minister_binding(envelope, report, entry),
            "Minister identity, manifest, repository, release, and adapter match the registry.",
        )
        self._run_check(
            checks,
            "GOVERNING_MANIFEST_FIXITY",
            lambda: self._assert_governing_manifest(report, entry),
            "The governing manifest bytes and Git blob match the registry.",
        )
        self._run_check(
            checks,
            "EXECUTION_CHRONOLOGY",
            lambda: self._assert_chronology(envelope, report),
            "Envelope issue, execution, completion, and report times are ordered.",
        )
        self._run_check(
            checks,
            "REFERENCE_INTEGRITY",
            lambda: self._assert_references(report),
            "All evidence, uncertainty, dissent, and finding references resolve uniquely.",
        )
        self._run_check(
            checks,
            "EVIDENCE_GIT_FIXITY",
            lambda: self._assert_evidence_fixity(report, entry),
            "Every evidence excerpt was independently re-read and hashed from reachable Git.",
        )
        self._run_check(
            checks,
            "TERMINATION_CONSISTENCY",
            lambda: self._assert_termination(report),
            "The termination state is consistent with the report contents.",
        )
        self._run_check(
            checks,
            "CONSTITUTIONAL_BOUNDARY",
            lambda: self._assert_constitutional_boundary(report),
            "The minister submitted a candidate report and conferred no validation or certification.",
        )
        return ValidationResult(
            report=report,
            record=self._record(
                envelope,
                report_raw,
                report,
                entry,
                checks,
            ),
        )

    @staticmethod
    def _check(check_id: str, status: str, detail: str) -> dict[str, Any]:
        return {
            "check_id": check_id,
            "status": status,
            "required": True,
            "detail": detail[:10000] or "No detail was supplied.",
        }

    def _run_check(
        self,
        checks: list[dict[str, Any]],
        check_id: str,
        action: Callable[[], None],
        success: str,
    ) -> None:
        try:
            action()
        except Exception as exc:
            detail = str(exc).strip() or type(exc).__name__
            checks.append(self._check(check_id, "FAIL", detail))
        else:
            checks.append(self._check(check_id, "PASS", success))

    def _assert_report_schema(self, report: dict[str, Any]) -> None:
        errors = schema_errors(report, self.contracts.ministerial_report)
        if errors:
            raise SanctumFederationError(
                "Ministerial Report schema failure: " + "; ".join(errors[:5])
            )

    def _assert_envelope_integrity(self, envelope: dict[str, Any]) -> None:
        self.contracts.validate_envelope(envelope)
        verify_object_integrity(
            envelope,
            "envelope_sha256",
            "Inquiry Envelope",
        )

    @staticmethod
    def _assert_envelope_binding(
        envelope: dict[str, Any],
        report: dict[str, Any],
    ) -> None:
        inquiry = report["inquiry"]
        expected = {
            "envelope_id": envelope["envelope_id"],
            "envelope_version": envelope["envelope_version"],
            "envelope_sha256": envelope["integrity"]["envelope_sha256"],
            "question_sha256": text_sha256(envelope["question"]["text"]),
        }
        mismatches = [
            key for key, value in expected.items() if inquiry.get(key) != value
        ]
        if mismatches:
            raise SanctumFederationError(
                "Report does not match the Inquiry Envelope: "
                + ", ".join(mismatches)
            )

    def _assert_registry_binding(self, envelope: dict[str, Any]) -> None:
        snapshot = envelope["routing"]["registry_snapshot"]
        expected = self.registry.receipt_snapshot(self.sanctum_commit)
        mismatches = [
            key for key, value in expected.items() if snapshot.get(key) != value
        ]
        if mismatches:
            raise SanctumFederationError(
                "Registry snapshot mismatch: " + ", ".join(mismatches)
            )

    def _repository_git(self, entry: MinisterEntry) -> GitSnapshot:
        with self._git_cache_lock:
            cached = self._git_cache.get(entry.repository_full_name)
            if cached is not None:
                return cached
            root = self.repository_roots.get(entry.repository_full_name)
            if root is None:
                raise SanctumFederationError(
                    "No verified local checkout is configured for "
                    f"{entry.repository_full_name}"
                )
            git = GitSnapshot(root)
            if self.verify_repository_checkouts:
                git.verify_clean_head(entry.repository_commit)
            else:
                git.resolve_commit(entry.repository_commit)
            self._git_cache[entry.repository_full_name] = git
            return git

    def _assert_minister_binding(
        self,
        envelope: dict[str, Any],
        report: dict[str, Any],
        entry: MinisterEntry,
    ) -> None:
        manifest = entry.value
        selection = [
            item
            for item in envelope["routing"]["selected_ministers"]
            if item["minister_id"] == entry.minister_id
        ]
        if len(selection) != 1:
            raise SanctumFederationError(
                "The validated minister is not selected exactly once"
            )
        selected = selection[0]
        expected_selection = {
            "minister_id": entry.minister_id,
            "manifest_id": entry.manifest_id,
            "manifest_version": manifest["manifest_version"],
            "repository_full_name": entry.repository_full_name,
            "repository_commit": entry.repository_commit,
        }
        expected_minister = {
            "minister_id": entry.minister_id,
            "manifest_id": entry.manifest_id,
            "manifest_version": manifest["manifest_version"],
            "name": manifest["minister"]["name"],
            "office": manifest["minister"]["office"],
        }
        expected_repository = {
            "full_name": entry.repository_full_name,
            "git_commit": entry.repository_commit,
            "canonical_authority": "GIT",
        }
        mismatches: list[str] = []
        for label, actual, expected in (
            ("selection", selected, expected_selection),
            ("minister", report["minister"], expected_minister),
            ("repository", report["repository"], expected_repository),
        ):
            mismatches.extend(
                f"{label}.{key}"
                for key, value in expected.items()
                if actual.get(key) != value
            )
        if mismatches:
            raise SanctumFederationError(
                "Ministerial identity or release mismatch: "
                + ", ".join(mismatches)
            )

        git = self._repository_git(entry)
        adapter = manifest["federation"]["adapter"]
        adapter_bytes = git.read_bytes(
            entry.repository_commit,
            adapter["path"],
        )
        if raw_sha256(adapter_bytes) != adapter["sha256"]:
            raise SanctumFederationError(
                "Registered adapter manifest failed Git fixity"
            )
        for authority in manifest["authority_records"]:
            authority_bytes = git.read_bytes(
                entry.repository_commit,
                authority["path"],
            )
            if raw_sha256(authority_bytes) != authority["sha256"]:
                raise SanctumFederationError(
                    f"Authority record failed SHA-256 fixity: "
                    f"{authority['record_id']}"
                )
            blob_sha = git.blob_sha(
                entry.repository_commit,
                authority["path"],
            )
            if blob_sha != authority["git_blob_sha"]:
                raise SanctumFederationError(
                    f"Authority record Git blob does not match registry: "
                    f"{authority['record_id']}"
                )

    def _assert_governing_manifest(
        self,
        report: dict[str, Any],
        entry: MinisterEntry,
    ) -> None:
        expected_source = entry.value["governing_manifest"]
        expected = {
            "id": expected_source["id"],
            "version": expected_source["version"],
            "path": expected_source["path"],
            "sha256": expected_source["sha256"],
            "git_blob_sha": expected_source["git_blob_sha"],
        }
        if "declared_repository_commit" in expected_source:
            expected["declared_repository_commit"] = expected_source[
                "declared_repository_commit"
            ]
        actual = report["governing_manifest"]
        mismatches = [
            key for key, value in expected.items() if actual.get(key) != value
        ]
        if mismatches:
            raise SanctumFederationError(
                "Report governing manifest does not match registry: "
                + ", ".join(mismatches)
            )

        git = self._repository_git(entry)
        manifest_bytes = git.read_bytes(
            entry.repository_commit,
            expected_source["path"],
        )
        if raw_sha256(manifest_bytes) != expected_source["sha256"]:
            raise SanctumFederationError(
                "Governing manifest content failed SHA-256 fixity"
            )
        blob_sha = git.blob_sha(
            entry.repository_commit,
            expected_source["path"],
        )
        if blob_sha != expected_source["git_blob_sha"]:
            raise SanctumFederationError(
                "Governing manifest Git blob does not match registry"
            )

    @staticmethod
    def _assert_chronology(
        envelope: dict[str, Any],
        report: dict[str, Any],
    ) -> None:
        issued = parse_datetime(envelope["created_at"], "Envelope created_at")
        started = parse_datetime(
            report["execution"]["started_at"],
            "Execution started_at",
        )
        completed = parse_datetime(
            report["execution"]["completed_at"],
            "Execution completed_at",
        )
        created = parse_datetime(report["created_at"], "Report created_at")
        if not issued <= started <= completed <= created:
            raise SanctumFederationError(
                "Required chronology is envelope <= start <= completion <= report"
            )

    @staticmethod
    def _unique_ids(
        values: list[dict[str, Any]],
        field: str,
        label: str,
    ) -> set[str]:
        identifiers = [item[field] for item in values]
        if len(identifiers) != len(set(identifiers)):
            raise SanctumFederationError(f"{label} identifiers are not unique")
        return set(identifiers)

    @classmethod
    def _assert_references(cls, report: dict[str, Any]) -> None:
        evidence_ids = cls._unique_ids(
            report["evidence"], "evidence_id", "Evidence"
        )
        finding_ids = cls._unique_ids(
            report["findings"], "finding_id", "Finding"
        )
        uncertainty_ids = cls._unique_ids(
            report["uncertainties"], "uncertainty_id", "Uncertainty"
        )
        dissent_ids = cls._unique_ids(
            report["dissent"], "dissent_id", "Dissent"
        )
        for finding in report["findings"]:
            cls._assert_subset(
                finding["evidence_refs"],
                evidence_ids,
                f"Finding {finding['finding_id']} evidence",
            )
            cls._assert_subset(
                finding["uncertainty_refs"],
                uncertainty_ids,
                f"Finding {finding['finding_id']} uncertainty",
            )
            cls._assert_subset(
                finding["dissent_refs"],
                dissent_ids,
                f"Finding {finding['finding_id']} dissent",
            )
        for uncertainty in report["uncertainties"]:
            cls._assert_subset(
                uncertainty["evidence_refs"],
                evidence_ids,
                f"Uncertainty {uncertainty['uncertainty_id']} evidence",
            )
        for dissent in report["dissent"]:
            cls._assert_subset(
                dissent["evidence_refs"],
                evidence_ids,
                f"Dissent {dissent['dissent_id']} evidence",
            )
            cls._assert_subset(
                dissent["related_finding_refs"],
                finding_ids,
                f"Dissent {dissent['dissent_id']} finding",
            )

    @staticmethod
    def _assert_subset(
        references: list[str],
        available: set[str],
        label: str,
    ) -> None:
        missing = sorted(set(references).difference(available))
        if missing:
            raise SanctumFederationError(
                f"{label} references do not resolve: {', '.join(missing)}"
            )

    def _assert_evidence_fixity(
        self,
        report: dict[str, Any],
        entry: MinisterEntry,
    ) -> None:
        git = self._repository_git(entry)
        release = entry.repository_commit
        for evidence in report["evidence"]:
            evidence_id = evidence["evidence_id"]
            if evidence["repository_full_name"] != entry.repository_full_name:
                raise SanctumFederationError(
                    f"{evidence_id} is outside the registered minister repository"
                )
            commit = evidence["git_commit"]
            if not git.is_ancestor(commit, release):
                raise SanctumFederationError(
                    f"{evidence_id} commit is not reachable from the minister release"
                )
            match = LINE_LOCATOR.search(evidence["locator"])
            if match is None:
                raise SanctumFederationError(
                    f"{evidence_id} has no verifiable 1-based line locator"
                )
            start, end = (int(match.group(1)), int(match.group(2)))
            if end < start:
                raise SanctumFederationError(
                    f"{evidence_id} has a reversed line range"
                )
            source = git.read_text(commit, evidence["path"])
            lines = source.splitlines(keepends=True)
            if end > len(lines):
                raise SanctumFederationError(
                    f"{evidence_id} line range exceeds the Git source"
                )
            excerpt = "".join(lines[start - 1 : end]).encode("utf-8")
            digest = raw_sha256(excerpt)
            if digest != evidence["sha256"]:
                raise SanctumFederationError(
                    f"{evidence_id} failed Git excerpt fixity"
                )
            if evidence.get("verified") is not True:
                raise SanctumFederationError(
                    f"{evidence_id} is not marked verified by the minister"
                )

    @staticmethod
    def _assert_termination(report: dict[str, Any]) -> None:
        status = report["termination"]["status"]
        evidence = report["evidence"]
        findings = report["findings"]
        uncertainties = report["uncertainties"]
        if status in {"COMPLETED", "COMPLETED_WITH_LIMITATIONS"}:
            if not evidence or not findings:
                raise SanctumFederationError(
                    "A completed report requires evidence and findings"
                )
        if status == "COMPLETED_WITH_LIMITATIONS" and not uncertainties:
            raise SanctumFederationError(
                "A limited completion requires a preserved uncertainty"
            )
        if status == "FAILED" and not report["termination"].get("error_code"):
            raise SanctumFederationError(
                "A failed report requires an error_code"
            )

    @staticmethod
    def _assert_constitutional_boundary(report: dict[str, Any]) -> None:
        if report["report_status"] != "SUBMITTED":
            raise SanctumFederationError(
                "Ministerial Report must remain SUBMITTED"
            )
        if report["secretary_validation_status"] != "NOT_YET_VALIDATED":
            raise SanctumFederationError(
                "A minister cannot validate its own report"
            )
        forbidden = {
            "certification",
            "certification_status",
            "secretary_validation_record",
        }
        present = sorted(forbidden.intersection(report))
        if present:
            raise SanctumFederationError(
                "Ministerial Report attempts to confer Assembly authority: "
                + ", ".join(present)
            )

    def _record(
        self,
        envelope: dict[str, Any],
        report_raw: bytes,
        report: dict[str, Any] | None,
        entry: MinisterEntry,
        checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        raw_digest = raw_sha256(report_raw)
        declared_digest: str | None = None
        report_id = f"UNPARSEABLE-{raw_digest[:24]}"
        termination_status = "UNKNOWN"
        if report is not None:
            if isinstance(report.get("report_id"), str) and report["report_id"]:
                report_id = report["report_id"][:240]
            candidate = (
                report.get("integrity", {}).get("report_sha256")
                if isinstance(report.get("integrity"), dict)
                else None
            )
            if isinstance(candidate, str) and SHA256_PATTERN.fullmatch(candidate):
                declared_digest = candidate
            candidate_status = (
                report.get("termination", {}).get("status")
                if isinstance(report.get("termination"), dict)
                else None
            )
            if candidate_status in {
                "COMPLETED",
                "COMPLETED_WITH_LIMITATIONS",
                "INSUFFICIENT_EVIDENCE",
                "OUT_OF_JURISDICTION",
                "FAILED",
            }:
                termination_status = candidate_status

        outcome = (
            "VALIDATED"
            if all(check["status"] == "PASS" for check in checks)
            else "REJECTED"
        )
        identity_seed = (
            f"{envelope['integrity']['envelope_sha256']}:{raw_digest}:"
            f"{entry.minister_id}:{self.registry.sha256}"
        )
        record_id_suffix = hashlib.sha256(
            identity_seed.encode("utf-8")
        ).hexdigest()[:24].upper()
        subject: dict[str, Any] = {
            "report_id": report_id,
            "report_file_sha256": raw_digest,
            "minister_id": entry.minister_id,
            "repository_full_name": entry.repository_full_name,
        }
        if declared_digest is not None:
            subject["declared_report_sha256"] = declared_digest

        record: dict[str, Any] = {
            "contract_version": "1.0.0",
            "validation_id": (
                f"SVR-{envelope['envelope_id']}-"
                f"{entry.minister_id}-{record_id_suffix}"
            ),
            "validation_version": "1.0.0",
            "record_status": "RECORDED",
            "created_at": iso8601(self.clock()),
            "secretary": {
                "office": "SECRETARY",
                "actor_id": self.secretary_actor_id,
            },
            "inquiry": {
                "envelope_id": envelope["envelope_id"],
                "envelope_sha256": envelope["integrity"]["envelope_sha256"],
            },
            "subject": subject,
            "registry_snapshot": self.registry.receipt_snapshot(
                self.sanctum_commit
            ),
            "outcome": outcome,
            "preservation_status": (
                "ELIGIBLE_FOR_ASSEMBLY_RECORD"
                if outcome == "VALIDATED"
                else "QUARANTINED_REJECTED_REPORT"
            ),
            "checks": checks,
            "report_termination_status": termination_status,
            "constitutional_effect": "PROVENANCE_VALIDATION_ONLY",
            "certification_status": "NOT_CERTIFIED",
        }
        record["integrity"] = {
            "hash_algorithm": "SHA-256",
            "canonicalization": "RFC8785",
            "record_sha256": object_sha256_without_integrity(record),
        }
        self.contracts.validate_secretary_record(record)
        return record
