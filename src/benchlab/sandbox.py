"""Fail-closed Docker execution with no host mounts or inherited container environment."""

import asyncio
import json
import shutil
import subprocess
import uuid
from typing import Any

IMAGE = "python:3.12.10-slim"
MAX_OUTPUT = 1_000_000


def diagnostics() -> dict:
    state: dict[str, Any] = {
        "available": False,
        "executable": shutil.which("docker"),
        "image": IMAGE,
        "network": "none",
        "isolation": "docker",
        "reason": None,
    }
    if not state["executable"]:
        state["reason"] = "Docker CLI is not installed"
        return state
    try:
        result = subprocess.run(  # noqa: S603 - resolved Docker executable, fixed argv, shell=False
            [state["executable"], "info", "--format", "{{.OSType}}"],
            capture_output=True,
            timeout=5,
            text=True,
            check=False,
        )
        state["available"] = result.returncode == 0 and result.stdout.strip() == "linux"
        state["reason"] = (
            None if state["available"] else "A running Docker Linux daemon is required"
        )
    except (OSError, subprocess.TimeoutExpired):
        state["reason"] = "Docker daemon did not respond"
    return state


async def _drain(stream):
    result = bytearray()
    while data := await stream.read(65536):
        result.extend(data)
        if len(result) > MAX_OUTPUT:
            raise RuntimeError("Sandbox output limit exceeded")
    return bytes(result)


async def run_python(
    code: str, test_code: str, timeout_seconds: float, memory_mb: int = 256, cpus: float = 1
) -> dict:
    state = await asyncio.to_thread(diagnostics)
    if not state["available"]:
        raise RuntimeError("Docker Linux sandbox is unavailable; no host fallback")
    if not 64 <= memory_mb <= 32768 or not 0.1 <= cpus <= 16 or not 0 < timeout_seconds <= 3600:
        raise ValueError("Invalid sandbox limits")
    if len(code.encode()) + len(test_code.encode()) > 1_000_000:
        raise ValueError("Code input too large")
    executable = state["executable"]
    name = "benchlab-" + uuid.uuid4().hex
    marker = "BENCHLAB_COMPLETED_" + uuid.uuid4().hex
    # Completion is required; exit(0) before tests cannot pass. This public harness is not an anti-cheat boundary.
    runner = "import sys,json\np=json.load(sys.stdin)\ng={}\nexec(compile(p['code'],'submission.py','exec'),g)\nexec(compile(p['tests'],'tests.py','exec'),g)\nsys.stdout.write(p['marker']+'\\n')\n"
    args = [
        executable,
        "run",
        "--name",
        name,
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--memory",
        f"{memory_mb}m",
        "--memory-swap",
        f"{memory_mb}m",
        "--cpus",
        str(cpus),
        "--user",
        "65534:65534",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",  # noqa: S108 - private container tmpfs, not host temp
        "--ulimit",
        "nofile=64:64",
        "-i",
        IMAGE,
        "python",
        "-I",
        "-B",
        "-c",
        runner,
    ]
    process = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert process.stdin is not None
    timed_out = False
    try:
        process.stdin.write(
            json.dumps({"code": code, "tests": test_code, "marker": marker}).encode()
        )
        await process.stdin.drain()
        process.stdin.close()
        async with asyncio.timeout(timeout_seconds):
            stdout, stderr = await asyncio.gather(_drain(process.stdout), _drain(process.stderr))
            await process.wait()
        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode(errors="replace").removesuffix(marker + "\n"),
            "completed": stdout.endswith((marker + "\n").encode()),
            "stderr": stderr.decode(errors="replace"),
            "timed_out": timed_out,
            "image": IMAGE,
        }
    except TimeoutError:
        timed_out = True
        return {"exit_code": None, "timed_out": True, "image": IMAGE}
    finally:
        cleanup = await asyncio.create_subprocess_exec(
            executable,
            "rm",
            "-f",
            name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(cleanup.wait(), timeout=5)
        except TimeoutError:
            cleanup.kill()
            await cleanup.wait()
        if process.returncode is None:
            process.kill()
            await process.wait()
