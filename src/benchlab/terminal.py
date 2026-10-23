"""Guided terminal workflows using the same SDK and compatibility gates as the dashboard."""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Literal

import typer
from click import IntRange
from pydantic import ValidationError
from rich.console import Console

from benchlab.adapters.registry import probe_agent, probe_model
from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig, SystemSpec
from benchlab.settings import environment_setting, redact
from benchlab.terminal_ui import execute_with_progress, render_banner, render_menu, render_results


def say(message):
    typer.echo(redact(str(message)))


def number(label, default, minimum=1, maximum=50):
    return typer.prompt(label, default=default, type=IntRange(minimum, maximum))


def environment_name(label, default=""):
    # Hidden input prevents accidental key pastes appearing in terminal logs.
    value = typer.prompt(label, default=default, hide_input=True, show_default=False).strip()
    if value and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError("Enter an environment variable name, never a credential value")
    return value or None


def choose(rows, label):
    if not rows:
        raise ValueError(f"No {label} available. Connect one first.")
    for index, row in enumerate(rows, 1):
        say(f"  {index}. {row['name']}  [{row['id']}]")
    return rows[number(f"Select {label}", 1, maximum=len(rows)) - 1]


def choose_many(rows, label):
    if not rows:
        raise ValueError(f"No {label} available. Connect one first.")
    for index, row in enumerate(rows, 1):
        say(f"  {index}. {row['name']}  [{row['id']}]")
    value = typer.prompt(f"Select {label} numbers separated by commas, or all", default="1").strip()
    if value.lower() == "all":
        return rows
    try:
        indices = list(dict.fromkeys(int(item.strip()) for item in value.split(",")))
    except ValueError:
        raise ValueError("Enter selection numbers separated by commas, or all") from None
    if not indices or any(index < 1 or index > len(rows) for index in indices):
        raise ValueError("Choose numbers from the displayed list")
    return [rows[index - 1] for index in indices]


def show_check(check):
    say("Compatibility: READY" if check.compatible else "Compatibility: BLOCKED")
    for reason in check.reasons:
        say(f"  Blocked: {reason}")
    for warning in check.warnings:
        say(f"  Note: {warning}")


def connect_model(lab):
    from benchlab.service import connect_model as save_connection

    name = typer.prompt("Model display name")
    say("  1. OpenAI-compatible chat endpoint\n  2. Ollama")
    adapter = "openai-compatible" if number("Adapter", 1, maximum=2) == 1 else "ollama"
    say("  1. Local server\n  2. Hosted API")
    connection: Literal["local", "hosted"] = "local" if number("Connection type", 1, maximum=2) == 1 else "hosted"
    base = typer.prompt(
        "Endpoint base URL",
        default="http://127.0.0.1:1234/v1"
        if adapter == "openai-compatible"
        else "http://127.0.0.1:11434",
    )
    identity = typer.prompt("Exact provider model ID")
    say("  1. No API key\n  2. Environment variable reference\n  3. Enter a key for this session")
    auth = number("Authentication", 1 if connection == "local" else 3, maximum=3)
    credential = environment_name("API key environment variable name") if auth == 2 else None
    model = ModelConfig(
        name=name,
        adapter=adapter,
        model=identity,
        base_url=base,
        api_key_env=credential,
        connection_type=connection,
    )
    key = (
        typer.prompt("API key (hidden; kept only in this terminal session)", hide_input=True)
        if auth == 3
        else None
    )
    saved = save_connection(lab.store, model, key)
    model = ModelConfig(**saved["config"])
    if key:
        say("Key held in session memory only. Re-enter after restarting this process.")
    say(f"Saved model {model.id}. Probing discovery; no generation request.")
    show_check(asyncio.run(probe_model(model)))


