from pathlib import Path
from types import SimpleNamespace

import harness
import secretary_gate
from tests.test_secretary_gate import polity_checklist


def test_codex_cli_provider_uses_gated_read_only_ephemeral_call(monkeypatch, tmp_path):
    checklist = polity_checklist()
    token = secretary_gate.open_gate(checklist)
    receipt = secretary_gate.StageLedger(token).enter("investigative_query")
    observed = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["input"] = kwargs["input"]
        output = Path(argv[argv.index("-o") + 1])
        output.write_text('{"record_type":"minister_horus_query"}', encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    result = harness.call(
        {
            "provider": "codex_cli",
            "command": "codex",
            "model": "gpt-test",
            "workdir": str(tmp_path),
        },
        "immutable prompt",
        pass_token=token,
        stage_receipt=receipt,
    )

    assert result["text"] == '{"record_type":"minister_horus_query"}'
    assert result["model"] == "gpt-test"
    assert observed["input"] == "immutable prompt"
    assert observed["argv"][:4] == ["codex", "-m", "gpt-test", "exec"]
    assert "--ephemeral" in observed["argv"]
    assert "read-only" in observed["argv"]
