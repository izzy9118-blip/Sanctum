#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXCLUDED = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(source: Path, *args: str, default: str = "") -> str:
    try:
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return default


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, default=Path.cwd())
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--capsule-id", default="CAP-000000001")
    a = p.parse_args()
    source, output = a.source.resolve(), a.output.resolve()
    if source == output:
        raise SystemExit("source and output must differ")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    records = []
    for src in sorted(source.rglob("*")):
        if not src.is_file() or any(part in EXCLUDED for part in src.parts):
            continue
        try:
            src.resolve().relative_to(output)
            continue
        except ValueError:
            pass
        rel = src.relative_to(source)
        dst = output / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        first = rel.parts[0] if rel.parts else ""
        role = {"governing": "governing", "corpus": "source", "inquiry": "inquiry", "reports": "report", "provenance": "provenance", "llm": "llm-instruction"}.get(first, "other")
        records.append({"path": rel.as_posix(), "sha256": digest(dst), "size_bytes": dst.stat().st_size, "role": role, "repository_identifier": None, "media_type": None})

    manifest = {
        "contract_version": "1.0.0",
        "capsule_id": a.capsule_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repository": {
            "name": git(source, "config", "--get", "remote.origin.url", default=source.name),
            "commit": git(source, "rev-parse", "HEAD", default="0" * 40),
            "branch": git(source, "branch", "--show-current", default="unknown"),
            "dirty": bool(git(source, "status", "--porcelain", default=""))
        },
        "active_inquiry": None,
        "governing_state": {"orientation": "README.md", "safeguards": "governing/safeguards.md", "schemas": ["interop/spacedrive/capsule-manifest.schema.json", "interop/spacedrive/project-state.schema.json", "interop/spacedrive/transfer-record.schema.json"]},
        "files": records
    }
    (output / "capsule-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "CAPSULE.md").write_text("# Sanctum Portable Inquiry Capsule\n\nRead project-state, governing files, and the active inquiry before corpus material. Imported reports are not certified.\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
