import pytest

from benchlab.benchmarks.catalog import get_tasks
from benchlab.schemas import AdapterOutput, ExperimentConfig, SystemSpec
from benchlab.verification import verify


@pytest.mark.asyncio
async def test_starter_golden_and_wrong(tmp_path):
    config = ExperimentConfig(name="test", systems=[SystemSpec(model_id="demo-reference")])
    tasks = get_tasks("starter-v1")
    assert len(tasks) == 8
    for task in tasks:
        assert not (await verify(task, AdapterOutput(text="wrong"), tmp_path, config)).passed
    task = next(t for t in tasks if t.id == "reasoning-inventory")
    assert (await verify(task, AdapterOutput(text="37"), tmp_path, config)).passed


@pytest.mark.asyncio
async def test_unknown_verifier_fails_closed(tmp_path):
    task = get_tasks("starter-v1")[0].model_copy(update={"verifier": "unsupported"})
    config = ExperimentConfig(name="t", systems=[SystemSpec(model_id="x")])
    assert not (await verify(task, AdapterOutput(text="37"), tmp_path, config)).passed


@pytest.mark.asyncio
async def test_python_verifier_rejects_exit_zero_without_completion(tmp_path, monkeypatch):
    from benchlab import sandbox

    async def fake(*args, **kwargs):
        return {"exit_code": 0, "stdout": "", "completed": False}

    monkeypatch.setattr(sandbox, "run_python", fake)
    task = get_tasks("starter-v1", ["coding-dedupe"])[0]
    config = ExperimentConfig(name="t", systems=[SystemSpec(model_id="x")])
    result = await verify(task, AdapterOutput(text="import sys; sys.exit(0)"), tmp_path, config)
    assert not result.passed


def test_benchmark_plugin_selection_and_validation():
    from benchlab.benchmarks.catalog import list_benchmarks, register_benchmark
    from benchlab.schemas import TaskDefinition

    task = TaskDefinition(
        id="one", name="one", category="fixture", prompt="Return 1", verifier="exact", expected="1"
    )
    register_benchmark("fixture-pack", [task], {"name": "fixture", "version": "1.0.0"})
    assert get_tasks("fixture-pack", ["one"])[0].prompt == "Return 1"
    assert any(pack["id"] == "fixture-pack" for pack in list_benchmarks())
    with pytest.raises(ValueError):
        get_tasks("fixture-pack", ["missing"])
    with pytest.raises(ValueError):
        register_benchmark("fixture-pack", [task], {})
