#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    request = json.loads(sys.stdin.read() or "{}")
    root = Path(request.get("root", ".")).resolve()
    manifest_path = root / "capsule-manifest.json"
    if not manifest_path.is_file():
        print(json.dumps({"error": "capsule-manifest.json not found"}))
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("files", []):
        path = root / item["path"]
        print(json.dumps({"id": item["sha256"], "path": item["path"], "title": path.name, "content_hash": item["sha256"], "size_bytes": item["size_bytes"], "role": item["role"], "trust": "authored", "metadata": {"capsule_id": manifest["capsule_id"], "repository": manifest["repository"], "repository_identifier": item.get("repository_identifier"), "media_type": item.get("media_type")}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
