"""Real standalone Hub API and portable release contract checks."""

import copy
import hashlib
import json
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from benchlab.hub import create_hub_app
from benchlab.hub_schemas import AgentRelease, AuthCredentials, release_digest


@pytest.fixture
def client(tmp_path):
    with TestClient(create_hub_app(tmp_path)) as client:
        yield client


def release(version="1.0.0"):
    return {
        "manifest": {
            "slug": "tiny-agent",
            "name": "Tiny Agent",
            "summary": "A test agent",
            "readme": "# Source",
            "version": version,
            "license": "Apache-2.0",
            "runtime": "python",
            "entrypoint": "agent.py",
            "recommended_models": ["test-model"],
            "benchmark_ids": ["coding"],
            "tags": ["coding"],
        },
        "files": {"agent.py": "print('hello')\n"},
    }


def account(client, username="alice"):
    response = client.post(
        "/v1/auth/register", json={"username": username, "password": "correct horse battery staple"}
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_empty_separate_service_and_security_headers(client):
    assert client.get("/v1/health").json() == {"status": "ok"}
    assert client.get("/v1/agents").json() == {"items": [], "total": 0}
    assert client.get("/api/models").status_code == 404
    assert client.get("/v1/health", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/v1/health", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/v1/health", headers={"Origin": "null"}).status_code == 403
    assert client.get("/v1/health").headers["X-Content-Type-Options"] == "nosniff"


def test_auth_password_and_tokens_hashed_expiry_logout(client, tmp_path):
    token = account(client)
    assert client.get("/v1/auth/me", headers=bearer(token)).json() == {
        "user": {"username": "alice"}
    }
    assert client.get("/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/v1/auth/register",
            json={"username": "alice", "password": "correct horse battery staple"},
        ).status_code
        == 409
    )
    for username in ["alice", "unknown"]:
        response = client.post(
            "/v1/auth/login", json={"username": username, "password": "wrong password"}
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid username or password"}
    logged = client.post(
        "/v1/auth/login", json={"username": "alice", "password": "correct horse battery staple"}
    )
    assert logged.status_code == 200
    db_path = tmp_path / "hub.sqlite3"
    content = db_path.read_bytes()
    assert token.encode() not in content
    assert b"correct horse battery staple" not in content
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE sessions SET expires_at = ?", (time.time() - 1,))
    assert client.get("/v1/auth/me", headers=bearer(token)).status_code == 401
    fresh = client.post(
        "/v1/auth/login", json={"username": "alice", "password": "correct horse battery staple"}
    ).json()["token"]
    assert client.post("/v1/auth/logout", headers=bearer(fresh)).status_code == 200
    assert client.get("/v1/auth/me", headers=bearer(fresh)).status_code == 401


def test_login_throttling_and_validation_never_echo_secrets(client):
    secret = "private-password-value"
    response = client.post("/v1/auth/register", json={"username": "bad name", "password": secret})
    assert response.status_code == 422
    assert secret not in response.text
    assert '"input"' not in response.text
    # Invalid registration also consumes the peer's authentication budget.
    for _ in range(9):
        assert (
            client.post(
                "/v1/auth/login", json={"username": "nobody", "password": "bad-password"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/v1/auth/login", json={"username": "nobody", "password": "bad-password"}
        ).status_code
        == 429
    )


def test_publish_ownership_versions_downloads_search_and_digest(client):
    alice, bob = account(client), account(client, "bob")
    first = release()
    assert client.post("/v1/agents", json=first).status_code == 401
    published = client.post("/v1/agents", json=first, headers=bearer(alice))
    assert published.status_code == 201, published.text
    detail = published.json()
    assert detail["owner"] == "alice"
    assert detail["digest"] == release_digest(AgentRelease.model_validate(first))
    assert client.post("/v1/agents", json=first, headers=bearer(bob)).status_code == 409
    assert (
        client.post(
            "/v1/agents/tiny-agent/versions", json=release("1.1.0"), headers=bearer(bob)
        ).status_code
        == 403
    )
    assert (
        client.post("/v1/agents/tiny-agent/versions", json=first, headers=bearer(alice)).status_code
        == 409
    )
    second = release("1.1.0")
    assert (
        client.post(
            "/v1/agents/tiny-agent/versions", json=second, headers=bearer(alice)
        ).status_code
        == 201
    )
    wrong_slug = release("1.2.0")
    wrong_slug["manifest"]["slug"] = "different"
    assert (
        client.post(
            "/v1/agents/tiny-agent/versions", json=wrong_slug, headers=bearer(alice)
        ).status_code
        == 422
    )
    public = client.get("/v1/agents/tiny-agent").json()
    assert public["latest_version"] == "1.1.0"
    assert len(public["versions"]) == 2
    assert public["downloads"] == 0
    assert client.get("/v1/agents/tiny-agent/versions/1.0.0").json() == detail
    assert client.get("/v1/agents/tiny-agent").json()["downloads"] == 0
    assert client.get("/v1/agents/tiny-agent/versions/1.0.0/download").json() == detail
    assert client.get("/v1/agents/tiny-agent").json()["downloads"] == 1
    found = client.get("/v1/agents?search=Tiny&model=test-model&license=Apache-2.0").json()
    assert found["total"] == 1
    assert found["items"][0]["downloads"] == 1
    assert client.get("/v1/agents?search=absent").json()["total"] == 0
    assert client.get("/v1/agents?model=other").json()["total"] == 0
    assert client.get("/v1/agents/missing").status_code == 404


def test_comments_reports_are_real_authenticated_and_self_reported(client):
    alice, bob = account(client), account(client, "bob")
    client.post("/v1/agents", json=release(), headers=bearer(alice))
    url = "/v1/agents/tiny-agent/versions/1.0.0"
    assert client.get(url + "/comments").json() == {"items": []}
    assert client.post(url + "/comments", json={"body": "Review"}).status_code == 401
    comment = client.post(url + "/comments", json={"body": "Review"}, headers=bearer(bob))
    assert comment.status_code == 201
    assert comment.json()["author"] == "bob"
    assert client.get(url + "/comments").json()["items"] == [comment.json()]
    report = {
        "model": "test-model",
        "benchmark_id": "coding",
        "passed": 3,
        "total": 4,
        "evidence_url": "https://example.com/results",
    }
    assert client.post(url + "/reports", json=report).status_code == 401
    response = client.post(url + "/reports", json=report, headers=bearer(bob))
    assert response.status_code == 201
    assert response.json()["self_reported"] is True
    assert client.get(url + "/reports").json()["items"] == [response.json()]
    assert (
        client.post(url + "/reports", json={**report, "passed": 5}, headers=bearer(bob)).status_code
        == 422
    )
    assert (
        client.post(
            url + "/reports", json={**report, "self_reported": False}, headers=bearer(bob)
        ).status_code
        == 422
    )
    assert client.get("/v1/agents/tiny-agent/versions/9.0.0/comments").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "../agent.py",
        "/agent.py",
        "C:/agent.py",
        "x\\agent.py",
        "x//agent.py",
        "x/./agent.py",
        "NUL.py",
        "x/COM1.txt",
        "x/.env",
        "x/.env.prod",
        "x/agent.py:stream",
        "x/agent.py.",
        "x/agent.py ",
        "x/.git/config",
        "id_rsa",
        "credentials.json",
        "agent.symlink",
    ],
)
def test_unsafe_paths_rejected(path):
    payload = release()
    payload["files"][path] = "content"
    with pytest.raises(ValidationError):
        AgentRelease.model_validate(payload)


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "runtime",
        "files",
        "file_bytes",
        "total_bytes",
        "secret",
        "unknown",
        "nul",
        "nontext",
        "private_url",
    ],
)
def test_source_limits_credentials_and_manifest_contract(change):
    payload = release()
    if change == "missing":
        payload["manifest"]["entrypoint"] = "missing.py"
    elif change == "runtime":
        payload["manifest"]["runtime"] = "node"
    elif change == "files":
        payload["files"].update({f"file{i}.txt": "x" for i in range(40)})
    elif change == "file_bytes":
        payload["files"]["file.txt"] = "é" * 65537
    elif change == "total_bytes":
        payload["files"].update({f"file{i}.txt": "x" * 131072 for i in range(8)})
    elif change == "secret":
        payload["files"]["agent.py"] = 'api_key = "sk-live-secret-token-123456789"'
    elif change == "unknown":
        payload["manifest"]["unrecognized"] = "bad"
    elif change == "nul":
        payload["files"]["agent.py"] = "a\x00b"
    elif change == "nontext":
        payload["files"]["link.py"] = {"symlink": "../../target"}
    else:
        payload["manifest"]["source_url"] = "https://127.0.0.1/private"
    with pytest.raises(ValidationError):
        AgentRelease.model_validate(payload)