def connect_agent(lab):
    name = typer.prompt("Agent display name")
    say(
        "  1. Custom subprocess harness\n  2. Codex CLI (native product)\n  3. OpenCode CLI (native product)"
    )
    adapter = ["subprocess", "codex-cli", "opencode-cli"][number("Adapter", 1, maximum=3) - 1]
    executable = typer.prompt(
        "Executable command or full path",
        default="python"
        if adapter == "subprocess"
        else ("codex" if adapter == "codex-cli" else "opencode"),
    )
    script = (
        typer.prompt("Script path (optional for Python/Node harnesses)", default="")
        if adapter == "subprocess"
        else ""
    )
    extra = json.loads(
        typer.prompt("Additional arguments as a JSON array; never include secrets", default="[]")
    )
    if not isinstance(extra, list) or any(not isinstance(value, str) for value in extra):
        raise ValueError("Arguments must be a JSON array of strings")
    args = ([str(Path(script).expanduser().resolve())] if script else []) + extra
    bindings = {}
    if adapter == "subprocess":
        say("For controlled model pairing, these settings must match your harness interface.")
        bindings = dict(
            model_flag=typer.prompt("Model selection flag", default="--model"),
            model_base_url_env=environment_name(
                "Harness endpoint environment variable name", "HARNESS_BASE_URL"
            ),
            model_api_key_env=environment_name(
                "Harness API key environment variable name", "HARNESS_API_KEY"
            ),
        )
    names = typer.prompt(
        "Additional environment variable names to allow (comma-separated; no values)", default=""
    )
    allowlist = [name.strip() for name in names.split(",") if name.strip()]
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) for value in allowlist):
        raise ValueError("Allowlist entries must be environment variable names, never values")
    agent = AgentConfig(
        name=name,
        adapter=adapter,
        executable=executable,
        args=args,
        env_allowlist=allowlist,
        native=adapter != "subprocess",
        **bindings,
    )
    lab.store.save_agent(agent)
    say(f"Saved agent {agent.id}. Checking executable discovery; no agent execution.")
    show_check(asyncio.run(probe_agent(agent)))


def describe_experiment(lab, experiment):
    render_results(Console(highlight=False), lab, experiment)


def execute(lab, mode):
    from benchlab.credentials import get_key, remember_key

    models = [row for row in lab.store.list_models() if not row["demo"]]
    agents = [row for row in lab.store.list_agents() if not row["demo"]]
    if mode in {"agent", "matrix"}:
        agents = [
            row
            for row in agents
            if not row["config"]["native"] and row["config"]["adapter"] == "subprocess"
        ]
    elif mode == "native":
        agents = [
            row
            for row in agents
            if row["config"]["native"] or row["config"]["adapter"] in {"codex-cli", "opencode-cli"}
        ]
    selected_models = (
        []
        if mode == "native"
        else ([choose(models, "model")] if mode == "agent" else choose_many(models, "models"))
    )
    selected_agents = [] if mode == "model" else choose_many(agents, "agents")
    if mode in {"agent", "matrix"}:
        systems = [
            SystemSpec(model_id=model["id"], agent_id=agent["id"])
            for model in selected_models
            for agent in selected_agents
        ]
    elif mode == "model":
        systems = [SystemSpec(model_id=model["id"]) for model in selected_models]
    else:
        systems = [SystemSpec(agent_id=agent["id"]) for agent in selected_agents]
    if len(systems) > 16:
        raise ValueError(
            f"Selected {len(systems)} systems; choose at most 16 combinations per experiment"
        )
    if mode == "matrix":
        say(f"{len(systems)} model-agent combinations selected:")
        for model in selected_models:
            for agent in selected_agents:
                say(f"  {agent['name']} + {model['name']}")
    for row in selected_models:
        reference = row["config"].get("api_key_env")
        if reference and reference.startswith("BENCH_AGENTS_SESSION_") and not get_key(reference):
            if not typer.confirm(
                f"Session key unavailable for {row['name']}. Enter it now?", default=False
            ):
                say("Run not launched. Re-enter the key in this process before testing.")
                return
            remember_key(typer.prompt("API key (hidden; session only)", hide_input=True), reference)
    say("  1. Single reasoning task smoke\n  2. All eight default public text tasks")
    task_ids = ["reasoning-inventory"] if number("Task set", 1, maximum=2) == 1 else []
    trials, tokens, timeout, budget = 1, 512, 30, 300
    if not typer.confirm("Use default limits: 1 trial, 30s per task, 300s total?", default=True):
        trials = number("Trials", 1)
        tokens = number("Maximum output tokens (provider adapters only)", 512, maximum=131072)
        timeout = number("Per-task timeout in seconds", 30, maximum=3600)
        budget = number("Whole experiment budget in seconds", 300, maximum=86400)
    host = False
    say(
        f"{len(systems)} systems × {len(task_ids) if task_ids else 8} tasks × {trials} trials = {len(systems) * (len(task_ids) if task_ids else 8) * trials} task checks. Systems execute sequentially within the total budget."
    )
    if selected_agents:
        if environment_setting("ALLOW_HOST_PROCESS") != "1":
            raise ValueError(
                "Host agents are disabled. Set BENCH_AGENTS_ALLOW_HOST_PROCESS=1 in your shell, restart terminal mode, and explicitly authorize the run."
            )
        host = typer.confirm(
            "Allow this registered agent to execute with your OS privileges?", default=False
        )
        if not host:
            say("Run not launched.")
            return
    config = ExperimentConfig(
        name=f"Terminal {mode} test: {len(systems)} systems",
        mode=mode,
        systems=systems,
        task_ids=task_ids,
        trials=trials,
        max_tokens=tokens,
        task_timeout_seconds=timeout,
        budget_seconds=budget,
        isolation="workspace",
        allow_host_process=host,
    )
    say("Validating selected systems. Provider discovery is not a capability guarantee.")
    check = asyncio.run(lab.engine.validate(config))
    show_check(check)
    if not check.compatible or not typer.confirm(
        "Run now? This contacts the configured provider and may incur its charges", default=False
    ):
        say("Run not launched.")
        return
    say("Running. Press Ctrl+C to interrupt and retain partial evidence.")
    result = asyncio.run(execute_with_progress(lab, config, Console(highlight=False)))
    describe_experiment(lab, result)
    say("Use Inspect/export results for the saved report and run IDs.")


