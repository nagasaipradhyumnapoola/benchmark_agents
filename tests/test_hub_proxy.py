import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from benchlab.store import Store


def test_registry_response_is_bounded(tmp_path):
    from benchlab.hub_client import create_hub_router

    app = FastAPI()
    app.include_router(
        create_hub_router(
            Store(tmp_path),
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=b" " * (3 * 1024 * 1024 + 1))
            ),
        )
    )
    with TestClient(app) as client:
        response = client.get("/api/hub/agents")
        assert response.status_code == 502
        assert "size limit" in response.json()["detail"]


def test_results_cannot_be_shared_to_another_registry():
    from benchlab.hub_client import _run_summary

    class ImportedRun:
        def get_run(self, run_id):
            return {
                "status": "completed",
                "demo": False,
                "manifest": {"system": {"agent_id": "hub-agent"}},
            }

        def _get(self, kind, record_id):
            return {
                "source": {
                    "hub_url": "https://original.example",
                    "slug": "agent",
                    "version": "1.0.0",
                }
            }

    with pytest.raises(ValueError, match="registry this agent was imported from"):
        _run_summary(ImportedRun(), "run", "https://another.example")


def test_login_uses_http_only_cookie_and_never_returns_token_to_javascript(tmp_path):
    from benchlab.hub_client import create_hub_router

    seen = []

    def upstream(request):
        seen.append(request)
        if request.url.path.endswith("/login"):
            return httpx.Response(
                200, json={"token": "opaque-session-test-value", "user": {"username": "author"}}
            )
        if request.url.path.endswith("/logout"):
            return httpx.Response(200, json={"ok": True})
        assert request.headers.get("Authorization") == "Bearer opaque-session-test-value"
        return httpx.Response(200, json={"user": {"username": "author"}})

    app = FastAPI()
    app.include_router(
        create_hub_router(
            Store(tmp_path),
            hub_url="http://127.0.0.1:8100",
            transport=httpx.MockTransport(upstream),
        )
    )
    with TestClient(app) as client:
        assert client.get("/api/hub/auth/me").json() == {"user": None}
        response = client.post(
            "/api/hub/auth/login",
            json={"username": "author", "password": "test-password-never-persist"},
        )
        assert response.status_code == 200
        assert response.json() == {"user": {"username": "author"}}
        assert "opaque-session-test-value" not in response.text
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=strict" in response.headers["set-cookie"].lower()
        assert client.get("/api/hub/auth/me").json()["user"]["username"] == "author"
        assert client.post("/api/hub/auth/logout", json={}).status_code == 200
        assert client.get("/api/hub/auth/me").json() == {"user": None}


def test_unavailable_hub_is_actionable_and_unknown_proxy_paths_are_blocked(tmp_path):
    from benchlab.hub_client import create_hub_router

    def upstream(request):
        raise httpx.ConnectError("private upstream details", request=request)

    app = FastAPI()
    app.include_router(
        create_hub_router(
            Store(tmp_path),
            hub_url="http://127.0.0.1:8100",
            transport=httpx.MockTransport(upstream),
        )
    )
    with TestClient(app) as client:
        status = client.get("/api/hub/status").json()
        assert status["available"] is False
        assert "bench-agents hub" in status["message"]
        assert client.get("/api/hub/private-administration").status_code == 404
        response = client.post(
            "/api/hub/auth/login",
            json={"username": "author", "password": "test-password-never-persist"},
        )
        assert response.status_code == 503
        assert "test-password-never-persist" not in response.text
        assert "private upstream details" not in response.text
