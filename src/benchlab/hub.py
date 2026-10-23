"""Independent Agent Hub HTTP service. No model, credential or execution API."""

import os
import threading
import time
from collections import OrderedDict, deque
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from benchlab.hub_schemas import AgentRelease, AuthCredentials, CommentInput, ReportInput
from benchlab.hub_store import HubError, HubStore
from benchlab.policies import PUBLICATION_RULES_HEADER, PUBLICATION_RULES_VERSION

MAX_REQUEST_BYTES = 2 * 1024 * 1024


class HubSecurityMiddleware:
    """Bound streamed bodies before JSON decoding and fail closed on foreign origins."""

    def __init__(self, app: ASGIApp, allowed_origins: set[str]):
        self.app = app
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def safe_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                        (b"cache-control", b"no-store"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        headers = scope.get("headers", [])
        origins = [value.decode("latin-1") for key, value in headers if key.lower() == b"origin"]
        if len(origins) > 1 or (origins and origins[0] not in self.allowed_origins):
            await JSONResponse({"detail": "Origin is not allowed"}, status_code=403)(
                scope, receive, safe_send
            )
            return
        lengths = [value for key, value in headers if key.lower() == b"content-length"]
        try:
            if len(lengths) > 1 or (
                lengths and (int(lengths[0]) < 0 or int(lengths[0]) > MAX_REQUEST_BYTES)
            ):
                raise ValueError
        except ValueError:
            await JSONResponse({"detail": "Request body exceeds the 2 MiB limit"}, status_code=413)(
                scope, receive, safe_send
            )
            return
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > MAX_REQUEST_BYTES:
                await JSONResponse(
                    {"detail": "Request body exceeds the 2 MiB limit"}, status_code=413
                )(scope, receive, safe_send)
                return
            chunks.append(body)
            if not message.get("more_body", False):
                break
        supplied = False

        async def replay() -> Message:
            nonlocal supplied
            if not supplied:
                supplied = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, safe_send)


class AuthThrottle:
    """Bound memory and auth hashing load per peer, without trusting forwarded IPs."""

    def __init__(self) -> None:
        self.attempts: OrderedDict[str, deque[float]] = OrderedDict()
        self.lock = threading.Lock()

    def check(self, peer: str) -> None:
        now = time.monotonic()
        with self.lock:
            recent = self.attempts.setdefault(peer, deque())
            self.attempts.move_to_end(peer)
            while recent and recent[0] <= now - 60:
                recent.popleft()
            if len(recent) >= 10:
                raise HTTPException(
                    429,
                    "Too many authentication attempts; try again later",
                    headers={"Retry-After": "60"},
                )
            recent.append(now)
            while len(self.attempts) > 4096:
                self.attempts.popitem(last=False)


