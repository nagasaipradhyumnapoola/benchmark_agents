"""Local browser proxy and pinned source imports for a separate shared Agent Hub."""

from __future__ import annotations

import json
import re
from urllib.parse import quote, urlsplit

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from benchlab.hub_schemas import AgentRelease, ReportInput
from benchlab.imports import install_release
from benchlab.settings import environment_setting

COOKIE = "bench_agents_hub_session"


def hub_origin(value: str | None = None) -> str:
    value = value or environment_setting("HUB_URL") or "http://127.0.0.1:8100"
    try:
        parts = urlsplit(value)
        if (
            not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path not in {"", "/"}
        ):
            raise ValueError("Invalid registry URL")
        if parts.scheme != "https" and not (
            parts.scheme == "http" and parts.hostname in {"127.0.0.1", "localhost", "::1", "hub"}
        ):
            raise ValueError("Remote registries require HTTPS")
        _ = parts.port
    except ValueError:
        raise ValueError(
            "Hub URL must be an HTTPS origin, or a local HTTP origin, without credentials"
        ) from None
    return value.rstrip("/")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    password: SecretStr = Field(min_length=12, max_length=256)


class ImportInput(Input):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    version: str = Field(min_length=5, max_length=80, pattern=r"^[0-9A-Za-z.+-]+$")
    expected_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ShareInput(Input):
    run_id: str = Field(min_length=1, max_length=128)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    version: str = Field(min_length=5, max_length=80, pattern=r"^[0-9A-Za-z.+-]+$")
    evidence_url: str | None = Field(default=None, max_length=2048)


def _run_summary(store, run_id: str, registry_url: str) -> dict:
    run = store.get_run(run_id)
    if run["status"] != "completed" or run.get("demo"):
        raise ValueError("Share a completed, non-demo run of an imported Hub agent")
    manifest = run["manifest"]
    agent_id = manifest["system"].get("agent_id")
    if not agent_id:
        raise ValueError("This run did not use an imported Hub agent")
    try:
        source = store._get("hub_import", "import-" + agent_id)["source"]
    except KeyError:
        raise ValueError("This run did not use an imported Hub agent") from None
    if source["hub_url"] != registry_url:
        raise ValueError(
            "Connect to the registry this agent was imported from before sharing its run"
        )
    results = store.list_results(run_id)
    if not results:
        raise ValueError("This run has no task evidence to share")
    model = manifest.get("model") or {}
    return dict(
        slug=source["slug"],
        version=source["version"],
        run_id=run_id,
        model=model.get("model") or "native-product",
        benchmark_id=manifest["config"]["benchmark_id"],
        passed=sum(bool(row["passed"]) for row in results),
        total=len(results),
    )