def inspect_results(lab):
    experiment = choose(list(reversed(lab.store.list_experiments())), "experiment")
    describe_experiment(lab, experiment)
    if typer.confirm("Export a ZIP evidence report?", default=False):
        content, _, filename = lab.report(experiment["id"], "zip")
        target = Path(typer.prompt("Output path", default=filename)).expanduser().resolve()
        if target.exists() and not typer.confirm("File exists. Replace it?", default=False):
            return
        target.write_bytes(content)
        say(f"Report saved: {target}")


def compare_results(lab):
    rows = [dict(run, name=run["system_name"]) for run in lab.store.list_runs()]
    baseline = choose(rows, "baseline run")
    candidate = choose([row for row in rows if row["id"] != baseline["id"]], "candidate run")
    comparison = lab.compare(baseline["id"], candidate["id"])
    say("Comparable conditions" if comparison["comparable"] else "Conditions do not match")
    for reason in comparison["reasons"]:
        say(reason)
    for result in comparison["summary"]:
        rate = result["success_rate"]
        say(
            f"{result['system_name']}: {result['passed']}/{result['total']} verified"
            + (f" ({rate:.1%})" if rate is not None else "")
        )
    for pair in comparison["paired_differences"]:
        say(
            f"Improved: {pair['improved']} | regressed: {pair['regressed']} | exploratory McNemar p={pair['mcnemar_exact_p']:.4g}"
        )


def run_terminal(lab):
    # Redirected Windows shells may use cp1252: retain readable escapes for unsupported names.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    console = Console(highlight=False)
    render_banner(console, lab)
    actions = {
        1: connect_model,
        2: connect_agent,
        3: lambda lab: execute(lab, "model"),
        4: lambda lab: execute(lab, "agent"),
        5: lambda lab: execute(lab, "native"),
        6: inspect_results,
        7: compare_results,
        8: lambda lab: execute(lab, "matrix"),
    }
    while True:
        try:
            render_menu(console, lab)
            choice = number("Action", 0, minimum=0, maximum=8)
            if choice == 0:
                return
            try:
                actions[choice](lab)
            except ValidationError as error:
                # Pydantic's default string includes submitted input, which could be a pasted key.
                say("Invalid configuration: " + "; ".join(item["msg"] for item in error.errors()))
            except (ValueError, OSError, KeyError, RuntimeError) as error:
                say(f"Cannot complete action: {error}")
        except (EOFError, KeyboardInterrupt, typer.Abort):
            say("\nTerminal session ended. Saved records remain in the workspace.")
            return