def create_hub_app(data_dir: Path | None = None) -> FastAPI:
    """Create an empty self-hosted registry backed only by its own hub.sqlite3."""
    directory = data_dir or Path(os.environ.get("BENCH_AGENTS_HUB_DATA_DIR", ".bench-agents/hub"))
    ttl = int(os.environ.get("BENCH_AGENTS_HUB_SESSION_TTL_SECONDS", str(7 * 24 * 3600)))
    if not 300 <= ttl <= 30 * 24 * 3600:
        raise ValueError("Hub session TTL must be between 300 and 2592000 seconds")
    store = HubStore(directory, session_ttl=ttl)
    throttle = AuthThrottle()
    app = FastAPI(title="Agent Hub", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.hub_store = store
    origins = {
        origin.strip()
        for origin in os.environ.get(
            "BENCH_AGENTS_HUB_ALLOWED_ORIGINS",
            "http://127.0.0.1:8100,http://localhost:8100,http://127.0.0.1:3000,http://localhost:3000",
        ).split(",")
        if origin.strip()
    }
    hosts = [
        host.strip()
        for host in os.environ.get(
            "BENCH_AGENTS_HUB_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver"
        ).split(",")
        if host.strip()
    ]
    if not hosts or "*" in hosts or "*" in origins:
        raise ValueError("Configure explicit Hub hosts and origins; wildcards are not allowed")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts, www_redirect=False)
    app.add_middleware(HubSecurityMiddleware, allowed_origins=origins)

    @app.exception_handler(HubError)
    async def hub_error(request: Request, exc: HubError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {
                "detail": [
                    {"type": error["type"], "loc": error["loc"], "msg": error["msg"]}
                    for error in exc.errors()
                ]
            },
            status_code=422,
        )

    def token_for(request: Request) -> str:
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token or len(token) > 200:
            raise HTTPException(
                401, "Authentication required", headers={"WWW-Authenticate": "Bearer"}
            )
        return token

    def authenticated(request: Request) -> str:
        return store.user_for_token(token_for(request))

    def check_auth_attempt(request: Request) -> None:
        throttle.check(request.client.host if request.client else "unknown")

    def acknowledged_rules(request: Request) -> str:
        if request.headers.get(PUBLICATION_RULES_HEADER) != PUBLICATION_RULES_VERSION:
            raise HTTPException(
                428, "Review and acknowledge the current publication rules before publishing"
            )
        return PUBLICATION_RULES_VERSION

    @app.get("/v1/policies")
    def policies() -> dict:
        return {
            "publication_rules_version": PUBLICATION_RULES_VERSION,
            "publication_acknowledgement_required": True,
        }

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/auth/register", status_code=201, dependencies=[Depends(check_auth_attempt)])
    def register(credentials: AuthCredentials) -> dict[str, Any]:
        return store.register(credentials.username, credentials.password.get_secret_value())

    @app.post("/v1/auth/login", dependencies=[Depends(check_auth_attempt)])
    def login(credentials: AuthCredentials) -> dict[str, Any]:
        return store.login(credentials.username, credentials.password.get_secret_value())

    @app.get("/v1/auth/me")
    def me(username: Annotated[str, Depends(authenticated)]) -> dict[str, Any]:
        return {"user": {"username": username}}

    @app.post("/v1/auth/logout")
    def logout(
        request: Request, username: Annotated[str, Depends(authenticated)]
    ) -> dict[str, str]:
        store.logout(token_for(request))
        return {"status": "ok"}

    @app.get("/v1/agents")
    def list_agents(
        search: Annotated[str, Query(max_length=200)] = "",
        model: Annotated[str, Query(max_length=200)] = "",
        license: Annotated[str, Query(max_length=100)] = "",
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=24)] = 24,
    ) -> dict[str, Any]:
        return store.list_agents(search, model, license, page=page, page_size=page_size)

    @app.post("/v1/agents", status_code=201)
    def publish(
        release: AgentRelease,
        username: Annotated[str, Depends(authenticated)],
        rules: Annotated[str, Depends(acknowledged_rules)],
    ) -> dict[str, Any]:
        return store.publish(release, username, rules_version=rules)

    @app.get("/v1/agents/{slug}")
    def agent(slug: str) -> dict[str, Any]:
        return store.agent(slug)

    @app.post("/v1/agents/{slug}/versions", status_code=201)
    def publish_version(
        slug: str,
        release: AgentRelease,
        username: Annotated[str, Depends(authenticated)],
        rules: Annotated[str, Depends(acknowledged_rules)],
    ) -> dict[str, Any]:
        return store.publish(release, username, existing_slug=slug, rules_version=rules)

    @app.get("/v1/agents/{slug}/versions/{version}")
    def version(slug: str, version: str) -> dict[str, Any]:
        return store.version(slug, version)

    @app.get("/v1/agents/{slug}/versions/{version}/download")
    def download(slug: str, version: str) -> dict[str, Any]:
        return store.version(slug, version, download=True)

    @app.get("/v1/agents/{slug}/versions/{version}/comments")
    def comments(slug: str, version: str) -> dict[str, Any]:
        return store.comments(slug, version)

    @app.post("/v1/agents/{slug}/versions/{version}/comments", status_code=201)
    def comment(
        slug: str,
        version: str,
        comment: CommentInput,
        username: Annotated[str, Depends(authenticated)],
    ) -> dict[str, Any]:
        return store.comments(slug, version, author=username, body=comment.body)

    @app.get("/v1/agents/{slug}/versions/{version}/reports")
    def reports(slug: str, version: str) -> dict[str, Any]:
        return store.reports(slug, version)

    @app.post("/v1/agents/{slug}/versions/{version}/reports", status_code=201)
    def report(
        slug: str,
        version: str,
        report: ReportInput,
        username: Annotated[str, Depends(authenticated)],
    ) -> dict[str, Any]:
        return store.reports(slug, version, author=username, report=report)

    return app


def app_factory() -> FastAPI:
    return create_hub_app()
