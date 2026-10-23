"""User-level terminal flow against a real local HTTP fixture and real subprocess."""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from typer.testing import CliRunner

from benchlab.cli import app
from benchlab.store import Store


def test_user_connects_model_pairs_agent_runs_and_exports(tmp_path, monkeypatch):
    key = "local-terminal-fixture-credential"
    calls = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, data):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        def do_GET(self):
            assert self.headers.get("Authorization") == "Bearer " + key
            self.send({"data": [{"id": "terminal-fixture"}]})

        def do_POST(self):
            assert self.headers.get("Authorization") == "Bearer " + key
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert body["model"] == "terminal-fixture"
            assert "expected" not in body
            calls.append(body)
            self.send({"choices": [{"message": {"content": "37"}}]})

    monkeypatch.setenv("BENCHLAB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BENCHLAB_ALLOW_HOST_PROCESS", "1")
    monkeypatch.setenv("TEST_TERMINAL_KEY", key)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    report = tmp_path / "terminal-report.zip"
    try:
        answers = [
            "1",
            "My local model",
            "1",
            f"http://127.0.0.1:{server.server_port}/v1",
            "terminal-fixture",
            "TEST_TERMINAL_KEY",
            "2",
            "My custom harness",
            "1",
            sys.executable,
            str(Path("examples/adapters/minimal_chat_agent.py").resolve()),
            "[]",
            "--model",
            "HARNESS_BASE_URL",
            "HARNESS_API_KEY",
            "",
            "4",
            "1",
            "1",
            "1",
            "y",
            "y",
            "y",
            "6",
            "1",
            "y",
            str(report),
            "0",
        ]
        result = CliRunner().invoke(app, ["terminal"], input="\n".join(answers) + "\n")
        assert result.exit_code == 0, result.output
        assert key not in result.output
        assert "Compatibility: READY" in result.output
        assert "1/1 verified" in result.output
        assert len(calls) == 1
        store = Store(tmp_path / "data")
        assert (
            len(store.list_models())
            == len(store.list_agents())
            == len(store.list_experiments())
            == 1
        )
        run = store.list_runs()[0]
        assert run["manifest"]["config"]["mode"] == "agent"
        assert store.list_results(run["id"])[0]["passed"]
        assert report.read_bytes().startswith(b"PK")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
