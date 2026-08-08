from pathlib import Path

import pytest

from evidence_genealogy import GenealogyError
from minister_ground_files import validate_minister_ground_files


def package(path="corpus/witness.yaml", witness="XEN-WIT-PRI-001", source="XEN-SRC-PRI-001"):
    return {
        "repository": {"full_name": "Xenophon", "git_commit": "a" * 40},
        "propositions": [{
            "proposition_id": "PROP-001",
            "genealogy": [{
                "origin": "minister_repository",
                "witness_id": witness,
                "source_id": source,
                "repository_commit": "a" * 40,
                "path": path,
                "locator": "Book I"
            }]
        }]
    }


def test_resolves_ids_inside_pinned_house_file(tmp_path: Path):
    file = tmp_path / "Xenophon" / "corpus" / "witness.yaml"
    file.parent.mkdir(parents=True)
    file.write_text("id: XEN-WIT-PRI-001\nsource_id: XEN-SRC-PRI-001\n", encoding="utf-8")
    validate_minister_ground_files(package(), tmp_path)


def test_rejects_missing_file(tmp_path: Path):
    (tmp_path / "Xenophon").mkdir()
    with pytest.raises(GenealogyError):
        validate_minister_ground_files(package(), tmp_path)


def test_rejects_witness_not_in_file(tmp_path: Path):
    file = tmp_path / "Xenophon" / "corpus" / "witness.yaml"
    file.parent.mkdir(parents=True)
    file.write_text("id: OTHER-WIT\nsource_id: XEN-SRC-PRI-001\n", encoding="utf-8")
    with pytest.raises(GenealogyError):
        validate_minister_ground_files(package(), tmp_path)


def test_rejects_source_not_in_file(tmp_path: Path):
    file = tmp_path / "Xenophon" / "corpus" / "witness.yaml"
    file.parent.mkdir(parents=True)
    file.write_text("id: XEN-WIT-PRI-001\nsource_id: OTHER-SRC\n", encoding="utf-8")
    with pytest.raises(GenealogyError):
        validate_minister_ground_files(package(), tmp_path)


def test_rejects_path_escape(tmp_path: Path):
    (tmp_path / "Xenophon").mkdir()
    with pytest.raises(GenealogyError):
        validate_minister_ground_files(package(path="../secret.txt"), tmp_path)
