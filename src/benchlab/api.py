"""Loopback-first REST API with a durable background worker."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import ValidationError

from benchlab import __version__
from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig
from benchlab.service import demo_config, diagnostics, install_demo_inventory
from benchlab.settings import Settings, environment_setting, redact
from benchlab.telemetry import FAILURE_CATEGORIES, metric_registry

logger = logging.getLogger("benchlab.api")


def create_app(data_dir: Path | None = None, *, run_worker: bool = True) -> FastAPI:
    from benchlab.engine import Engine
    from benchlab.store import Store

    settings = Settings.from_env()
    store = Store(data_dir or settings.data_dir)
    engine = Engine(store)

    async def worker() -> None:
        while True:
            try:
                worked = await engine.work_once()
                if not worked:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.error("worker_error %s", redact(str(error)))
                await asyncio.sleep(0.5)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if run_worker:
            engine.recover()
        application.state.store = store
        application.state.engine = engine
        job = asyncio.create_task(worker()) if run_worker else None
        yield
        if job:
            job.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await job
            engine.recover()

    application = FastAPI(title="Bench Agents API", version=__version__, lifespan=lifespan)
    application.state.store = store
    application.state.engine = engine

    @application.middleware("http")
    async def protect_local_api(request: Request, call_next):
        host = urlsplit("//" + request.headers.get("host", "")).hostname
        if host not in {"localhost", "127.0.0.1", "::1", "testserver", "api"}:
            return JSONResponse({"detail": "Invalid local Host"}, status_code=400)
        origin = request.headers.get("origin")
        origins = {
            f"http://{hostname}:{port}"
            for hostname in ("localhost", "127.0.0.1")
            for port in (3000, 8000)
        }
        trusted_origin = environment_setting("WEB_ORIGIN")
        if trusted_origin:
            origins.add(trusted_origin)
        if origin and origin not in origins:
            return JSONResponse(
                {"detail": "Foreign Origin denied by local laboratory"}, status_code=403
            )
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > 2 * 1024 * 1024:
                    return JSONResponse({"detail": "Request body exceeds 2 MiB"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(KeyError)
    async def not_found(_request: Request, _error: KeyError):
        return JSONResponse({"detail": "Resource not found"}, status_code=404)

    @application.exception_handler(ValueError)
    async def invalid(_request: Request, error: ValueError):
        return JSONResponse({"detail": redact(str(error))}, status_code=422)

    @application.exception_handler(RequestValidationError)
    @application.exception_handler(ValidationError)
    async def invalid_schema(_request: Request, error: Any):
        # Validation errors normally include raw submitted inputs. Keep only field/reason.
        messages = [
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        ]
        return JSONResponse({"detail": redact("; ".join(messages))}, status_code=422)

    @application.exception_handler(PermissionError)
    async def forbidden(_request: Request, error: PermissionError):
        return JSONResponse({"detail": redact(str(error))}, status_code=403)

    def authorize_config(config: ExperimentConfig) -> None:
        if config.allow_host_process and not Settings.from_env().allow_host_process:
            raise HTTPException(
                403,
                "Host process execution requires BENCH_AGENTS_ALLOW_HOST_PROCESS=1 on the server and explicit experiment consent",
            )

    @application.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @application.get("/api/overview")
    def overview() -> dict:
        from benchlab.analysis import summarize

        experiments = sorted(
            store.list_experiments(), key=lambda row: row["created_at"], reverse=True
        )
        runs = sorted(
            store.list_runs(), key=lambda row: row["manifest"]["created_at"], reverse=True
        )
        results = [result for run in runs for result in store.list_results(run["id"])]
        return {
            "experiments": experiments,
            "runs": runs,
            "models": store.list_models(),
            "agents": store.list_agents(),
            "metrics": summarize(results),
            "recent_failures": [
                dict(result, run_id=run["id"])
                for run in runs
                for result in store.list_results(run["id"])
                if not result["passed"]
            ][:20],
        }

    @application.get("/api/models")
    def models() -> list[dict]:
        return store.list_models()

    @application.post("/api/models", status_code=201)
    def add_model(config: ModelConfig) -> dict:
        return store.save_model(config)

    @application.get("/api/models/{model_id}")
    def model_detail(model_id: str) -> dict:
        return store.get_model(model_id)

    @application.delete("/api/models/{model_id}", status_code=204)
    def delete_model(model_id: str) -> Response:
        store.delete_model(model_id)
        return Response(status_code=204)

    @application.post("/api/models/{model_id}/probe")
    async def model_probe(model_id: str) -> dict:
        from benchlab.adapters.registry import probe_model

        row = store.get_model(model_id)
        return (await probe_model(ModelConfig.model_validate(row.get("config", row)))).model_dump()

    @application.get("/api/agents")
    def agents() -> list[dict]:
        return store.list_agents()

    @application.post("/api/agents", status_code=201)
    def add_agent(config: AgentConfig) -> dict:
        return store.save_agent(config)

    @application.get("/api/agents/{agent_id}")
    def agent_detail(agent_id: str) -> dict:
        return store.get_agent(agent_id)

    @application.delete("/api/agents/{agent_id}", status_code=204)
    def delete_agent(agent_id: str) -> Response:
        store.delete_agent(agent_id)
        return Response(status_code=204)

    @application.post("/api/agents/{agent_id}/probe")
    async def agent_probe(agent_id: str) -> dict:
        from benchlab.adapters.registry import probe_agent

        row = store.get_agent(agent_id)
        return (await probe_agent(AgentConfig.model_validate(row.get("config", row)))).model_dump()

    @application.get("/api/benchmarks")
    def benchmarks() -> list[dict]:
        from benchlab.benchmarks.catalog import list_benchmarks

        return list_benchmarks()

    @application.get("/api/benchmarks/{benchmark_id}")
    def benchmark_detail(benchmark_id: str) -> dict:
        from benchlab.benchmarks.catalog import get_tasks

        item = next((item for item in benchmarks() if item["id"] == benchmark_id), None)
        if item is None:
            raise KeyError(benchmark_id)
        if item.get("status") in {"unsupported", "setup-required", "unavailable"}:
            return dict(item, tasks=[])
        return dict(
            item,
            tasks=item.get("tasks")
            or [
                task.model_dump(exclude={"expected", "verification_config"})
                for task in get_tasks(benchmark_id)
            ],
        )

    @application.get("/api/experiments")
    def experiments() -> list[dict]:
        return store.list_experiments()

    @application.post("/api/experiments/validate")
    async def validate(config: ExperimentConfig) -> dict:
        authorize_config(config)
        return (await engine.validate(config)).model_dump()

    @application.post("/api/experiments", status_code=201)
    async def create_experiment(config: ExperimentConfig) -> dict:
        authorize_config(config)
        return await engine.submit(config)

    @application.get("/api/experiments/{experiment_id}")
    def experiment_detail(experiment_id: str) -> dict:
        return dict(store.get_experiment(experiment_id), runs=store.list_runs(experiment_id))

    @application.post("/api/experiments/{experiment_id}/cancel")
    async def cancel_experiment(experiment_id: str) -> dict:
        return engine.cancel(experiment_id)

    @application.post("/api/experiments/{experiment_id}/clone", status_code=201)
    async def clone_experiment(
        experiment_id: str, overrides: Annotated[dict[str, Any] | None, Body()] = None
    ) -> dict:
        original = store.get_experiment(experiment_id)
        config = ExperimentConfig.model_validate(
            {
                **original["config"],
                "name": original["name"] + " · revision",
                "baseline_id": experiment_id,
                **(overrides or {}),
            }
        )
        authorize_config(config)
        return await engine.submit(config)

    @application.post("/api/demo", status_code=201)
    async def demo() -> dict:
        install_demo_inventory(store)
        return await engine.submit(demo_config())

    @application.get("/api/runs")
    def runs(experiment_id: str | None = None) -> list[dict]:
        return store.list_runs(experiment_id)

    @application.get("/api/runs/{run_id}")
    def run_detail(run_id: str) -> dict:
        return dict(
            store.get_run(run_id),
            results=store.list_results(run_id),
            events=store.list_events(run_id),
            artifacts=store.list_artifacts(run_id),
        )

    @application.get("/api/runs/{run_id}/events")
    def events(run_id: str, after: Annotated[int, Query(ge=0)] = 0) -> list[dict]:
        store.get_run(run_id)
        return store.list_events(run_id, after)

    @application.get("/api/runs/{run_id}/artifacts/{artifact_id}")
    def artifact(run_id: str, artifact_id: str) -> FileResponse:
        path = store.artifact_path(run_id, artifact_id)
        item = next(
            (item for item in store.list_artifacts(run_id) if item["id"] == artifact_id), None
        )
        if not item:
            raise KeyError(artifact_id)
        return FileResponse(path, media_type="application/octet-stream", filename=item["name"])

    @application.get("/api/compare")
    def comparison(run_ids: str = "") -> dict:
        from benchlab.analysis import compare_runs

        ids = list(dict.fromkeys(part for part in run_ids.split(",") if part))
        if not 2 <= len(ids) <= 16:
            raise HTTPException(422, "Choose between two and sixteen distinct runs")
        return compare_runs(store, ids)

    @application.get("/api/experiments/{experiment_id}/report")
    def report(
        experiment_id: str, format: Literal["json", "csv", "html", "zip"] = "json"
    ) -> Response:
        from benchlab.reports import export_experiment

        content, media_type, filename = export_experiment(store, experiment_id, format)
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        if format == "html":
            headers["Content-Security-Policy"] = (
                "default-src 'none'; style-src 'unsafe-inline'; sandbox"
            )
        return Response(content, media_type=media_type, headers=headers)

    @application.get("/api/diagnostics")
    async def diagnostic_report() -> dict:
        return await asyncio.to_thread(diagnostics, store.data_dir)

    @application.get("/api/metrics")
    def metrics() -> dict:
        return {"metrics": metric_registry(), "failure_categories": FAILURE_CATEGORIES}

    @application.get("/api/settings")
    def public_settings() -> dict:
        return {
            "storage": "sqlite",
            "data_dir": str(store.data_dir),
            "local_first": True,
            "telemetry": False,
            "allow_host_process": Settings.from_env().allow_host_process,
            "api_version": "1.0",
            "credential_policy": "Environment variable references only; no inline credentials",
        }

    @application.post("/api/import")
    def import_config(config: ExperimentConfig) -> dict:
        authorize_config(config)
        return config.model_dump()

    return application


def app_factory() -> FastAPI:
    return create_app()
