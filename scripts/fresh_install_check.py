"""Run with the installed wheel's interpreter from a disposable working directory."""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

import benchlab
from benchlab.hub import create_hub_app
from benchlab.sdk import Laboratory


async def main():
    root = Path.cwd().resolve()
    assert "site-packages" in str(benchlab.__file__)
    data = root / "data"
    hub = create_hub_app(root / "registry")
    assert any(route.path == "/v1/health" for route in hub.routes)
    assert not any(route.path == "/api/models" for route in hub.routes)
    os.environ["BENCH_AGENTS_DATA_DIR"] = str(data)
    lab = Laboratory(data)
    experiment = await lab.demo()
    runs = lab.store.list_runs(experiment["id"])
    assert experiment["status"] == "completed" and len(runs) == 2
    assert [sum(r["passed"] for r in lab.store.list_results(run["id"])) for run in runs] == [8, 0]
    for extension in ["json", "csv", "html", "zip"]:
        content, _, filename = lab.report(experiment["id"], extension)
        (root / filename).write_bytes(content)
        assert content
    command = [
        str(
            Path(sys.executable).with_name(
                "bench-agents.exe" if os.name == "nt" else "bench-agents"
            )
        ),
        "experiments",
        "list",
    ]
    listed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=15)  # noqa: S603
    assert experiment["id"] in listed.stdout
    server = subprocess.Popen(  # noqa: S603 - fixed local API executable and argv
        [
            sys.executable,
            "-m",
            "uvicorn",
            "benchlab.api:app_factory",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(timeout=2, trust_env=False) as client:
            for _ in range(50):
                try:
                    response = client.get("http://127.0.0.1:8001/api/experiments")
                    response.raise_for_status()
                    break
                except httpx.HTTPError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Installed wheel API did not become ready")
            assert any(row["id"] == experiment["id"] for row in response.json())
            assert client.get("http://127.0.0.1:8001/openapi.json").status_code == 200
            community = client.get("http://127.0.0.1:8001/api/community")
            community.raise_for_status()
            assert isinstance(community.json()["published"], list)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
    print(
        json.dumps(
            {
                "status": "passed",
                "installed_distribution": "bench-agents 0.1.0",
                "isolated_venv": True,
                "sdk_demo": "8/8 reference, 0/8 deliberate negative",
                "cli_shared_storage": "passed",
                "api_shared_storage": "passed",
                "community_catalog_packaged": "passed",
                "separate_hub_modules_packaged": "passed",
                "exports": ["json", "csv", "html", "zip"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
