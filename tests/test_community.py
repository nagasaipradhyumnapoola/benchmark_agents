import json
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from benchlab.store import Store


@pytest.fixture
def client(tmp_path):
    from benchlab.community import build_community_router

    app = FastAPI()
    app.include_router(build_community_router(Store(tmp_path)))
    return TestClient(app)


def proposal(**changes):
    return {
        "kind": "agent",
        "title": "A small open agent",
        "description": "Try this agent on repository tasks.",
        "source_url": "https://github.com/example/agent",
        "license": "Apache-2.0",
        "recommended_models": ["provider/exact-model-v1"],
        **changes,
    }


def test_empty_catalog_and_persisted_draft_export(client, tmp_path):
    listing = client.get("/api/community").json()
    assert listing["published"] == []
    assert listing["drafts"] == []
    response = client.post("/api/community", json=proposal())
    assert response.status_code == 201, response.text
    draft = response.json()
    assert draft["publication_status"] == "local_draft"
    assert draft["verification_status"] == "unverified"
    assert Store(tmp_path)._get("community_proposal", draft["id"])["title"] == "A small open agent"
    assert client.get("/api/community").json()["drafts"][0]["id"] == draft["id"]
    share = urlsplit(draft["share_url"])
    assert share.netloc == "github.com"
    assert share.path == "/nagasaipradhyumnapoola/benchmark_agents/issues/new"
    body = parse_qs(share.query)["body"][0]
    assert "provider/exact-model-v1" in body
    assert "unverified" in body
    assert draft["share_requires_paste"] is False
    assert len(draft["share_url"].encode("ascii")) <= 7000
    export = client.get(f"/api/community/{draft['id']}/export")
    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    assert export.json()["proposal"]["recommended_models"] == ["provider/exact-model-v1"]
    assert str(tmp_path) not in export.text
    assert "share_url" not in export.text
    assert client.get("/api/community/missing/export").status_code == 404


def test_maximum_unicode_draft_uses_bounded_link_without_losing_review_or_export(client):
    payload = proposal(
        title="界" * 120,
        description="界" * 1500,
        author_name="界" * 80,
        license="界" * 100,
        recommended_models=["界" * 200 for _ in range(12)],
        benchmark_ids=["界" * 200 for _ in range(12)],
    )
    response = client.post("/api/community", json=payload)
    assert response.status_code == 201, response.text
    draft = response.json()
    assert len(draft["share_url"].encode("ascii")) <= 7000
    assert draft["share_requires_paste"] is True
    query = parse_qs(urlsplit(draft["share_url"]).query)
    assert query["title"] == ["[Community] " + payload["title"]]
    assert "body" not in query
    assert "界" * 1500 in draft["share_body"]
    exported = client.get(f"/api/community/{draft['id']}/export").json()["proposal"]
    for field, value in payload.items():
        assert exported[field] == value


@pytest.mark.parametrize("kind", ["pairing", "benchmark"])
def test_non_agent_suggestions_need_no_source_or_license(client, kind):
    payload = proposal(kind=kind, source_url=None, license=None)
    assert client.post("/api/community", json=payload).status_code == 201


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "model"},
        {"title": "   "},
        {"description": ""},
        {"source_url": None},
        {"license": None},
        {"license": "  "},
        {"api_key": "secret"},
        {"config": {"executable": "cmd"}},
        {"env_allowlist": ["KEY"]},
        {"api_key_env": "BENCH_AGENTS_SESSION_private"},
        {"description": "Use sk-proj-testsecret1234567890"},
        {"description": "Authorization: Bearer secret-token"},
        {"recommended_models": ["BENCH_AGENTS_SESSION_private"]},
        {"recommended_models": [" "]},
        {"recommended_models": "model"},
        {"title": 17},
        {"recommended_models": [42]},
    ],
)
def test_invalid_or_secret_bearing_proposals_are_not_persisted(client, changes):
    response = client.post("/api/community", json=proposal(**changes))
    assert response.status_code == 422
    assert client.get("/api/community").json()["drafts"] == []


def test_validation_errors_do_not_echo_rejected_credentials(client):
    response = client.post("/api/community", json=proposal(api_key="private-credential-value"))
    assert response.status_code == 422
    assert "private-credential-value" not in response.text
    response = client.post("/api/community", json=proposal(description="Bearer private-value"))
    assert response.status_code == 422
    assert "private-value" not in response.text


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///tmp/code",
        "http://github.com/example/agent",
        "https://user:pass@github.com/example/agent",
        "https://github.com/x?token=secret",
        "https://localhost/code",
        "https://127.0.0.1/code",
        "https://10.0.0.1/code",
        "https://[::1]/code",
        "https://169.254.169.254/code",
        "https://server.local/code",
        "https://github.com/x#token=secret",
        "https://2130706433/code",
    ],
)
@pytest.mark.parametrize("field", ["source_url", "evidence_url"])
def test_only_public_credential_free_https_links_are_accepted(client, field, url):
    assert client.post("/api/community", json=proposal(**{field: url})).status_code == 422


def test_published_catalog_is_validated_and_unverified(client, tmp_path, monkeypatch):
    import benchlab.community as community

    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps([{"id": "agent-one", **proposal()}]), encoding="utf-8")
    monkeypatch.setattr(community, "CATALOG_PATH", catalog)
    item = client.get("/api/community").json()["published"][0]
    assert item["verification_status"] == "unverified"
    assert item["publication_status"] == "published"
    catalog.write_text(json.dumps([{"id": "bad", **proposal(), "api_key": "secret"}]))
    response = client.get("/api/community")
    assert response.status_code == 503
    assert "secret" not in response.text
    catalog.write_text("not JSON")
    assert client.get("/api/community").status_code == 503
    catalog.unlink()
    assert client.get("/api/community").status_code == 503
