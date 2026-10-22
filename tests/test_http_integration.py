"""Real loopback HTTP fixture servers test wire behavior, not model intelligence."""

import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from benchlab.engine import Engine
from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig, SystemSpec
from benchlab.store import Store


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, payload):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_GET(self):
        assert self.path == "/v1/models"
        self.send({"data": [{"id": "wire-fixture"}]})

    def do_POST(self):
        assert self.path == "/v1/chat/completions"
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(body)
        assert body["model"] == "wire-fixture"
        assert "expected" not in body
        assert body["seed"] == 42
        content = "37" if self.server.correct else "wrong"
        self.send(
            {
                "choices": [{"message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 31, "completion_tokens": 2},
            }
        )


@pytest.mark.asyncio
async def test_two_independent_http_endpoints_execute_and_verify_persisted_comparison(tmp_path):
    servers = []
    threads = []
    try:
        store = Store(tmp_path)
        systems = []
        for correct in [True, False]:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
            server.correct = correct
            server.requests = []
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append(server)
            threads.append(thread)
            config = ModelConfig(
                name=f"Wire fixture {correct}",
                adapter="openai-compatible",
                model="wire-fixture",
                base_url=f"http://127.0.0.1:{server.server_port}/v1",
                input_cost_per_million=1,
                output_cost_per_million=2,
            )
            model = store.save_model(config)
            systems.append(SystemSpec(model_id=model["id"]))
        engine = Engine(store)
        config = ExperimentConfig(
            name="HTTP protocol integration fixture — not real intelligence",
            systems=systems,
            task_ids=["reasoning-inventory"],
        )
        experiment = await engine.submit(config)
        await engine.execute(experiment["id"])
        runs = store.list_runs(experiment["id"])
        assert len(runs) == 2
        assert [store.list_results(run["id"])[0]["passed"] for run in runs] == [True, False]
        assert all(
            run["manifest"]["config"]["systems"] == config.model_dump(mode="json")["systems"]
            for run in runs
        )
        assert all(store.list_results(run["id"])[0]["output"]["input_tokens"] == 31 for run in runs)
        assert all(len(server.requests) == 1 for server in servers)
        from benchlab.analysis import compare_runs

        comparison = compare_runs(store, [run["id"] for run in runs])
        assert comparison["comparable"] is True
        assert comparison["paired_differences"][0]["regressed"] == 1
    finally:
        for server in servers:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)


@pytest.mark.asyncio
async def test_controlled_agent_pair_calls_selected_endpoint_via_real_subprocess(
    tmp_path, monkeypatch
):
    class HarnessProvider(Provider):
        def do_POST(self):
            assert self.path == "/v1/chat/completions"
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.requests.append(body)
            assert body["model"] == "wire-fixture"
            assert "expected" not in body
            self.send({"choices": [{"message": {"content": "37"}}]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), HarnessProvider)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("BENCHLAB_ALLOW_HOST_PROCESS", "1")
    try:
        store = Store(tmp_path)
        model = ModelConfig(
            name="Harness protocol fixture",
            adapter="openai-compatible",
            model="wire-fixture",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
        )
        store.save_model(model)
        systems = []
        for name in ["Harness A", "Harness B"]:
            agent = AgentConfig(
                name=name,
                adapter="subprocess",
                executable=sys.executable,
                args=[str(Path("examples/adapters/minimal_chat_agent.py").resolve())],
                model_flag="--model",
                model_base_url_env="HARNESS_BASE_URL",
            )
            store.save_agent(agent)
            systems.append(SystemSpec(model_id=model.id, agent_id=agent.id))
        config = ExperimentConfig(
            name="Controlled harness wire fixture, not model intelligence",
            mode="agent",
            systems=systems,
            task_ids=["reasoning-inventory"],
            isolation="workspace",
            allow_host_process=True,
        )
        engine = Engine(store)
        experiment = await engine.submit(config)
        await engine.execute(experiment["id"])
        runs = store.list_runs(experiment["id"])
        assert len(runs) == 2 and len(server.requests) == 2
        assert all(store.list_results(run["id"])[0]["passed"] for run in runs)
        from benchlab.analysis import compare_runs

        assert compare_runs(store, [run["id"] for run in runs])["comparable"]
    finally:
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        thread.join(timeout=2)
