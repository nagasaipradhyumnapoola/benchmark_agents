from typer.testing import CliRunner

from benchlab.cli import app
from benchlab.store import Store


def test_terminal_starts_empty_and_exits_without_creating_records(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCHLAB_DATA_DIR", str(tmp_path))
    result = CliRunner().invoke(app, ["terminal"], input="0\n")
    assert result.exit_code == 0, result.output
    assert "Connect a model" in result.output
    assert "Connect an agent" in result.output
    assert Store(tmp_path).list_models() == []
    assert Store(tmp_path).list_agents() == []


def test_terminal_never_echoes_a_key_pasted_as_an_environment_reference(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCHLAB_DATA_DIR", str(tmp_path))
    secret = "sk-do-not-echo-private-credential"
    answers = ["1", "Local model", "1", "http://127.0.0.1:1234/v1", "local-model", secret, "0"]
    result = CliRunner().invoke(app, ["terminal"], input="\n".join(answers) + "\n")
    assert result.exit_code == 0, result.output
    assert secret not in result.output
    assert "environment variable name" in result.output
    assert Store(tmp_path).list_models() == []


def test_terminal_validation_does_not_repeat_credentials_in_a_url(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_AGENTS_DATA_DIR", str(tmp_path))
    secret = "accidental-private-password"
    answers = ["1", "Local model", "1", f"https://user:{secret}@localhost/v1", "id", "", "0"]
    result = CliRunner().invoke(app, ["terminal"], input="\n".join(answers) + "\n")
    # Prompt input is echoed by the test runner, so inspect the validation message itself.
    error = result.output.split("Invalid configuration:")[-1]
    assert result.exit_code == 0
    assert secret not in error
    assert "without credentials" in error
    assert Store(tmp_path).list_models() == []
