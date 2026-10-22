import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    from benchlab.api import create_app

    with TestClient(create_app(tmp_path)) as client:
        yield client


def test_health_and_seeded_inventory(client):
    assert client.get("/api/health").json()["status"] == "ok"
    models = client.get("/api/models").json()
    assert {model["id"] for model in models} >= {"demo-reference", "demo-flawed"}


def test_foreign_origins_and_hosts_cannot_read_or_modify_local_lab(client):
    assert (
        client.get("/api/models", headers={"Origin": "https://attacker.example"}).status_code == 403
    )
    assert client.post("/api/demo", headers={"Origin": "null"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400


def test_validation_and_missing_resources(client):
    assert client.get("/api/experiments/missing").status_code == 404
    assert client.post("/api/models", json={"name": "invalid"}).status_code == 422
    assert client.post("/api/import", json={"name": "bad", "systems": []}).status_code == 422


def test_demo_lifecycle_is_persisted_with_real_verification(client):
    response = client.post("/api/demo")
    assert response.status_code == 201, response.text
    experiment = response.json()
    for _ in range(100):
        detail = client.get("/api/experiments/" + experiment["id"]).json()
        if detail["status"] not in {"queued", "running"}:
            break
        time.sleep(0.05)
    assert detail["status"] == "completed", detail
    assert detail["demo"] is True
    assert len(detail["runs"]) == 2
    results = [client.get("/api/runs/" + run["id"]).json() for run in detail["runs"]]
    assert any(task["passed"] for run in results for task in run["results"])
    assert any(not task["passed"] for run in results for task in run["results"])
    assert all(run["events"] for run in results)
    assert client.get("/api/experiments/" + experiment["id"]).json()["status"] == "completed"
    report = client.get(f"/api/experiments/{experiment['id']}/report?format=json")
    assert report.status_code == 200
    assert "demo" in report.text.lower()


def test_model_registration_never_accepts_inline_credentials(client):
    response = client.post(
        "/api/models",
        json={
            "name": "local",
            "adapter": "openai-compatible",
            "model": "x",
            "base_url": "http://127.0.0.1:1234/v1",
            "api_key": "secret",
        },
    )
    assert response.status_code == 422


def test_host_execution_requires_server_authorization(client):
    response = client.post(
        "/api/import",
        json={
            "name": "host",
            "systems": [{"model_id": "demo-reference"}],
            "allow_host_process": True,
        },
    )
    assert response.status_code == 403
