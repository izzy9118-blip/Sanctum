#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("report", type=Path)
    p.add_argument("--destination", type=Path, default=Path("reports/imported"))
    p.add_argument("--model", required=True)
    p.add_argument("--provider", default="unknown")
    a = p.parse_args()
    report = a.report.resolve()
    if not report.is_file():
        raise SystemExit(f"report not found: {report}")
    destination = a.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / report.name
    if target.exists():
        raise SystemExit(f"refusing to overwrite: {target}")
    shutil.copy2(report, target)
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".provenance.json")
    sidecar.write_text(json.dumps({"status": "candidate", "imported_at": datetime.now(timezone.utc).isoformat(), "model": a.model, "provider": a.provider, "path": target.name, "sha256": sha, "certified": False}, indent=2) + "\n", encoding="utf-8")
    print(sidecar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
