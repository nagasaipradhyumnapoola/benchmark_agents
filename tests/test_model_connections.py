"""Write-only credentials are resolved at runtime, never persisted in records."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from benchlab.api import create_app


@pytest.fixture(autouse=True)
def isolated_process_credentials(monkeypatch):
    # Each credential scenario models a fresh backend process. Production retains
    # retired keys until exit; test-only keys must not mask unrelated later tests.
    import benchlab.credentials as credentials

    monkeypatch.setattr(credentials, "_keys", {})
    monkeypatch.setattr(credentials, "_redaction_history", set())


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path, run_worker=False)) as result:
        yield result


def connection(identity="connected"):
    return {
        "id": identity,
        "name": identity,
        "adapter": "openai-compatible",
        "model": "wire-model",
        "base_url": "http://127.0.0.1:1/v1",
        "connection_type": "local",
    }


def test_connect_keeps_keys_out_of_environment_response_and_disk(client, tmp_path):
    key = "private-entered-key-distinct-12345"
    before = dict(os.environ)
    response = client.post("/api/models/connect", json={"config": connection(), "api_key": key})
    assert response.status_code == 201, response.text
    reference = response.json()["config"]["api_key_env"]
    assert reference.startswith("BENCH_AGENTS_SESSION_")
    assert response.json()["config"]["connection_type"] == "local"
    assert os.environ == before
    assert key not in response.text
    assert key not in client.get("/api/models").text
    from benchlab.credentials import forget_key, get_key

    assert get_key(reference) == key
    assert key.encode() not in (tmp_path / "bench-agents.sqlite3").read_bytes()
    assert client.delete("/api/models/connected").status_code == 204
    assert get_key(reference) is None
    forget_key(reference)


def test_reentry_only_changes_own_session_reference(client, monkeypatch):
    from benchlab.credentials import forget_key, get_key

    refs = []
    for identity in ["first", "second"]:
        row = client.post(
            "/api/models/connect",
            json={"config": connection(identity), "api_key": f"private-{identity}-original-key"},
        )
        assert row.status_code == 201, row.text
        refs.append(row.json()["config"]["api_key_env"])
    forget_key(refs[0])
    probe = client.post("/api/models/first/probe").json()
    assert not probe["compatible"]
    assert "re-enter" in " ".join(probe["reasons"]).lower()
    response = client.post("/api/models/first/credential", json={"api_key": "replacement-key-123"})
    assert response.json() == {"configured": True, "scope": "session"}
    assert get_key(refs[0]) == "replacement-key-123"
    assert get_key(refs[1]) == "private-second-original-key"
    monkeypatch.setenv("EXTERNAL_PROVIDER_KEY", "environment-value")
    model = connection("environment")
    model["api_key_env"] = "EXTERNAL_PROVIDER_KEY"
    assert client.post("/api/models", json=model).status_code == 201
    response = client.post(
        "/api/models/environment/credential", json={"api_key": "bad-replacement"}
    )
    assert response.status_code == 422
    assert get_key("EXTERNAL_PROVIDER_KEY") == "environment-value"
    assert client.post("/api/models/missing/credential", json={"api_key": "x"}).status_code == 404
    for reference in refs:
        forget_key(reference)


@pytest.mark.parametrize(
    "key",
    ["", "a" * 8193, {"sensitive": "never-echo-this-input"}],
    ids=["empty", "too-long", "object"],
)
def test_invalid_key_is_rejected_without_echoing_input(client, key):
    response = client.post("/api/models/connect", json={"config": connection(), "api_key": key})
    assert response.status_code == 422
    assert "never-echo-this-input" not in response.text
    assert "a" * 100 not in response.text


def test_plain_registration_still_rejects_inline_key(client):
    config = connection()
    config["api_key"] = "never-echo-inline-secret"
    response = client.post("/api/models", json=config)
    assert response.status_code == 422
    assert "never-echo-inline-secret" not in response.text


def test_failed_save_cleans_new_key_and_preserves_previous_credential(client):
    from benchlab.credentials import forget_key, get_key, secret_values

    response = client.post(
        "/api/models/connect", json={"config": connection(), "api_key": "existing-session-key-123"}
    )
    assert response.status_code == 201
    reference = response.json()["config"]["api_key_env"]
    from benchlab.schemas import ExperimentConfig, SystemSpec

    client.app.state.store.create_experiment(
        ExperimentConfig(name="immutable", systems=[SystemSpec(model_id="connected")])
    )
    changed = connection()
    changed["model"] = "changed-model"
    response = client.post(
        "/api/models/connect", json={"config": changed, "api_key": "failed-save-secret-123"}
    )
    assert response.status_code == 422
    # Failed saves remove active lookup, while late errors must still be masked.
    assert "failed-save-secret-123" in list(secret_values())
    assert get_key(reference) == "existing-session-key-123"
    assert client.delete("/api/models/connected").status_code == 422
    assert get_key(reference) == "existing-session-key-123"
    forget_key(reference)


def test_session_keys_redact_in_unstructured_text_and_environment_fallback(monkeypatch):
    from benchlab.credentials import forget_key, get_key, remember_key
    from benchlab.settings import redact

    reference = remember_key("private-runtime-redaction-12345")
    try:
        assert redact("error private-runtime-redaction-12345 echoed") == "error [REDACTED] echoed"
        assert get_key(None) is None
        monkeypatch.setenv("LEGACY_PROVIDER_KEY", "legacy-provider-key-12345")
        assert get_key("LEGACY_PROVIDER_KEY") == "legacy-provider-key-12345"
        with pytest.raises(ValueError):
            remember_key("overwrite", "LEGACY_PROVIDER_KEY")
        assert get_key("LEGACY_PROVIDER_KEY") == "legacy-provider-key-12345"
    finally:
        forget_key(reference)


def test_short_key_is_accepted_and_redacted_without_corrupting_registration(client):
    from benchlab.credentials import forget_key, get_key
    from benchlab.settings import redact

    response = client.post("/api/models/connect", json={"config": connection(), "api_key": "a"})
    assert response.status_code == 201, response.text
    reference = response.json()["config"]["api_key_env"]
    try:
        assert response.json()["config"]["adapter"] == "openai-compatible"
        assert get_key(reference) == "a"
        assert redact("key: a; failed") == "key: [REDACTED]; failed"
    finally:
        forget_key(reference)


@pytest.mark.parametrize("key", ["local", "http", "model", "status"])
def test_common_short_keys_preserve_structural_records_and_redact_outputs(client, key):
    from benchlab.credentials import forget_key, get_key
    from benchlab.schemas import ExperimentConfig, ModelConfig, SystemSpec
    from benchlab.settings import redact

    config = connection(key)
    response = client.post("/api/models/connect", json={"config": config, "api_key": key})
    assert response.status_code == 201, response.text
    row = response.json()
    reference = row["config"]["api_key_env"]
    try:
        parsed = ModelConfig.model_validate(row["config"])
        assert parsed.id == key
        assert parsed.model == config["model"]
        assert parsed.connection_type == "local"
        assert parsed.base_url == config["base_url"]
        assert client.get(f"/api/models/{key}").status_code == 200
        experiment = client.app.state.store.create_experiment(
            ExperimentConfig(
                name="Short credential", mode="model", systems=[SystemSpec(model_id=key)]
            )
        )
        assert ExperimentConfig.model_validate(experiment["config"]).mode == "model"
        assert experiment["config"]["systems"][0]["model_id"] == key
        assert get_key(reference) == key
        text = f"provider echoed {key}; request failed"
        assert key not in redact(text)
        masked = redact(
            {
                "error": text,
                "output": {"model": key, "base_url": f"http://example.com/{key}"},
                "api_key": key,
            }
        )
        assert masked["api_key"] == "[REDACTED]"
        assert key not in masked["error"]
        assert masked["output"]["model"] == "[REDACTED]"
        assert key not in masked["output"]["base_url"]
    finally:
        forget_key(reference)


def test_rotated_and_deleted_keys_remain_redacted_from_late_output():
    from benchlab.credentials import forget_key, get_key, remember_key, secret_values
    from benchlab.settings import redact

    original = "original-inflight-credential-123"
    replacement = "replacement-active-credential-456"
    reference = remember_key(original)
    remember_key(replacement, reference)
    assert get_key(reference) == replacement
    assert original in secret_values()
    assert redact(f"late stderr: {original}") == "late stderr: [REDACTED]"
    forget_key(reference)
    assert get_key(reference) is None
    assert replacement in secret_values()
    assert redact({"output": replacement, "error": original}) == {
        "output": "[REDACTED]",
        "error": "[REDACTED]",
    }


def test_cannot_register_a_second_model_with_another_models_session_reference(client):
    from benchlab.credentials import forget_key, get_key

    first = client.post(
        "/api/models/connect", json={"config": connection("owner"), "api_key": "owner-secret-123"}
    )
    assert first.status_code == 201
    reference = first.json()["config"]["api_key_env"]
    try:
        second = connection("imposter")
        second["api_key_env"] = reference
        assert client.post("/api/models", json=second).status_code == 422
        assert (
            client.post("/api/models/imposter/credential", json={"api_key": "replace"}).status_code
            == 404
        )
        assert get_key(reference) == "owner-secret-123"
    finally:
        forget_key(reference)


@pytest.mark.asyncio
async def test_probe_and_generation_use_session_key_on_real_http(tmp_path):
    from benchlab.engine import Engine
    from benchlab.schemas import ExperimentConfig, ModelConfig, SystemSpec
    from benchlab.service import connect_model
    from benchlab.store import Store

    key = "private-http-session-12345"
    calls = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, body):
            calls.append((self.path, self.headers.get("Authorization")))
            self.send_response(200 if self.headers.get("Authorization") == "Bearer " + key else 401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def do_GET(self):
            self.reply({"data": [{"id": "wire-model"}]})

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.reply({"choices": [{"message": {"content": "37"}}]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    reference = None
    try:
        store = Store(tmp_path)
        config = connection()
        config["base_url"] = f"http://127.0.0.1:{server.server_port}/v1"
        row = connect_model(store, ModelConfig(**config), api_key=key)
        reference = row["config"]["api_key_env"]
        engine = Engine(store)
        experiment = await engine.submit(
            ExperimentConfig(
                name="session HTTP",
                systems=[SystemSpec(model_id=row["id"])],
                task_ids=["reasoning-inventory"],
            )
        )
        await engine.execute(experiment["id"])
        run = store.list_runs(experiment["id"])[0]
        assert store.list_results(run["id"])[0]["passed"]
        assert ("/v1/models", "Bearer " + key) in calls
        assert ("/v1/chat/completions", "Bearer " + key) in calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if reference:
            from benchlab.credentials import forget_key

            forget_key(reference)
