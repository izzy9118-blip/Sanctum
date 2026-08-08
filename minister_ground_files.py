#!/usr/bin/env python3
"""Resolve minister_repository genealogy entries against the pinned local house.

The round has already pulled the estate and recorded the exact house HEAD. This
validator prevents a minister from satisfying genealogy with a plausible-looking
path whose file does not contain the cited sovereign witness/source identities.
"""
from __future__ import annotations

from pathlib import Path

from evidence_genealogy import GenealogyError


def validate_minister_ground_files(package: dict, estate_root: Path) -> None:
    repository = package.get("repository", {})
    repo_name = str(repository.get("full_name", "")).rstrip("/").split("/")[-1]
    if not repo_name:
        raise GenealogyError("repository.full_name cannot resolve a house directory")
    house_root = (Path(estate_root) / repo_name).resolve()
    if not house_root.is_dir():
        raise GenealogyError(f"pinned minister house directory is absent: {house_root}")

    for proposition in package.get("propositions", []):
        proposition_id = proposition.get("proposition_id", "?")
        for ground in proposition.get("genealogy", []):
            if ground.get("origin") != "minister_repository":
                continue
            relative = Path(ground["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise GenealogyError(f"{proposition_id} minister ground path escapes the house")
            path = (house_root / relative).resolve()
            try:
                path.relative_to(house_root)
            except ValueError as exc:
                raise GenealogyError(f"{proposition_id} minister ground path escapes the house") from exc
            if not path.is_file():
                raise GenealogyError(f"{proposition_id} minister ground file does not exist: {ground['path']}")
            text = path.read_text(encoding="utf-8")
            witness_id = ground["witness_id"]
            source_id = ground["source_id"]
            if witness_id not in text:
                raise GenealogyError(
                    f"{proposition_id} witness_id {witness_id!r} is not present in {ground['path']}"
                )
            if source_id not in text:
                raise GenealogyError(
                    f"{proposition_id} source_id {source_id!r} is not present in {ground['path']}"
                )
