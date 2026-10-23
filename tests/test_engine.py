import asyncio

import pytest

from benchlab.engine import Engine
from benchlab.schemas import ExperimentConfig, SystemSpec
from benchlab.store import Store


def demo_store(path):
    from benchlab.service import install_demo_inventory

    store = Store(path)
    install_demo_inventory(store, include_agents=True)
    return store


@pytest.mark.asyncio
async def test_demo_multi_trial_and_verification(tmp_path):
    s = demo_store(tmp_path)
    engine = Engine(s)
    c = ExperimentConfig(
        name="demo",
        demo=True,
        trials=2,
        systems=[SystemSpec(model_id="demo-reference"), SystemSpec(model_id="demo-flawed")],
    )
    e = await engine.submit(c)
    assert await engine.work_once()
    runs = s.list_runs(e["id"])
    assert len(runs) == 4
    assert s.get_experiment(e["id"])["status"] == "completed"
    assert all(r["metrics"]["passed"] == 0 for r in runs if r["system_id"] == "demo-flawed")
    assert all(r["metrics"]["passed"] > 0 for r in runs if r["system_id"] == "demo-reference")


@pytest.mark.asyncio
async def test_rejects_demo_mislabel(tmp_path):
    e = Engine(demo_store(tmp_path))
    c = ExperimentConfig(name="bad", systems=[SystemSpec(model_id="demo-reference")])
    assert not (await e.validate(c)).compatible


@pytest.mark.asyncio
async def test_cancel_interrupts_await(tmp_path, monkeypatch):
    from benchlab.adapters import registry

    entered = asyncio.Event()
    stopped = asyncio.Event()

    async def slow(*a, **kw):
        entered.set()
        try:
            await asyncio.sleep(100)
        finally:
            stopped.set()

    monkeypatch.setattr(registry, "execute_system", slow)
    s = demo_store(tmp_path)
    e = Engine(s)
    row = await e.submit(
        ExperimentConfig(name="cancel", demo=True, systems=[SystemSpec(model_id="demo-reference")])
    )
    task = asyncio.create_task(e.execute(row["id"]))
    await asyncio.wait_for(entered.wait(), 2)
    e.cancel(row["id"])
    await asyncio.wait_for(task, 2)
    assert stopped.is_set()
    assert s.get_experiment(row["id"])["status"] == "cancelled"


@pytest.mark.asyncio
async def test_timeout_counts_all_tasks_and_retries(tmp_path, monkeypatch):
    from benchlab.adapters import registry

    async def slow(*a, **kw):
        await asyncio.sleep(10)

    monkeypatch.setattr(registry, "execute_system", slow)
    s = demo_store(tmp_path)
    e = Engine(s)
    row = await e.submit(
        ExperimentConfig(
            name="timeout",
            demo=True,
            systems=[SystemSpec(model_id="demo-reference")],
            task_ids=["reasoning-inventory", "knowledge-protocol"],
            task_timeout_seconds=0.01,
            retries=1,
            retry_delay_seconds=0,
        )
    )
    await e.execute(row["id"])
    run = s.list_runs(row["id"])[0]
    results = s.list_results(run["id"])
    assert len(results) == 2 and all(r["attempts"] == 2 for r in results)
    assert run["metrics"]["failed"] == 2 and run["metrics"]["passed"] == 0


@pytest.mark.asyncio
async def test_budget_failure_records_every_task(tmp_path):
    s = demo_store(tmp_path)
    e = Engine(s)
    row = await e.submit(
        ExperimentConfig(
            name="budget",
            demo=True,
            systems=[SystemSpec(model_id="demo-reference")],
            budget_seconds=0.000001,
        )
    )
    await e.execute(row["id"])
    run = s.list_runs(row["id"])[0]
    assert len(s.list_results(run["id"])) == 8
    assert run["metrics"]["failed"] == 8


@pytest.mark.asyncio
async def test_host_agent_requires_optin_before_queue(tmp_path, monkeypatch):
    import sys

    from benchlab.schemas import AgentConfig

    monkeypatch.delenv("BENCHLAB_ALLOW_HOST_PROCESS", raising=False)
    s = demo_store(tmp_path)
    a = s.save_agent(AgentConfig(name="process", adapter="subprocess", executable=sys.executable))
    c = ExperimentConfig(name="host", mode="agent", systems=[SystemSpec(agent_id=a["id"])])
    assert not (await Engine(s).validate(c)).compatible


@pytest.mark.asyncio
async def test_mixed_demo_components_rejected(tmp_path):
    from benchlab.schemas import ModelConfig

    s = demo_store(tmp_path)
    model = s.save_model(
        ModelConfig(
            name="real",
            model="local",
            adapter="openai-compatible",
            base_url="http://127.0.0.1:1234/v1",
        )
    )
    c = ExperimentConfig(
        name="mixed",
        mode="agent",
        demo=True,
        systems=[SystemSpec(agent_id="demo-agent", model_id=model["id"])],
    )
    assert not (await Engine(s).validate(c)).compatible


