from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

from .contracts import ContractSet
from .errors import SanctumFederationError
from .git_snapshot import GitSnapshot
from .integrity import parse_datetime, raw_sha256


REGISTRY_PATH = "registry/ministers.yaml"
REGISTRY_REPOSITORY = "izzy9118-blip/Sanctum"
ENTRY_SCHEMA_ID = "urn:sanctum:federation:minister-manifest:1.0.0"


@dataclass(frozen=True)
class MinisterEntry:
    value: dict[str, Any]

    @property
    def minister_id(self) -> str:
        return self.value["minister"]["minister_id"]

    @property
    def manifest_id(self) -> str:
        return self.value["manifest_id"]

    @property
    def repository_full_name(self) -> str:
        return self.value["repository"]["full_name"]

    @property
    def repository_commit(self) -> str:
        return self.value["repository"]["pinned_commit"]

    @property
    def routing_status(self) -> str:
        return self.value["federation"]["routing_status"]


@dataclass(frozen=True)
class RegistrySnapshot:
    repository_root: Path
    raw: bytes
    value: dict[str, Any]
    entries: tuple[MinisterEntry, ...]

    @classmethod
    def load(
        cls,
        repository_root: Path,
        contracts: ContractSet,
    ) -> "RegistrySnapshot":
        root = repository_root.expanduser().resolve()
        path = root / REGISTRY_PATH
        if not path.is_file():
            raise SanctumFederationError(
                f"Minister registry does not exist: {path}"
            )
        raw = path.read_bytes()
        try:
            value = yaml.safe_load(raw.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise SanctumFederationError(
                "Minister registry is not valid UTF-8 YAML"
            ) from exc
        if not isinstance(value, dict):
            raise SanctumFederationError(
                "Minister registry must be a YAML mapping"
            )

        required = {
            "registry_id",
            "registry_version",
            "contract_version",
            "entry_schema",
            "canonical_repository",
            "canonical_path",
            "updated_at",
            "routing_policy",
            "ministers",
        }
        missing = sorted(required.difference(value))
        unknown = sorted(set(value).difference(required))
        if missing:
            raise SanctumFederationError(
                f"Minister registry is missing fields: {', '.join(missing)}"
            )
        if unknown:
            raise SanctumFederationError(
                f"Minister registry has unknown fields: {', '.join(unknown)}"
            )
        if value["contract_version"] != "1.0.0":
            raise SanctumFederationError(
                "Minister registry contract_version is unsupported"
            )
        if value["entry_schema"] != ENTRY_SCHEMA_ID:
            raise SanctumFederationError(
                "Minister registry entry_schema is not the canonical contract"
            )
        if value["canonical_repository"] != REGISTRY_REPOSITORY:
            raise SanctumFederationError(
                "Minister registry canonical_repository is incorrect"
            )
        if value["canonical_path"] != REGISTRY_PATH:
            raise SanctumFederationError(
                "Minister registry canonical_path is incorrect"
            )
        if not re.fullmatch(
            r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)",
            str(value["registry_version"]),
        ):
            raise SanctumFederationError(
                "Minister registry registry_version is not semantic"
            )
        if not re.fullmatch(
            r"REG-[A-Z0-9][A-Z0-9._-]{2,127}",
            str(value["registry_id"]),
        ):
            raise SanctumFederationError(
                "Minister registry registry_id is invalid"
            )
        parse_datetime(value["updated_at"], "Minister registry updated_at")

        routing_policy = value["routing_policy"]
        if not isinstance(routing_policy, dict):
            raise SanctumFederationError(
                "Minister registry routing_policy must be a mapping"
            )
        if set(routing_policy) != {"selectable_statuses", "on_unknown_status"}:
            raise SanctumFederationError(
                "Minister registry routing_policy fields are not recognized"
            )
        statuses = routing_policy["selectable_statuses"]
        if (
            not isinstance(statuses, list)
            or not statuses
            or not all(isinstance(item, str) for item in statuses)
            or len(statuses) != len(set(statuses))
        ):
            raise SanctumFederationError(
                "selectable_statuses must be a non-empty unique string list"
            )
        if statuses != ["AVAILABLE"]:
            raise SanctumFederationError(
                "Federation v1 may route only entries explicitly marked AVAILABLE"
            )
        if routing_policy["on_unknown_status"] != "REJECT":
            raise SanctumFederationError(
                "Unknown minister routing statuses must be rejected"
            )

        raw_entries = value["ministers"]
        if not isinstance(raw_entries, list) or not raw_entries:
            raise SanctumFederationError(
                "Minister registry must contain at least one entry"
            )
        entries: list[MinisterEntry] = []
        for item in raw_entries:
            if not isinstance(item, dict):
                raise SanctumFederationError(
                    "Every minister registry entry must be a mapping"
                )
            contracts.validate_manifest(item)
            entries.append(MinisterEntry(item))

        cls._assert_unique(entries, "minister_id")
        cls._assert_unique(entries, "manifest_id")
        cls._assert_unique(entries, "repository_full_name")
        return cls(
            repository_root=root,
            raw=raw,
            value=value,
            entries=tuple(entries),
        )

    @staticmethod
    def _assert_unique(entries: list[MinisterEntry], attribute: str) -> None:
        values = [getattr(entry, attribute) for entry in entries]
        if len(values) != len(set(values)):
            raise SanctumFederationError(
                f"Minister registry repeats {attribute}"
            )

    @property
    def sha256(self) -> str:
        return raw_sha256(self.raw)

    @property
    def version(self) -> str:
        return self.value["registry_version"]

    def entry(self, minister_id: str) -> MinisterEntry:
        matches = [
            entry for entry in self.entries if entry.minister_id == minister_id
        ]
        if len(matches) != 1:
            raise SanctumFederationError(
                f"Minister is not uniquely registered: {minister_id}"
            )
        return matches[0]

    def verify_checkout_and_envelope(
        self,
        envelope: dict[str, Any],
        *,
        verify_checkout: bool = True,
    ) -> str:
        snapshot = envelope["routing"]["registry_snapshot"]
        expected = {
            "repository_full_name": REGISTRY_REPOSITORY,
            "path": REGISTRY_PATH,
            "sha256": self.sha256,
            "registry_version": self.version,
        }
        mismatches = [
            key for key, value in expected.items() if snapshot.get(key) != value
        ]
        if mismatches:
            raise SanctumFederationError(
                "Inquiry Envelope registry snapshot does not match canonical "
                "registry: "
                + ", ".join(mismatches)
            )
        commit = snapshot["git_commit"]
        git = GitSnapshot(self.repository_root)
        resolved = (
            git.verify_clean_head(commit)
            if verify_checkout
            else git.resolve_commit(commit)
        )
        registry_at_commit = git.read_bytes(resolved, REGISTRY_PATH)
        if raw_sha256(registry_at_commit) != self.sha256:
            raise SanctumFederationError(
                "Working registry bytes do not match the pinned Sanctum commit"
            )
        for entry in self.entries:
            authority = entry.value["registration"]["authority"]
            if authority["repository_full_name"] != REGISTRY_REPOSITORY:
                raise SanctumFederationError(
                    f"Registration authority is outside Sanctum: "
                    f"{entry.minister_id}"
                )
            if not git.is_ancestor(authority["git_commit"], resolved):
                raise SanctumFederationError(
                    f"Registration authority is not reachable from the "
                    f"pinned registry commit: {entry.minister_id}"
                )
            blob_sha = git.blob_sha(
                authority["git_commit"],
                authority["path"],
            )
            if blob_sha != authority["git_blob_sha"]:
                raise SanctumFederationError(
                    f"Registration authority Git blob does not match: "
                    f"{entry.minister_id}"
                )
        return resolved

    def selected_entries(
        self,
        envelope: dict[str, Any],
    ) -> tuple[MinisterEntry, ...]:
        selections = envelope["routing"]["selected_ministers"]
        minister_ids = [item["minister_id"] for item in selections]
        if len(minister_ids) != len(set(minister_ids)):
            raise SanctumFederationError(
                "Inquiry Envelope selects a minister more than once"
            )

        selected: list[MinisterEntry] = []
        selectable = set(
            self.value["routing_policy"]["selectable_statuses"]
        )
        for selection in selections:
            entry = self.entry(selection["minister_id"])
            manifest = entry.value
            expected = {
                "minister_id": entry.minister_id,
                "manifest_id": entry.manifest_id,
                "manifest_version": manifest["manifest_version"],
                "repository_full_name": entry.repository_full_name,
                "repository_commit": entry.repository_commit,
            }
            mismatches = [
                key
                for key, value in expected.items()
                if selection.get(key) != value
            ]
            if mismatches:
                raise SanctumFederationError(
                    f"Selected minister {entry.minister_id} does not match "
                    "the pinned registry entry: "
                    + ", ".join(mismatches)
                )
            federation = manifest["federation"]
            adapter = federation["adapter"]
            if manifest["registration"]["membership_status"] != "ESTABLISHED":
                raise SanctumFederationError(
                    f"Ministerial membership is not established: "
                    f"{entry.minister_id}"
                )
            if manifest["governing_manifest"]["release_status"] not in {
                "RELEASED",
                "CERTIFIED",
                "ADMITTED",
            }:
                raise SanctumFederationError(
                    f"Minister governing manifest is not released: "
                    f"{entry.minister_id}"
                )
            if entry.routing_status not in selectable:
                raise SanctumFederationError(
                    f"Minister is not routable: {entry.minister_id} "
                    f"({entry.routing_status})"
                )
            if adapter["status"] != "AVAILABLE":
                raise SanctumFederationError(
                    f"Minister adapter is not available: {entry.minister_id}"
                )
            if (
                federation["accepts_schema"]
                != "urn:sanctum:federation:inquiry-envelope:1.0.0"
            ):
                raise SanctumFederationError(
                    f"Minister accepts the wrong envelope schema: {entry.minister_id}"
                )
            if (
                federation["produces_schema"]
                != envelope["report_contract"]["schema_id"]
            ):
                raise SanctumFederationError(
                    f"Minister produces the wrong report schema: {entry.minister_id}"
                )
            selected.append(entry)
        return tuple(selected)

    def receipt_snapshot(self, sanctum_commit: str) -> dict[str, Any]:
        return {
            "repository_full_name": REGISTRY_REPOSITORY,
            "git_commit": sanctum_commit,
            "path": REGISTRY_PATH,
            "sha256": self.sha256,
            "registry_version": self.version,
        }
