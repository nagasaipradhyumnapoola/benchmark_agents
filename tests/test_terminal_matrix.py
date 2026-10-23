"""Multi-model terminal selection through real local HTTP and subprocess adapters."""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from typer.testing import CliRunner

from benchlab.cli import app
from benchlab.schemas import AgentConfig, ModelConfig
from benchlab.sdk import Laboratory


@pytest.fixture
def matrix_lab(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_AGENTS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BENCH_AGENTS_ALLOW_HOST_PROCESS", "1")
    calls = []
    keys = {"first": "terminal-first-private-fixture", "second": "terminal-second-private-fixture"}

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, payload):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        def do_GET(self):
            assert self.headers.get("Authorization") in {"Bearer " + key for key in keys.values()}
            self.send({"data": [{"id": model} for model in keys]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.headers.get("Authorization") == "Bearer " + keys[body["model"]]
            assert "expected" not in body
            calls.append(body["model"])
            self.send({"choices": [{"message": {"content": "37"}}]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    lab = Laboratory(tmp_path)
    for model, key in keys.items():
        monkeypatch.setenv("FIXTURE_KEY_" + model, key)
        lab.store.save_model(
            ModelConfig(
                id=model,
                name=model,
                adapter="openai-compatible",
                model=model,
                base_url=f"http://127.0.0.1:{server.server_port}/v1",
                api_key_env="FIXTURE_KEY_" + model,
            )
        )
    for identity in ["one", "two"]:
        lab.store.save_agent(
            AgentConfig(
                id=identity,
                name=identity,
                adapter="subprocess",
                executable=sys.executable,
                args=[str(Path("examples/adapters/minimal_chat_agent.py").resolve())],
                model_flag="--model",
                model_base_url_env="HARNESS_BASE_URL",
                model_api_key_env="HARNESS_API_KEY",
            )
        )
    try:
        yield lab, calls, keys
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_terminal_runs_each_of_two_models_with_each_of_two_agents(matrix_lab):
    lab, calls, keys = matrix_lab
    answers = ["8", "1,2", "1,2", "1", "y", "y", "y", "0"]
    result = CliRunner().invoke(app, ["terminal"], input="\n".join(answers) + "\n")
    assert result.exit_code == 0, result.output
    assert "4 model-agent combinations" in result.output
    assert len(lab.store.list_runs()) == 4
    assert sorted(calls) == ["first", "first", "second", "second"]
    assert {
        (run["manifest"]["system"]["model_id"], run["manifest"]["system"]["agent_id"])
        for run in lab.store.list_runs()
    } == {(model, agent) for model in keys for agent in ["one", "two"]}
    assert all(lab.store.list_results(run["id"])[0]["passed"] for run in lab.store.list_runs())
    assert all(key not in result.output for key in keys.values())


def test_terminal_declining_matrix_launch_does_not_generate_or_save_experiment(matrix_lab):
    lab, calls, _ = matrix_lab
    result = CliRunner().invoke(app, ["terminal"], input="8\nall\nall\n1\ny\ny\nn\n0\n")
    assert result.exit_code == 0
    assert "Run not launched" in result.output
    assert calls == [] and lab.store.list_experiments() == []


def test_terminal_session_key_entry_is_hidden_and_not_persisted(matrix_lab):
    lab, _, keys = matrix_lab
    model = lab.store.get_model("first")["config"]
    answers = [
        "1",
        "Session connection",
        "1",
        "1",
        model["base_url"],
        "first",
        "3",
        keys["first"],
        "0",
    ]
    result = CliRunner().invoke(app, ["terminal"], input="\n".join(answers) + "\n")
    assert result.exit_code == 0
    assert "Compatibility: READY" in result.output
    assert keys["first"] not in result.output
    saved = lab.store.list_models()[-1]
    assert saved["config"]["api_key_env"].startswith("BENCH_AGENTS_SESSION_")
    assert keys["first"] not in json.dumps(saved)


def test_terminal_refuses_more_than_sixteen_pairs_before_discovery(matrix_lab):
    lab, calls, _ = matrix_lab
    for index in range(3):
        lab.store.save_model(
            ModelConfig(
                name=f"Extra model {index}",
                adapter="openai-compatible",
                model=f"extra-{index}",
                base_url="http://127.0.0.1:65530/v1",
            )
        )
    for index in range(2):
        lab.store.save_agent(
            AgentConfig(
                name=f"Extra harness {index}", adapter="subprocess", executable=sys.executable
            )
        )
    result = CliRunner().invoke(app, ["terminal"], input="8\nall\nall\n0\n")
    assert result.exit_code == 0
    assert "20 systems" in result.output and "at most 16" in result.output
    assert calls == [] and lab.store.list_experiments() == []