@pytest.mark.asyncio
async def test_two_engines_execute_once_and_cross_cancel(tmp_path, monkeypatch):
    from benchlab.adapters import registry

    entered = asyncio.Event()
    stopped = asyncio.Event()

    async def slow(*args, **kwargs):
        entered.set()
        try:
            await asyncio.sleep(100)
        finally:
            stopped.set()

    monkeypatch.setattr(registry, "execute_system", slow)
    s = demo_store(tmp_path)
    first = Engine(s)
    second = Engine(demo_store(tmp_path))
    row = await first.submit(
        ExperimentConfig(
            name="concurrent", demo=True, systems=[SystemSpec(model_id="demo-reference")]
        )
    )
    one = asyncio.create_task(first.execute(row["id"]))
    await asyncio.wait_for(entered.wait(), 2)
    assert second.recover() == 0
    two = asyncio.create_task(second.execute(row["id"]))
    await asyncio.sleep(0.1)
    assert len(s.list_runs(row["id"])) == 1
    second.cancel(row["id"])
    await asyncio.wait_for(asyncio.gather(one, two), 2)
    assert stopped.is_set()
    assert s.get_experiment(row["id"])["status"] == "cancelled"


@pytest.mark.asyncio
async def test_observed_usage_budget_counts_failed_verification_attempt(tmp_path, monkeypatch):
    from benchlab import verification
    from benchlab.adapters import registry
    from benchlab.schemas import AdapterOutput

    calls = []

    async def output(*args, **kwargs):
        calls.append(1)
        return AdapterOutput(text="37", input_tokens=1, output_tokens=1, cost_usd=0.1)

    async def broken(*args, **kwargs):
        raise RuntimeError("verifier fixture crash")

    monkeypatch.setattr(registry, "execute_system", output)
    monkeypatch.setattr(verification, "verify", broken)
    s = demo_store(tmp_path)
    e = Engine(s)
    row = await e.submit(
        ExperimentConfig(
            name="usage",
            demo=True,
            systems=[SystemSpec(model_id="demo-reference")],
            task_ids=["reasoning-inventory", "knowledge-protocol"],
            retries=2,
            retry_delay_seconds=0,
            max_total_tokens=1,
        )
    )
    await e.execute(row["id"])
    assert len(calls) == 1
    assert s.list_runs(row["id"])[0]["metrics"]["failed"] == 2


@pytest.mark.asyncio
async def test_agent_comparison_records_controlled_model_condition(tmp_path):
    from benchlab.analysis import compare_runs

    s = demo_store(tmp_path)
    e = Engine(s)
    runs = []
    for model in ["demo-reference", "demo-flawed"]:
        row = await e.submit(
            ExperimentConfig(
                name="controlled",
                mode="agent",
                demo=True,
                systems=[SystemSpec(agent_id="demo-agent", model_id=model)],
                task_ids=["reasoning-inventory"],
            )
        )
        await e.execute(row["id"])
        runs.append(s.list_runs(row["id"])[0]["id"])
    assert not compare_runs(s, runs)["comparable"]


@pytest.mark.asyncio
async def test_persisted_cancel_checked_at_task_boundary(tmp_path, monkeypatch):
    from benchlab.adapters import registry
    from benchlab.schemas import AdapterOutput

    s = demo_store(tmp_path)
    e = Engine(s)
    calls = []
    row = await e.submit(
        ExperimentConfig(
            name="boundary", demo=True, systems=[SystemSpec(model_id="demo-reference")]
        )
    )

    async def output(*args, **kwargs):
        calls.append(1)
        Engine(demo_store(tmp_path)).cancel(row["id"])
        return AdapterOutput(text="37")

    monkeypatch.setattr(registry, "execute_system", output)
    await e.execute(row["id"])
    assert s.get_experiment(row["id"])["status"] == "cancelled"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_controlled_agent_mode_requires_explicit_model(tmp_path):
    e = Engine(demo_store(tmp_path))
    config = ExperimentConfig(
        name="agent", mode="agent", demo=True, systems=[SystemSpec(agent_id="demo-agent")]
    )
    assert not (await e.validate(config)).compatible


@pytest.mark.asyncio
async def test_outer_worker_cancellation_propagates(tmp_path, monkeypatch):
    from benchlab.adapters import registry

    entered = asyncio.Event()

    async def slow(*a, **kw):
        entered.set()
        await asyncio.sleep(100)

    monkeypatch.setattr(registry, "execute_system", slow)
    s = demo_store(tmp_path)
    e = Engine(s)
    row = await e.submit(
        ExperimentConfig(
            name="shutdown", demo=True, systems=[SystemSpec(model_id="demo-reference")]
        )
    )
    worker = asyncio.create_task(e.execute(row["id"]))
    await asyncio.wait_for(entered.wait(), 2)
    worker.cancel()
    with pytest.raises(asyncio.CancelledError):
        await worker
    assert s.get_experiment(row["id"])["status"] == "interrupted"
