import json
import runpy
from pathlib import Path

import pytest

from benchlab.plugins import register_environment, task_environment
from benchlab.schemas import AdapterOutput, ExperimentConfig, SystemSpec
from benchlab.sdk import Laboratory
from benchlab.verification import verify

example = runpy.run_path(str(Path(__file__).parents[1] / "examples/adapters/extension_points.py"))
MarkerEnvironment = example["MarkerEnvironment"]
register_examples = example["register_examples"]


@pytest.mark.asyncio
async def test_registered_environment_verifier_exporter_run_in_shared_engine(tmp_path):
    register_examples("contract-test")
    lab = Laboratory(tmp_path)
    experiment = await lab.run(
        ExperimentConfig(
            name="extensions",
            systems=[SystemSpec(model_id="demo-reference")],
            benchmark_id="contract-test-pack",
            workspace_provider="contract-test-environment",
            isolation="workspace",
            demo=True,
        )
    )
    assert experiment["status"] == "completed"
    run = lab.store.list_runs(experiment["id"])[0]
    assert lab.store.list_results(run["id"])[0]["passed"]
    assert not list(lab.store.workspaces_dir.rglob("provider-marker.txt"))
    payload = json.loads(lab.report(experiment["id"], "contract-test-evidence")[0])
    assert payload["experiment"]["id"] == experiment["id"]
    from benchlab.benchmarks.catalog import get_tasks

    task = get_tasks("contract-test-pack")[0]
    assert not (
        await verify(
            task,
            AdapterOutput(text="incorrect"),
            tmp_path,
            ExperimentConfig(**experiment["config"]),
        )
    ).passed
    with pytest.raises(ValueError):
        register_environment("contract-test-environment", MarkerEnvironment())
    with pytest.raises(ValueError):
        register_environment("bad-version", MarkerEnvironment(), version="2.0")


@pytest.mark.asyncio
async def test_environment_cleanup_runs_on_interruption(tmp_path):
    register_environment("cleanup-test", MarkerEnvironment())
    from benchlab.benchmarks.catalog import get_tasks

    with pytest.raises(RuntimeError):
        async with task_environment("cleanup-test", get_tasks("starter-v1")[0], tmp_path):
            assert (tmp_path / "provider-marker.txt").exists()
            raise RuntimeError("interrupted task")
    assert not (tmp_path / "provider-marker.txt").exists()
