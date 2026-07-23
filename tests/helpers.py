from __future__ import annotations

import json
import os
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from sanctum_federation.integrity import (
    iso8601,
    object_sha256_without_integrity,
    utc_now,
)
from sanctum_federation.registry import RegistrySnapshot


SANCTUM_ROOT = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def custos_root() -> Path:
    configured = os.environ.get("CUSTOS_REPO_ROOT")
    root = (
        Path(configured).expanduser().resolve()
        if configured
        else SANCTUM_ROOT.parent / "custos-release"
    )
    if not (root / ".git").exists():
        pytest.skip("A released Custos checkout is not available")
    return root


def envelope(
    registry: RegistrySnapshot,
    *,
    created_at: Any | None = None,
) -> dict[str, Any]:
    entry = registry.entries[0]
    manifest = entry.value
    issued = created_at or (utc_now() - timedelta(minutes=2))
    value: dict[str, Any] = {
        "contract_version": "1.0.0",
        "envelope_id": "INQ-000000001",
        "envelope_version": "1.0.0",
        "status": "ISSUED",
        "created_at": iso8601(issued),
        "created_by": {
            "office": "PRESIDENT",
            "actor_id": "SANCTUM-PRESIDENT",
        },
        "question": {
            "text": "What does this bounded documentary evidence support?",
            "purpose": "Exercise the Sanctum dispatcher and Secretary.",
            "context": "A strict federation fixture.",
            "requested_deliverable": (
                "A source-bounded Ministerial Report."
            ),
        },
        "scope": {
            "documentary_boundary": (
                "Only the declared line range in the content-addressed "
                "evidence bundle."
            ),
            "included_topics": ["Political philosophy"],
            "excluded_topics": ["Unfixed evidence"],
            "constraints": ["Preserve epistemic classifications"],
            "preserve_uncertainty": True,
        },
        "routing": {
            "registry_snapshot": registry.receipt_snapshot(
                git(registry.repository_root, "rev-parse", "HEAD")
            ),
            "selected_ministers": [
                {
                    "minister_id": entry.minister_id,
                    "manifest_id": entry.manifest_id,
                    "manifest_version": manifest["manifest_version"],
                    "repository_full_name": entry.repository_full_name,
                    "repository_commit": entry.repository_commit,
                    "selection_reason": (
                        "The bounded inquiry concerns political philosophy."
                    ),
                }
            ],
        },
        "dispatch_policy": {
            "same_envelope_for_all": True,
            "isolated_context_required": True,
            "parallel_execution": "PREFERRED_WHERE_AVAILABLE",
        },
        "report_contract": {
            "schema_id": (
                "urn:sanctum:federation:ministerial-report:1.0.0"
            ),
            "contract_version": "1.0.0",
        },
    }
    value["integrity"] = {
        "hash_algorithm": "SHA-256",
        "canonicalization": "RFC8785",
        "envelope_sha256": object_sha256_without_integrity(value),
    }
    return value


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(json_bytes(value))
