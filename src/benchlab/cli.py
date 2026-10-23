"""CLI workflows over the same store and engine as the web application."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig, SystemSpec
from benchlab.sdk import Laboratory
from benchlab.service import diagnostics
from benchlab.settings import redact

app = typer.Typer(
    no_args_is_help=True,
    help="Bench Agents — local-first AI experiments with independent verification.",
)
models = typer.Typer(help="Register, inspect and probe model endpoints.")
agents = typer.Typer(help="Register, inspect and probe agent executables.")
benchmarks = typer.Typer(help="Discover runnable packs and setup requirements.")
experiments = typer.Typer(help="Inspect persisted experiments.")
app.add_typer(models, name="models")
app.add_typer(agents, name="agents")
app.add_typer(benchmarks, name="benchmarks")
app.add_typer(experiments, name="experiments")


def output(value) -> None:
    typer.echo(json.dumps(redact(value), indent=2, ensure_ascii=False, allow_nan=False))


def fail(error: Exception) -> NoReturn:
    typer.echo(json.dumps({"error": redact(str(error))}), err=True)
    raise typer.Exit(2)


def load_config(path: Path) -> dict:
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Configuration exceeds 2 MiB")
    if path.suffix == ".toml":
        import tomllib

        return tomllib.loads(path.read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


@models.command("list")
def model_list() -> None:
    output(Laboratory().store.list_models())


@models.command("add")
def model_add(config: Path) -> None:
    try:
        output(Laboratory().store.save_model(ModelConfig.model_validate(load_config(config))))
    except (ValueError, OSError, KeyError) as error:
        fail(error)


@models.command("probe")
def model_probe(model_id: str) -> None:
    from benchlab.adapters.registry import probe_model

    try:
        config = ModelConfig.model_validate(Laboratory().store.get_model(model_id)["config"])
        result = asyncio.run(probe_model(config))
        output(result.model_dump())
        if not result.compatible:
            raise typer.Exit(1)
    except (ValueError, KeyError) as error:
        fail(error)


@agents.command("list")
def agent_list() -> None:
    output(Laboratory().store.list_agents())


@agents.command("add")
def agent_add(config: Path) -> None:
    try:
        output(Laboratory().store.save_agent(AgentConfig.model_validate(load_config(config))))
    except (ValueError, OSError, KeyError) as error:
        fail(error)


@agents.command("probe")
def agent_probe(agent_id: str) -> None:
    from benchlab.adapters.registry import probe_agent

    try:
        config = AgentConfig.model_validate(Laboratory().store.get_agent(agent_id)["config"])
        result = asyncio.run(probe_agent(config))
        output(result.model_dump())
        if not result.compatible:
            raise typer.Exit(1)
    except (ValueError, KeyError) as error:
        fail(error)


@benchmarks.command("list")
def benchmark_list() -> None:
    from benchlab.benchmarks.catalog import list_benchmarks

    output(list_benchmarks())


@experiments.command("list")
def experiment_list() -> None:
    output(Laboratory().store.list_experiments())


@experiments.command("show")
def experiment_show(experiment_id: str) -> None:
    lab = Laboratory()
    try:
        output(
            dict(lab.store.get_experiment(experiment_id), runs=lab.store.list_runs(experiment_id))
        )
    except KeyError as error:
        fail(error)


@app.command()
def terminal() -> None:
    """Guided terminal: connect models/agents, validate, run and export real experiments."""
    from benchlab.terminal import run_terminal

    run_terminal(Laboratory())


@app.command()
def demo() -> None:
    """Execute deterministic public fixtures and deliberate negative cases, with zero credentials."""
    try:
        output(asyncio.run(Laboratory().demo()))
    except (ValueError, OSError, RuntimeError) as error:
        fail(error)


@app.command()
def doctor() -> None:
    """Inspect local runtime requirements; unavailable optional runtimes are explicit."""
    lab = Laboratory()
    output(diagnostics(lab.store.data_dir))


@app.command()
def run(
    config: Annotated[
        Path | None, typer.Option(help="JSON or TOML experiment configuration.")
    ] = None,
    model: Annotated[str | None, typer.Option(help="Previously registered model ID.")] = None,
    agent: Annotated[str | None, typer.Option(help="Previously registered agent ID.")] = None,
    benchmark: str = "starter-v1",
    trials: Annotated[int, typer.Option(min=1, max=50)] = 1,
    name: str = "CLI experiment",
    demo_mode: Annotated[
        bool,
        typer.Option("--demo", help="Required when testing deterministic demonstration adapters."),
    ] = False,
    allow_host_process: Annotated[
        bool,
        typer.Option(
            help="Explicitly authorize registered native agent processes; server environment opt-in also required."
        ),
    ] = False,
) -> None:
    """Run a real configured system and verify its results. Any rejected task yields exit 1."""
    try:
        selected = (
            ExperimentConfig.model_validate(load_config(config))
            if config
            else ExperimentConfig(
                name=name,
                systems=[SystemSpec(model_id=model, agent_id=agent)],
                benchmark_id=benchmark,
                mode=("agent" if model else "native") if agent else "model",
                isolation="workspace" if agent else "docker",
                trials=trials,
                demo=demo_mode,
                allow_host_process=allow_host_process,
            )
        )
        lab = Laboratory()
        experiment = asyncio.run(lab.run(selected))
        output(dict(experiment, runs=lab.store.list_runs(experiment["id"])))
        results = [
            result
            for run in lab.store.list_runs(experiment["id"])
            for result in lab.store.list_results(run["id"])
        ]
        if experiment["status"] != "completed" or any(not result["passed"] for result in results):
            raise typer.Exit(1)
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        fail(error)


@app.command()
def compare(
    run_ids: Annotated[list[str], typer.Argument(help="Two or more saved run IDs.")],
) -> None:
    try:
        if not 2 <= len(run_ids) <= 16:
            raise ValueError("Choose between two and sixteen runs")
        output(Laboratory().compare(*run_ids))
    except (ValueError, KeyError) as error:
        fail(error)


@app.command()
def report(
    experiment_id: str,
    format: Annotated[str, typer.Option(help="json, csv, html or zip")] = "json",
    out: Annotated[Path | None, typer.Option(help="Write export to this file.")] = None,
) -> None:
    try:
        content, _media_type, filename = Laboratory().report(experiment_id, format)
        if out:
            out.write_bytes(content)
            output({"path": str(out.resolve()), "filename": filename, "bytes": len(content)})
        elif format == "zip":
            raise ValueError("ZIP exports require --out PATH")
        else:
            typer.echo(content.decode("utf-8"))
    except (ValueError, KeyError, OSError) as error:
        fail(error)


@app.command()
def cancel(experiment_id: str) -> None:
    """Persist cancellation; active workers observe the state and stop execution."""
    try:
        output(Laboratory().engine.cancel(experiment_id))
    except KeyError as error:
        fail(error)


@app.command()
def worker() -> None:
    """Process durable queued work without the web UI. Use a single worker per data directory."""
    lab = Laboratory()
    lab.engine.recover()

    async def work() -> None:
        while True:
            if not await lab.engine.work_once():
                await asyncio.sleep(0.2)

    try:
        asyncio.run(work())
    except KeyboardInterrupt:
        lab.engine.recover()


@app.command()
def hub(
    port: Annotated[int, typer.Option(min=1024, max=65535)] = 8100,
    host: Annotated[
        str,
        typer.Option(
            help="Registry bind address; use TLS and deployment controls before public exposure."
        ),
    ] = "127.0.0.1",
) -> None:
    """Start only the shared agent registry; no private benchmark execution endpoints."""
    import uvicorn

    uvicorn.run("benchlab.hub:app_factory", factory=True, host=host, port=port)


def _start_local_hub():
    import os
    import subprocess
    import sys

    import httpx

    from benchlab.settings import Settings, environment_setting

    if environment_setting("HUB_URL"):
        return None
    try:
        with httpx.Client(timeout=0.5, trust_env=False) as client:
            response = client.get("http://127.0.0.1:8100/v1/health")
            if response.is_success and response.json().get("status") == "ok":
                return None
    except (httpx.HTTPError, ValueError):
        pass
    runtime_names = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "PATHEXT",
        "COMSPEC",
        "TEMP",
        "TMP",
        "LANG",
        "LC_ALL",
        "PYTHONIOENCODING",
        "PYTHONUTF8",
    }
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in runtime_names or key.startswith("BENCH_AGENTS_HUB_")
    }
    env.setdefault("BENCH_AGENTS_HUB_DATA_DIR", str(Settings.from_env().data_dir / "hub"))
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "benchlab.hub:app_factory",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8100",
            "--no-access-log",
        ],
        env=env,
    )  # noqa: S603 - fixed local service argv


@app.command()
def ui(
    port: Annotated[int, typer.Option(min=1024, max=65535)] = 8000,
    api_only: Annotated[bool, typer.Option(help="Start only the FastAPI service.")] = False,
    with_hub: Annotated[
        bool,
        typer.Option(
            help="Start the default local agent registry when no external Hub URL is configured."
        ),
    ] = True,
    web_dir: Annotated[
        Path | None,
        typer.Option(help="Next.js source directory; defaults to apps/web in this checkout."),
    ] = None,
) -> None:
    """Start the loopback API and, in a source checkout, the Next.js dashboard."""
    import os
    import shutil
    import subprocess

    import uvicorn

    web_process = None
    hub_process = None
    if not api_only:
        web = (web_dir or Path(__file__).resolve().parents[2] / "apps" / "web").resolve()
        node = shutil.which("node")
        next_cli = web / "node_modules" / "next" / "dist" / "bin" / "next"
        if not node or not next_cli.is_file() or not (web / "package.json").is_file():
            fail(
                ValueError(
                    "Dashboard source/Node dependencies unavailable. Run npm ci --prefix apps/web, or use --api-only / --web-dir"
                )
            )
        env = dict(
            os.environ,
            NEXT_PUBLIC_API_URL="/api",
            BENCH_AGENTS_API_URL=f"http://127.0.0.1:{port}",
            NEXT_TELEMETRY_DISABLED="1",
        )
        start_script = web / "scripts" / "start.mjs"
        built = web / ".next" / "standalone" / "server.js"
        argv = (
            [node, str(start_script)]
            if port == 8000 and built.is_file() and start_script.is_file()
            else [node, str(next_cli), "dev", "--hostname", "127.0.0.1"]
        )
        web_process = subprocess.Popen(argv, cwd=web, env=env)  # noqa: S603 - fixed resolved Node/Next entry, no shell
        typer.echo(
            "Dashboard: http://127.0.0.1:3000 · API: http://127.0.0.1:" + str(port), err=True
        )
    try:
        if with_hub and not api_only:
            hub_process = _start_local_hub()
        uvicorn.run("benchlab.api:app_factory", factory=True, host="127.0.0.1", port=port)
    finally:
        for process in [web_process, hub_process]:
            if process is None:
                continue
            import psutil

            try:
                for child in psutil.Process(process.pid).children(recursive=True):
                    try:
                        child.kill()
                    except psutil.Error:
                        pass
            except psutil.Error:
                pass
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
