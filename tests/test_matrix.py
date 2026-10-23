"""Explicit controlled pairs reject partial bindings and reach the selected endpoint."""

import asyncio
import io
import json
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from benchlab.engine import Engine
from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig, SystemSpec
from benchlab.store import Store


@pytest.mark.asyncio
@pytest.mark.parametrize("member", ["model", "agent", "duplicate", "native"])
async def test_matrix_rejects_partial_duplicate_and_native_pairs(tmp_path, member):
    store = Store(tmp_path)
    model = ModelConfig(id="m", name="m", adapter="demo", model="reference", demo=True)
    agent = AgentConfig(id="a", name="a", adapter="demo", demo=True, native=member == "native")
    store.save_model(model)
    store.save_agent(agent)
    pair = SystemSpec(model_id="m", agent_id="a")
    systems = [pair]
    if member == "model":
        systems = [SystemSpec(agent_id="a")]
    elif member == "agent":
        systems = [SystemSpec(model_id="m")]
    elif member == "duplicate":
        systems.append(SystemSpec(model_id="m", agent_id="a", label="different label"))
    check = await Engine(store).validate(
        ExperimentConfig(name="matrix", mode="matrix", systems=systems, demo=True)
    )
    assert not check.compatible
    expected = (
        "duplicate" if member == "duplicate" else "native" if member == "native" else "explicit"
    )
    assert expected in " ".join(check.reasons).lower()


def test_matrix_rejects_native_product_even_without_native_metadata():
    from benchlab.adapters.registry import validate_system_config

    agent = AgentConfig(name="native", adapter="codex-cli", executable=sys.executable)
    pair = SystemSpec(agent_id=agent.id)
    check = validate_system_config(
        pair, None, agent, ExperimentConfig(name="matrix", mode="matrix", systems=[pair])
    )
    assert not check.compatible
    assert "native" in " ".join(check.reasons).lower()


@pytest.mark.asyncio
async def test_two_models_by_two_agents_preserve_exact_authenticated_pair_bindings(
    tmp_path, monkeypatch
):
    from benchlab.credentials import forget_key
    from benchlab.reports import export_experiment
    from benchlab.service import connect_model

    monkeypatch.setenv("BENCH_AGENTS_ALLOW_HOST_PROCESS", "1")
    monkeypatch.setenv("UNRELATED_PROVIDER_KEY", "unrelated-matrix-private-value")
    store = Store(tmp_path)
    servers, threads, references = [], [], []
    script = tmp_path / "matrix_harness.py"
    script.write_text(
        "import argparse,json,os,sys,urllib.request\n"
        "p=argparse.ArgumentParser();p.add_argument('--model');p.add_argument('--agent');a=p.parse_args()\n"
        "assert 'UNRELATED_PROVIDER_KEY' not in os.environ\n"
        "assert not any(k.startswith('BENCH_AGENTS_SESSION_') for k in os.environ)\n"
        "body={'model':a.model,'agent':a.agent,'messages':[{'role':'user','content':sys.stdin.read()}]}\n"
        "r=urllib.request.Request(os.environ['PAIR_URL']+'/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['PAIR_KEY']})\n"
        "with urllib.request.urlopen(r,timeout=10) as response: print(json.load(response)['choices'][0]['message']['content'])\n"
    )

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, body, valid):
            self.send_response(200 if valid else 401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def do_GET(self):
            valid = self.headers.get("Authorization") == "Bearer " + self.server.key
            self.reply({"data": [{"id": self.server.model}]}, valid)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.calls.append((body, self.headers.get("Authorization")))
            valid = (
                self.headers.get("Authorization") == "Bearer " + self.server.key
                and body["model"] == self.server.model
            )
            self.reply({"choices": [{"message": {"content": "37"}}]}, valid)

    try:
        for number in [1, 2]:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
            server.key = f"matrix-private-endpoint-{number}-key"
            server.model = f"wire-model-{number}"
            server.calls = []
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append(server)
            threads.append(thread)
            row = connect_model(
                store,
                ModelConfig(
                    id=f"m{number}",
                    name=f"m{number}",
                    adapter="openai-compatible",
                    model=server.model,
                    base_url=f"http://127.0.0.1:{server.server_port}/v1",
                ),
                api_key=server.key,
            )
            references.append(row["config"]["api_key_env"])
        for identity in ["a1", "a2"]:
            store.save_agent(
                AgentConfig(
                    id=identity,
                    name=identity,
                    adapter="subprocess",
                    executable=sys.executable,
                    args=[str(script), "--agent", identity],
                    model_flag="--model",
                    model_base_url_env="PAIR_URL",
                    model_api_key_env="PAIR_KEY",
                )
            )
        pairs = [
            SystemSpec(model_id=model, agent_id=agent)
            for model in ["m1", "m2"]
            for agent in ["a1", "a2"]
        ]
        engine = Engine(store)
        experiment = await engine.submit(
            ExperimentConfig(
                name="2 x 2 authenticated matrix fixture",
                mode="matrix",
                systems=pairs,
                task_ids=["reasoning-inventory"],
                isolation="workspace",
                allow_host_process=True,
            )
        )
        await engine.execute(experiment["id"])
        runs = store.list_runs(experiment["id"])
        assert len(runs) == 4
        assert {(r["manifest"]["model"]["id"], r["manifest"]["agent"]["id"]) for r in runs} == {
            ("m1", "a1"),
            ("m1", "a2"),
            ("m2", "a1"),
            ("m2", "a2"),
        }
        assert all(store.list_results(run["id"])[0]["passed"] for run in runs)
        for server in servers:
            assert len(server.calls) == 2
            assert {(body["model"], body["agent"], auth) for body, auth in server.calls} == {
                (server.model, "a1", "Bearer " + server.key),
                (server.model, "a2", "Bearer " + server.key),
            }
            assert all("expected" not in json.dumps(body) for body, _ in server.calls)
        exported, _, _ = export_experiment(store, experiment["id"], "zip")
        with zipfile.ZipFile(io.BytesIO(exported)) as archive:
            contents = b"".join(archive.read(name) for name in archive.namelist())
        saved = store.db.read_bytes() + contents
        assert all(server.key.encode() not in saved for server in servers)
        assert b"unrelated-matrix-private-value" not in saved
    finally:
        for server in servers:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)
        for reference in references:
            forget_key(reference)
