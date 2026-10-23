"""Bounded, disposable evidence probes; success means audit ran, never launch approval.

No real provider, uploaded program, model, live registry, or Docker daemon is used.
The observations intentionally describe current gaps rather than passing security gates.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from rich.console import Console
from typer.testing import CliRunner

from benchlab.api import create_app
from benchlab.cli import app as cli
from benchlab.hub import create_hub_app
from benchlab.hub_client import create_hub_router
from benchlab.hub_schemas import AgentRelease, release_digest
from benchlab.imports import install_release
from benchlab.sdk import Laboratory
from benchlab.store import Store
from benchlab.terminal import say
from benchlab.terminal_ui import render_banner, render_menu

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/launch-audit"


def release(name="Audit fixture", slug="audit-fixture"):
    return AgentRelease.model_validate(
        {
            "manifest": {
                "slug": slug,
                "name": name,
                "summary": "Disposable audit fixture, not a published agent",
                "readme": "Never executed",
                "version": "1.0.0",
                "license": "MIT",
                "runtime": "python",
                "entrypoint": "agent.py",
            },
            "files": {"agent.py": "print('not executed')\n"},
        }
    )


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    parent = ROOT / ".bench-agents/launch-audit"
    parent.mkdir(parents=True, exist_ok=True)
    observations = {}
    with tempfile.TemporaryDirectory(prefix="probes-", dir=parent) as directory:
        work = Path(directory)
        lab_app = create_app(work / "private-lab", run_worker=False)
        with TestClient(lab_app) as client:
            saved = client.post(
                "/api/models",
                json={
                    "id": "audit-owned-model",
                    "name": "Private fixture",
                    "adapter": "demo",
                    "model": "reference",
                    "demo": True,
                },
            )
            listed = client.get("/api/models")
            deleted = client.delete("/api/models/audit-owned-model")
            observations["unauthenticated_private_api"] = {
                "create": saved.status_code,
                "list": listed.status_code,
                "delete": deleted.status_code,
                "finding_confirmed": saved.status_code == 201
                and listed.status_code == 200
                and deleted.status_code == 204,
                "scope": "Local API has no identity/tenant boundary; public exposure is a deployment blocker",
            }
            large_body = json.dumps(
                {
                    "name": "Chunked audit",
                    "systems": [
                        {
                            "model_id": "fixture",
                            "parameters": {"padding": "x" * (2 * 1024 * 1024 + 1024)},
                        }
                    ],
                }
            ).encode()
            chunked = client.post(
                "/api/import",
                content=iter([large_body]),
                headers={"Content-Type": "application/json"},
            )
            observations["chunked_lab_body_limit"] = {
                "bytes": len(large_body),
                "content_length_present": "content-length" in chunked.request.headers,
                "status": chunked.status_code,
                "finding_confirmed": chunked.status_code == 200
                and "content-length" not in chunked.request.headers,
            }
            del large_body, chunked

            from benchlab.adapters import registry

            captured = []

            def provider(request):
                captured.append(
                    {
                        "loopback_target": request.url.host == "127.0.0.1",
                        "dummy_credential_forwarded": request.headers.get("authorization")
                        == "Bearer audit-dummy-provider-value",
                    }
                )
                return httpx.Response(200, json={"data": [{"id": "audit-model"}]})

            with (
                patch.dict(
                    "os.environ", {"AUDIT_PROVIDER_CREDENTIAL": "audit-dummy-provider-value"}
                ),
                patch.object(
                    registry,
                    "http_client",
                    side_effect=lambda **kwargs: httpx.AsyncClient(
                        transport=httpx.MockTransport(provider), **kwargs
                    ),
                ),
            ):
                client.post(
                    "/api/models",
                    json={
                        "id": "audit-probe-model",
                        "name": "Probe fixture",
                        "adapter": "openai-compatible",
                        "model": "audit-model",
                        "base_url": "http://127.0.0.1:17999",
                        "api_key_env": "AUDIT_PROVIDER_CREDENTIAL",
                    },
                )
                probe = client.post("/api/models/audit-probe-model/probe")
            observations["caller_selected_target_and_environment_reference"] = {
                "status": probe.status_code,
                "requests": captured,
                "finding_confirmed": bool(captured) and all(captured[0].values()),
                "network": "MockTransport only; no network connection or real credential",
            }

        hub = create_hub_app(work / "hub")
        with TestClient(hub) as client:
            denied = [
                client.post(
                    "/v1/auth/login",
                    json={"username": "no-such-user", "password": "dummy-audit-password"},
                ).status_code
                for _ in range(11)
            ]
            second = create_hub_app(work / "hub")
            with TestClient(second) as other:
                second_worker = other.post(
                    "/v1/auth/login",
                    json={"username": "no-such-user", "password": "dummy-audit-password"},
                ).status_code
            observations["authentication_throttle_scope"] = {
                "single_peer_first_ten": denied[:10],
                "single_peer_eleventh": denied[10],
                "fresh_worker_same_database": second_worker,
                "finding_confirmed": denied[:10] == [401] * 10
                and denied[10] == 429
                and second_worker == 401,
                "scope": "Per-process peer limiter; shared egress collapses users and worker replicas do not share counters",
            }
            oversized = client.post(
                "/v1/auth/login",
                content=iter([b" " * (2 * 1024 * 1024 + 1)]),
                headers={"Content-Type": "application/json"},
            )
            observations["hub_streaming_body_limit_positive_control"] = {
                "status": oversized.status_code,
                "protection_confirmed": oversized.status_code == 413,
            }

        valid = release(name="N" * 120, slug="valid-name-too-long-after-import")
        store = hub.state.hub_store
        account = store.register("audit-owner", "dummy-audit-password")
        published = store.publish(valid, account["user"]["username"])
        try:
            install_release(
                Store(work / "name-import"),
                published,
                "http://127.0.0.1:8100",
                release_digest(valid),
            )
            failed_fields = []
        except ValidationError as error:
            failed_fields = [list(item["loc"]) for item in error.errors()]
        observations["published_release_import_name_contract"] = {
            "published_name_length": len(valid.manifest.name),
            "import_display_name_length": len(valid.manifest.name + " " + valid.manifest.version),
            "rejected_fields": failed_fields,
            "finding_confirmed": ["name"] in failed_fields,
        }
        argument_release = release(slug="valid-forty-arguments")
        argument_release.manifest.args = ["fixture"] * 40
        argument_published = store.publish(argument_release, "audit-owner")
        try:
            install_release(
                Store(work / "args-import"),
                argument_published,
                "http://127.0.0.1:8100",
                release_digest(argument_release),
            )
            argument_fields = []
        except ValidationError as error:
            argument_fields = [list(item["loc"]) for item in error.errors()]
        observations["published_release_import_argument_contract"] = {
            "published_args": 40,
            "import_args_including_entrypoint": 41,
            "rejected_fields": argument_fields,
            "finding_confirmed": ["args"] in argument_fields,
        }

        unsafe_name = "Audit name\x1b]52;c;YXVkaXQ=\x07"
        terminal_item = release(name=unsafe_name, slug="terminal-control-fixture")
        imported = install_release(
            Store(work / "terminal-import"),
            {**terminal_item.model_dump(mode="json"), "digest": release_digest(terminal_item)},
            "http://127.0.0.1:8100",
            release_digest(terminal_item),
        )

        class Tty(io.StringIO):
            def isatty(self):
                return True

        terminal = Tty()
        with contextlib.redirect_stdout(terminal):
            say(imported["agent"]["name"])
        observations["terminal_control_sequence"] = {
            "publisher_name_accepted": True,
            "osc52_reaches_simulated_tty": "\x1b]52;" in terminal.getvalue(),
            "finding_confirmed": "\x1b]52;" in terminal.getvalue(),
            "safety": "Captured in StringIO; never emitted to an actual terminal or clipboard",
        }

        template = release(name="Catalog fixture", slug="catalog-template").model_dump(mode="json")
        template["manifest"].update(
            summary="S" * 950, recommended_models=[f"provider-{i}/" + "m" * 175 for i in range(20)]
        )
        AgentRelease.model_validate(template)
        with store.connection(write=True) as db:
            for number in range(800):
                slug = f"catalog-audit-{number:04d}"
                template["manifest"]["slug"] = slug
                db.execute(
                    "INSERT INTO agents VALUES (?, ?, ?, 0, ?)",
                    (slug, "audit-owner", "1.0.0", "2026-10-23T00:00:00Z"),
                )
                db.execute(
                    "INSERT INTO versions VALUES (?, ?, ?, ?, ?)",
                    (slug, "1.0.0", json.dumps(template), "a" * 64, "2026-10-23T00:00:00Z"),
                )
        start = time.perf_counter()
        catalog = store.list_agents()
        duration = time.perf_counter() - start
        body = json.dumps(catalog).encode()
        proxy = FastAPI()
        proxy.include_router(
            create_hub_router(
                Store(work / "catalog-proxy"),
                transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body)),
            )
        )
        with TestClient(proxy) as client:
            response = client.get("/api/hub/agents")
        observations["catalog_exceeds_own_proxy_limit"] = {
            "synthetic_agents": catalog["total"],
            "returned_agents": len(catalog["items"]),
            "page_size": catalog.get("page_size"),
            "response_bytes": len(body),
            "list_seconds_single_local_sample": round(duration, 4),
            "proxy_status": response.status_code,
            "finding_confirmed": len(body) > 3 * 1024 * 1024 and response.status_code == 502,
            "fixture_note": "800 valid-shaped synthetic releases inserted transactionally; no public traffic or million-user load test",
        }

        runner = CliRunner()
        cli_env = {"BENCH_AGENTS_DATA_DIR": str(work / "terminal-session")}
        started = runner.invoke(cli, ["terminal"], input="0\n", env=cli_env)
        command = runner.invoke(cli, ["--help"])
        observations["terminal_entry_exit"] = {
            "exit_code": started.exit_code,
            "help_exit_code": command.exit_code,
            "menu_matrix_present": "multiple models" in started.stdout.lower(),
        }
        laboratory = Laboratory(work / "terminal-render")
        for width in (40, 96):
            text = io.StringIO()
            console = Console(file=text, width=width, color_system=None, highlight=False)
            render_banner(console, laboratory)
            render_menu(console, laboratory)
            (EVIDENCE / f"terminal-{width}.txt").write_text(
                "\n".join(line.rstrip() for line in text.getvalue().splitlines()).rstrip() + "\n",
                encoding="utf-8",
            )

        async def provider_response_probe():
            from benchlab.adapters import registry
            from benchlab.schemas import ExperimentConfig, ModelConfig, TaskDefinition

            chunks_read = []

            class Payload(httpx.AsyncByteStream):
                async def __aiter__(self):
                    for _ in range(20):
                        chunks_read.append(1)
                        yield b"x" * 65536

            transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=Payload()))
            with patch.object(
                registry,
                "http_client",
                side_effect=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
            ):
                try:
                    await registry._provider(
                        ModelConfig(
                            name="Audit",
                            model="audit",
                            adapter="openai-compatible",
                            base_url="http://127.0.0.1:17999/v1",
                        ),
                        TaskDefinition(
                            id="audit",
                            name="Audit",
                            category="reasoning",
                            prompt="fixture",
                            verifier="exact",
                            expected="x",
                        ),
                        ExperimentConfig(name="Audit", systems=[{"model_id": "fixture"}]),
                        {},
                    )
                except ValueError:
                    pass
            return {
                "chunks_received_before_rejection": len(chunks_read),
                "fixture_total_chunks": 20,
                "bytes_received": len(chunks_read) * 65536,
                "finding_confirmed": len(chunks_read) == 20,
                "network": "MockTransport only",
            }

        observations["provider_limit_after_buffering"] = asyncio.run(provider_response_probe())

    payload = {
        "date": datetime.now(UTC).isoformat(),
        "audited_revision": "working-tree follow-up to baseline f5e9b989",
        "meaning": "Observations confirm launch gaps, not passing production acceptance tests",
        "live_workspace_untouched": True,
        "temporary_probe_directories_removed": True,
        "real_credentials_used": False,
        "uploaded_code_executed": False,
        "observations": observations,
    }
    (EVIDENCE / "probes-current.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
