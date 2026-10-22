import json
import sys

import httpx
import pytest

from benchlab.adapters import registry
from benchlab.benchmarks.catalog import get_tasks
from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig, SystemSpec


@pytest.mark.asyncio
async def test_provider_seed_changes_actual_request(tmp_path, monkeypatch):
    bodies = []

    async def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "37"}}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        registry, "http_client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    model = ModelConfig(
        name="fixture",
        model="fixture",
        adapter="openai-compatible",
        base_url="http://localhost:1234/v1",
    )
    for seed in [12, 99]:
        await registry.execute_system(
            SystemSpec(model_id=model.id),
            model,
            None,
            get_tasks("starter-v1")[0],
            tmp_path / str(seed),
            ExperimentConfig(name="seed", systems=[SystemSpec(model_id=model.id)], seed=seed),
            lambda event: None,
        )
    assert [body["seed"] for body in bodies] == [12, 99]


def test_cli_cannot_ignore_selected_model():
    model = ModelConfig(name="selected", model="required-model", adapter="openai-compatible")
    agent = AgentConfig(name="generic", adapter="subprocess", executable=sys.executable)
    with pytest.raises(ValueError, match="model_flag"):
        registry.cli_argv(agent, model, "prompt")


@pytest.mark.asyncio
async def test_cli_rejects_ignored_system_parameters(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCHLAB_ALLOW_HOST_PROCESS", "1")
    agent = AgentConfig(
        name="generic", adapter="subprocess", executable=sys.executable, args=["-c", 'print("37")']
    )
    config = ExperimentConfig(
        name="ignored",
        mode="native",
        systems=[SystemSpec(agent_id=agent.id)],
        allow_host_process=True,
    )
    with pytest.raises(ValueError, match="parameters"):
        await registry.execute_system(
            SystemSpec(agent_id=agent.id, parameters={"temperature": 0.2}),
            None,
            agent,
            get_tasks("starter-v1")[0],
            tmp_path,
            config,
            lambda event: None,
        )
