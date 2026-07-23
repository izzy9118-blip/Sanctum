from __future__ import annotations

import subprocess
from pathlib import Path

from .errors import SanctumFederationError


class GitSnapshot:
    def __init__(self, repository_root: Path) -> None:
        self.root = repository_root.expanduser().resolve()
        if not (self.root / ".git").exists():
            raise SanctumFederationError(
                f"Not a Git checkout: {self.root}"
            )

    def _run_text(self, *args: str, check: bool = True) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if check and completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip()
            raise SanctumFederationError(
                message or f"Git command failed: {' '.join(args)}"
            )
        return completed.stdout

    def resolve_commit(self, ref: str) -> str:
        return self._run_text("rev-parse", f"{ref}^{{commit}}").strip()

    def head(self) -> str:
        return self.resolve_commit("HEAD")

    def verify_clean_head(self, expected_commit: str) -> str:
        resolved = self.resolve_commit(expected_commit)
        head = self.head()
        if head != resolved:
            raise SanctumFederationError(
                "Execution requires checkout HEAD to equal the pinned commit: "
                f"{head} != {resolved}"
            )
        status = self._run_text(
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
        if status.strip():
            raise SanctumFederationError(
                f"Execution requires a clean checkout: {self.root}"
            )
        return resolved

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.returncode == 0

    def read_bytes(self, commit: str, repository_path: str) -> bytes:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "show",
                f"{commit}:{repository_path}",
            ],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            message = completed.stderr.decode("utf-8", errors="replace").strip()
            raise SanctumFederationError(
                message
                or f"Cannot read {repository_path} at {commit}"
            )
        return completed.stdout

    def read_text(self, commit: str, repository_path: str) -> str:
        try:
            return self.read_bytes(commit, repository_path).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SanctumFederationError(
                f"Git object is not UTF-8: {repository_path} at {commit}"
            ) from exc

    def blob_sha(self, commit: str, repository_path: str) -> str:
        return self._run_text(
            "rev-parse",
            f"{commit}:{repository_path}",
        ).strip()
