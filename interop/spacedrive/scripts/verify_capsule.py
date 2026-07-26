#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("capsule", type=Path)
    root = p.parse_args().capsule.resolve()
    manifest_path = root / "capsule-manifest.json"
    if not manifest_path.is_file():
        print("missing capsule-manifest.json")
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    for item in manifest.get("files", []):
        path = root / item["path"]
        if not path.is_file():
            errors.append(f"missing: {item['path']}")
        elif digest(path) != item["sha256"]:
            errors.append(f"hash mismatch: {item['path']}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"verified {len(manifest.get('files', []))} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