def test_digest_is_validated_canonical_utf8_json_and_order_independent():
    validated = AgentRelease.model_validate(release())
    canonical = json.dumps(
        validated.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    assert release_digest(validated) == hashlib.sha256(canonical).hexdigest()
    reordered = copy.deepcopy(release())
    reordered["files"] = dict(reversed(list(reordered["files"].items())))
    assert release_digest(AgentRelease.model_validate(reordered)) == release_digest(validated)


def test_body_cap_and_short_password(client):
    assert (
        client.post(
            "/v1/auth/register", json={"username": "alice", "password": "short"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/agents",
            content=b"x" * (2 * 1024 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/path?token=secret",
        "https://example.com/path#fragment",
        "https://alice:password@example.com",
        "https://example.com:0",
        "https://example.com:99999",
        "https://example.com/a b",
        "http://example.com",
        "https://localhost/path",
        "https://[::1]/",
        "https://10.0.0.1/",
    ],
)
def test_public_source_and_evidence_urls_are_bounded_and_credential_free(url):
    from benchlab.hub_schemas import ReportInput

    payload = release()
    payload["manifest"]["source_url"] = url
    with pytest.raises(ValidationError):
        AgentRelease.model_validate(payload)
    with pytest.raises(ValidationError):
        ReportInput(model="test", benchmark_id="test", passed=1, total=1, evidence_url=url)


def test_password_model_never_serializes_plaintext():
    credentials = AuthCredentials(username="alice", password="private-password-123")
    assert "private-password-123" not in repr(credentials)
    assert "private-password-123" not in credentials.model_dump_json()


@pytest.mark.parametrize(
    "change", ["surrogate", "control", "case_collision", "directory_collision"]
)
def test_portability_and_unicode_edges_rejected(change):
    payload = release()
    if change == "surrogate":
        payload["manifest"]["name"] = "bad\ud800"
    elif change == "control":
        payload["files"]["agent.py"] = "binary\x01content"
    elif change == "case_collision":
        payload["files"]["AGENT.py"] = "hello"
    else:
        payload["files"]["agent.py/child.txt"] = "hello"
    with pytest.raises(ValidationError):
        AgentRelease.model_validate(payload)


def test_failed_download_and_preview_never_increment_downloads(client):
    alice = account(client)
    client.post("/v1/agents", json=release(), headers=bearer(alice))
    assert client.get("/v1/agents/tiny-agent/versions/9.0.0/download").status_code == 404
    assert client.head("/v1/agents/tiny-agent/versions/1.0.0/download").status_code == 405
    assert client.get("/v1/agents/tiny-agent").json()["downloads"] == 0


def test_hub_config_accepts_only_explicit_public_host_and_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_AGENTS_HUB_ALLOWED_HOSTS", "hub.example.com")
    monkeypatch.setenv("BENCH_AGENTS_HUB_ALLOWED_ORIGINS", "https://hub.example.com")
    with TestClient(create_hub_app(tmp_path), base_url="https://hub.example.com") as public:
        assert (
            public.get("/v1/health", headers={"Origin": "https://hub.example.com"}).status_code
            == 200
        )
        assert public.get("/v1/health", headers={"Host": "testserver"}).status_code == 400
    monkeypatch.setenv("BENCH_AGENTS_HUB_ALLOWED_HOSTS", "*")
    with pytest.raises(ValueError, match="explicit"):
        create_hub_app(tmp_path)


@pytest.mark.parametrize(
    "secret",
    [
        '{"api_key": "do-not-publish-secret"}',
        '{"password": "private-password"}',
        'Authorization = "Bearer private-access-token-value"',
    ],
)
def test_obvious_json_and_bearer_credentials_are_not_publishable(secret):
    payload = release()
    payload["files"]["config.json"] = secret
    with pytest.raises(ValidationError):
        AgentRelease.model_validate(payload)


def test_racing_publications_return_one_created_and_one_conflict(client):
    from concurrent.futures import ThreadPoolExecutor

    token = account(client)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(client.post, "/v1/agents", json=release(), headers=bearer(token))
            for _ in range(2)
        ]
    assert sorted(future.result().status_code for future in futures) == [201, 409]
    assert client.get("/v1/agents").json()["total"] == 1
    assert len(client.get("/v1/agents/tiny-agent").json()["versions"]) == 1
