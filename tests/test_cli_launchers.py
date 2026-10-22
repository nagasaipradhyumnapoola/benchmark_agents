import pytest

from benchlab.adapters import registry
from benchlab.schemas import AgentConfig


def test_shell_launcher_rejected(tmp_path, monkeypatch):
    launcher = tmp_path / "agent.cmd"
    launcher.write_text("@echo off")
    monkeypatch.setattr(registry.shutil, "which", lambda _: str(launcher))
    agent = AgentConfig(name="unsafe wrapper", adapter="subprocess", executable="agent")
    with pytest.raises(ValueError, match="Shell scripts"):
        registry.cli_argv(agent, None, "$(untrusted) & commands")


def test_codex_npm_launcher_resolves_to_node_without_shell(tmp_path, monkeypatch):
    entry = tmp_path / "node_modules/@openai/codex/bin/codex.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("// fixture")
    shim = tmp_path / "codex.cmd"
    node = str(tmp_path / "node.exe")
    monkeypatch.setattr(
        registry.shutil, "which", lambda name: node if name == "node" else str(shim)
    )
    agent = AgentConfig(name="codex", adapter="codex-cli")
    prompt = "untrusted & del ; $(anything)"
    argv = registry.cli_argv(agent, None, prompt)
    assert argv[:2] == [node, str(entry)]
    assert argv[-1] == prompt
    assert "cmd.exe" not in argv


def test_opencode_npm_launcher_resolves_native_binary(tmp_path, monkeypatch):
    entry = tmp_path / "node_modules/opencode-ai/bin/opencode.exe"
    entry.parent.mkdir(parents=True)
    entry.write_bytes(b"fixture")
    monkeypatch.setattr(registry.shutil, "which", lambda _: str(tmp_path / "opencode.cmd"))
    agent = AgentConfig(name="opencode", adapter="opencode-cli")
    assert registry.cli_argv(agent, None, "hello")[0] == str(entry)
