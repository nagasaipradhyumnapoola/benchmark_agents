"""Optional framework execution. Scores retain upstream names and never masquerade as starter runs."""

import asyncio
import json
import os
import re
from pathlib import Path

from benchlab.sandbox import _drain


def _permission(allowed):
    if not allowed or os.environ.get("BENCHLAB_ALLOW_HOST_PROCESS") != "1":
        raise PermissionError("Framework execution requires both host-process opt-ins")


def build_lm_eval_command(
    model: str, model_args: str, tasks: list[str], output: Path, limit: int | None = None
) -> list[str]:
    if not tasks or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", task) for task in tasks):
        raise ValueError("Explicit task names are required")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", model):
        raise ValueError("Invalid model backend")
    args = [
        "lm-eval",
        "run",
        "--model",
        model,
        "--model_args",
        model_args,
        "--tasks",
        ",".join(tasks),
        "--output_path",
        str(output),
        "--log_samples",
    ]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        args += ["--limit", str(limit)]
    return args


def parse_lm_eval_results(data: dict) -> dict:
    results = data.get("results")
    if not isinstance(results, dict) or not results:
        raise ValueError("No upstream task results")
    metrics = {}
    for task, values in results.items():
        if not isinstance(values, dict):
            raise ValueError("Malformed upstream metrics")
        metrics[task] = {
            key: value
            for key, value in values.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        if not metrics[task]:
            raise ValueError("No numeric upstream metrics")
    return {
        "framework": "lm-evaluation-harness",
        "metrics": metrics,
        "versions": data.get("versions", {}),
        "comparable_to_starter": False,
    }


async def run_lm_eval(
    model: str,
    model_args: str,
    tasks: list[str],
    workspace: Path,
    *,
    allow_host_process: bool = False,
    limit: int | None = None,
    timeout_seconds: float = 300,
    env_allowlist: list[str] | None = None,
) -> dict:
    _permission(allow_host_process)
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    result_dir = workspace / "lm-eval-results"
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "SystemRoot", "WINDIR", "PATHEXT", *(env_allowlist or [])}
    }
    env.update(
        {
            "HOME": str(workspace),
            "USERPROFILE": str(workspace),
            "HF_HOME": str(workspace / "hf-cache"),
        }
    )
    process = await asyncio.create_subprocess_exec(
        *build_lm_eval_command(model, model_args, tasks, result_dir, limit),
        cwd=workspace,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            stdout, stderr = await asyncio.gather(_drain(process.stdout), _drain(process.stderr))
            await process.wait()
        if process.returncode:
            raise RuntimeError(f"lm-eval exited with status {process.returncode}")
        files = list(result_dir.rglob("results_*.json"))
        if len(files) != 1:
            raise ValueError("Expected one upstream result file; use a fresh workspace")
        path = files[0]
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(result_dir.resolve())
            or path.stat().st_size > 10_000_000
        ):
            raise ValueError("Unsafe upstream result artifact")
        return {
            **parse_lm_eval_results(json.loads(path.read_text())),
            "artifact": str(path),
            "sample_limit": limit,
        }
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


async def run_inspect_starter(
    model: str, workspace: Path, *, allow_host_process: bool = False
) -> dict:
    """Run original non-code fixtures using actual Inspect dataset/solver/scorer/eval_async APIs."""
    _permission(allow_host_process)
    from inspect_ai import Task, eval_async
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import match
    from inspect_ai.solver import generate

    from benchlab.benchmarks.catalog import get_tasks

    tasks = get_tasks("starter-v1", ["reasoning-inventory", "knowledge-protocol"])
    dataset = [Sample(id=task.id, input=task.prompt, target=task.expected) for task in tasks]
    workspace.mkdir(parents=True, exist_ok=True)
    model_args = {}
    if model.startswith("mockllm/"):
        from inspect_ai.model import ModelOutput, ModelUsage

        model_args = {
            "custom_outputs": [
                ModelOutput.from_content(
                    model="mockllm",
                    content="deliberately wrong framework fixture",
                )
                for _ in tasks
            ]
        }
    for output in model_args.get("custom_outputs", []):
        output.usage = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)
    logs = await eval_async(
        Task(dataset=dataset, solver=generate(), scorer=match()),
        model=model,
        model_args=model_args,
        log_dir=str(workspace),
        log_format="json",
        time_limit=30,
    )
    if len(logs) != 1:
        raise ValueError("Expected one Inspect evaluation log")
    log = logs[0]
    return {
        "framework": "inspect-ai",
        "status": log.status,
        "log_location": log.location,
        "results": log.results.model_dump(mode="json") if log.results else None,
        "comparable_to_starter": False,
        "demo": model.startswith("mockllm/"),
    }
