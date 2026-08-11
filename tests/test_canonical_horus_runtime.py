import sys
from types import SimpleNamespace

import pytest

from sovereign_round import RoundError, _require_horus_commit, _resolve_horus_command, _source_head


def args(command=None, allow=False):
    return SimpleNamespace(horus_command=command, allow_horus_command_override=allow)


def test_production_resolves_runtime_from_estate_horus(tmp_path):
    horus = tmp_path / "Horus"
    runtime = horus / "runtime"
    runtime.mkdir(parents=True)
    gather = runtime / "gather.py"
    gather.write_text("print('fixture')\n", encoding="utf-8")
    assert _resolve_horus_command(horus, args()) == [sys.executable, str(gather.resolve())]


def test_arbitrary_horus_command_is_rejected_in_production(tmp_path):
    horus = tmp_path / "Horus"
    with pytest.raises(RoundError, match="test-only"):
        _resolve_horus_command(horus, args("python fake_horus.py", allow=False))


def test_test_override_requires_explicit_flag(tmp_path):
    horus = tmp_path / "Horus"
    assert _resolve_horus_command(horus, args("python fake_horus.py", allow=True)) == ["python", "fake_horus.py"]


def test_missing_canonical_runtime_fails_closed(tmp_path):
    with pytest.raises(RoundError, match="canonical Horus acquisition runtime is missing"):
        _resolve_horus_command(tmp_path / "Horus", args())


def test_horus_response_commit_must_match_pulled_estate_commit():
    commit = "a" * 40
    _require_horus_commit({"provenance": {"horus_repository_commit": commit}}, commit)
    with pytest.raises(RoundError, match="does not match"):
        _require_horus_commit({"provenance": {"horus_repository_commit": "b" * 40}}, commit)


def test_source_head_uses_exact_horus_checkout_state():
    commit = "c" * 40
    assert _source_head([{"repository": "Horus", "head": commit}], "Horus") == commit
    with pytest.raises(RoundError):
        _source_head([{"repository": "Horus", "head": "not-a-sha"}], "Horus")