def create_hub_router(store, *, hub_url: str | None = None, transport=None) -> APIRouter:
    router = APIRouter(prefix="/api/hub", tags=["agent-hub"])

    async def call(method: str, path: str, request: Request, body=None, *, authentication=False):
        headers = {}
        token = request.cookies.get(COOKIE)
        if token:
            headers["Authorization"] = "Bearer " + token
        try:
            async with httpx.AsyncClient(
                timeout=20, transport=transport, trust_env=False, follow_redirects=False
            ) as client:
                async with client.stream(
                    method,
                    hub_origin(hub_url) + "/v1/" + path,
                    params=dict(request.query_params),
                    json=body,
                    headers=headers,
                ) as response:
                    content = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        content.extend(chunk)
                        if len(content) > 3 * 1024 * 1024:
                            raise HTTPException(502, "The registry response exceeds the size limit")
        except (httpx.HTTPError, ValueError):
            raise HTTPException(
                503,
                "Agent Hub unavailable. Start it with uv run bench-agents hub, or configure BENCH_AGENTS_HUB_URL.",
            ) from None
        if not response.is_success:
            status = response.status_code if 400 <= response.status_code <= 599 else 502
            detail = {
                401: "Sign in to the Agent Hub again",
                403: "This account does not own the requested agent",
                404: "Hub agent or version not found",
                409: "Username, agent slug or immutable version already exists",
                422: "The registry rejected this input; check required fields and portable source paths",
                429: "Too many attempts; wait before trying again",
            }.get(status, "The registry request failed")
            if authentication:
                detail = (
                    "Account request failed; check the username and password"
                    if status in {401, 403}
                    else detail
                )
            raise HTTPException(status, detail)
        try:
            return json.loads(content)
        except ValueError:
            raise HTTPException(502, "The registry returned an invalid response") from None

    @router.get("/status")
    async def status(request: Request):
        try:
            await call("GET", "health", request)
            return dict(
                available=True,
                url=hub_origin(hub_url),
                message="Agent registry available; private benchmark execution stays in this workspace.",
            )
        except (HTTPException, ValueError):
            return dict(
                available=False,
                url=None,
                message="Start the registry with uv run bench-agents hub, or set BENCH_AGENTS_HUB_URL to your shared registry.",
            )

    @router.get("/auth/me")
    async def me(request: Request):
        if not request.cookies.get(COOKIE):
            return {"user": None}
        try:
            return await call("GET", "auth/me", request)
        except HTTPException as error:
            if error.status_code == 401:
                response = JSONResponse({"user": None})
                response.delete_cookie(COOKIE, path="/api/hub")
                return response
            raise

    @router.post("/auth/logout")
    async def logout(request: Request):
        try:
            if request.cookies.get(COOKIE):
                await call("POST", "auth/logout", request, {})
        except HTTPException:
            pass
        response = JSONResponse({"user": None})
        response.delete_cookie(COOKIE, path="/api/hub")
        return response

    @router.post("/auth/{action}")
    async def authenticate(action: str, credentials: Login, request: Request):
        if action not in {"register", "login"}:
            raise HTTPException(404, "Account action not found")
        data = await call(
            "POST",
            "auth/" + action,
            request,
            {"username": credentials.username, "password": credentials.password.get_secret_value()},
            authentication=True,
        )
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("token"), str)
            or not isinstance(data.get("user"), dict)
        ):
            raise HTTPException(502, "The registry returned an invalid account response")
        response = JSONResponse({"user": data["user"]})
        response.set_cookie(
            COOKIE,
            data["token"],
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="strict",
            max_age=7 * 86400,
            path="/api/hub",
        )
        return response

    @router.post("/import")
    async def import_agent(selection: ImportInput, request: Request):
        path = f"agents/{quote(selection.slug, safe='')}/versions/{quote(selection.version, safe='')}/download"
        data = await call("GET", path, request)
        if (
            data.get("manifest", {}).get("slug") != selection.slug
            or data.get("manifest", {}).get("version") != selection.version
        ):
            raise ValueError("Registry release identity differs from the selected version")
        return install_release(store, data, hub_origin(hub_url), selection.expected_digest)

    @router.get("/runs/{run_id}/share")
    def share_preview(run_id: str):
        return _run_summary(store, run_id, hub_origin(hub_url))

    @router.post("/share-run")
    async def share_run(selection: ShareInput, request: Request):
        summary = _run_summary(store, selection.run_id, hub_origin(hub_url))
        if summary["slug"] != selection.slug or summary["version"] != selection.version:
            raise ValueError("Selected release does not match the benchmarked imported agent")
        report = ReportInput.model_validate(
            {key: summary[key] for key in ("model", "benchmark_id", "passed", "total")}
            | {"evidence_url": selection.evidence_url}
        )
        return await call(
            "POST",
            f"agents/{quote(selection.slug, safe='')}/versions/{quote(selection.version, safe='')}/reports",
            request,
            report.model_dump(mode="json"),
        )

    @router.api_route("/{path:path}", methods=["GET", "POST"])
    async def registry(path: str, request: Request):
        if not re.fullmatch(
            r"agents(?:/[a-z0-9-]+(?:/versions(?:/[0-9A-Za-z.+-]+(?:/(?:download|comments|reports))?)?)?)?",
            path,
        ):
            raise HTTPException(404, "Registry route not found")
        body = None
        if request.method == "POST":
            try:
                body = await request.json()
            except ValueError:
                raise HTTPException(422, "Send a JSON object") from None
            if path == "agents" or path.endswith("/versions"):
                body = AgentRelease.model_validate(body).model_dump(mode="json")
        return await call(request.method, path, request, body)

    return router
