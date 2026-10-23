"""Run browser integration against fresh, isolated Lab and Hub services, then stop them."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]


def stop(process):
    try:
        for child in psutil.Process(process.pid).children(recursive=True):
            try:
                child.kill()
            except psutil.Error:
                pass
    except psutil.Error:
        pass
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    node = shutil.which("node")
    cli = ROOT / "node_modules/@playwright/test/cli.js"
    web = ROOT / "apps/web"
    if not node or not cli.is_file() or not (web / ".next/standalone/server.js").is_file():
        raise SystemExit(
            "Install npm dependencies in root and apps/web, then run npm run build --prefix apps/web first."
        )
    for port in (3000, 8000, 8101):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(
                    f"Port {port} is in use. Stop your owned preview before running isolated browser tests."
                )
    data = ROOT / ".bench-agents/browser-checks" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    data.mkdir(parents=True)
    runtime = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "PATHEXT",
        "COMSPEC",
        "TEMP",
        "TMP",
        "LANG",
        "LC_ALL",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "LOCALAPPDATA",
        "USERPROFILE",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in runtime}
    env.update(
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
        NEXT_TELEMETRY_DISABLED="1",
        BENCH_AGENTS_DATA_DIR=str(data / "lab"),
        BENCH_AGENTS_HUB_DATA_DIR=str(data / "hub"),
        BENCH_AGENTS_HUB_URL="http://127.0.0.1:8101",
        BENCH_AGENTS_ALLOW_HOST_PROCESS="1",
        BENCH_AGENTS_TEST_PYTHON=sys.executable,
    )
    processes = []
    logs = []
    try:
        for name, argv, cwd in [
            (
                "hub",
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "benchlab.hub:app_factory",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8101",
                    "--no-access-log",
                ],
                ROOT,
            ),
            (
                "lab",
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "benchlab.api:app_factory",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--no-access-log",
                ],
                ROOT,
            ),
            ("web", [node, "scripts/start.mjs"], web),
        ]:
            log = (data / f"{name}.log").open("w", encoding="utf-8")
            logs.append(log)
            processes.append(
                subprocess.Popen(  # noqa: S603 - fixed runtimes and argv, no shell
                    argv,
                    cwd=cwd,
                    env=env,
                    stdout=log,
                    stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            )  # noqa: S603 - fixed resolved runtimes and argv
        with httpx.Client(timeout=1, trust_env=False) as client:
            for url in (
                "http://127.0.0.1:8101/v1/health",
                "http://127.0.0.1:8000/api/health",
                "http://127.0.0.1:3000/api/health",
            ):
                for _ in range(150):
                    try:
                        if client.get(url).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if any(process.poll() is not None for process in processes):
                        raise RuntimeError(f"A test service exited; inspect logs under {data}")
                    time.sleep(0.1)
                else:
                    raise RuntimeError(f"Test service not ready; inspect logs under {data}")
        print(f"Fresh isolated Lab + Hub ready. Test data: {data.relative_to(ROOT)}", flush=True)
        completed = subprocess.run(  # noqa: S603 - Playwright argv, no shell
            [node, str(cli), "test", *sys.argv[1:]], cwd=ROOT, env=env, check=False
        )  # noqa: S603 - Playwright argv, no shell
        return completed.returncode
    finally:
        for process in reversed(processes):
            stop(process)
        for log in logs:
            log.close()
        (ROOT / "docs/evidence/browser-environment.json").write_text(
            json.dumps(
                {
                    "isolated_lab_and_hub": True,
                    "live_workspace_untouched": True,
                    "data_dir": str(data.relative_to(ROOT)),
                    "owned_services_stopped": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    raise SystemExit(main())
