import json
import sys

import httpx
import pytest

from benchlab.adapters import registry
from benchlab.benchmarks.catalog import get_tasks
from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig, SystemSpec
from benchlab.verification import verify


@pytest.mark.asyncio
async def test_demo_passes_and_flawed_fails(tmp_path):
    config = ExperimentConfig(name="demo", systems=[SystemSpec(model_id="x")])
    for task in get_tasks("starter-v1"):
        for variant, want in [("reference", True), ("flawed", False)]:
            output = await registry.execute_system(
                config.systems[0],
                ModelConfig(name="demo", adapter="demo", model=variant, demo=True),
                None,
                task,
                tmp_path,
                config,
                lambda e: None,
            )
            assert (await verify(task, output, tmp_path, config)).passed is want


@pytest.mark.asyncio
async def test_openai_request_usage_and_no_answer_leak(tmp_path, monkeypatch):
    def handler(request):
        body = json.loads(request.content)
        assert body["messages"] == [{"role": "user", "content": get_tasks("starter-v1")[0].prompt}]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "37"}}],
                "usage": {"prompt_tokens": 21, "completion_tokens": 1},
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        registry,
        "http_client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    model = ModelConfig(
        name="local",
        adapter="openai-compatible",
        model="fixture",
        base_url="http://localhost:9000/v1",
        input_cost_per_million=1,
        output_cost_per_million=2,
    )
    config = ExperimentConfig(name="test", systems=[SystemSpec(model_id=model.id)])
    output = await registry.execute_system(
        config.systems[0], model, None, get_tasks("starter-v1")[0], tmp_path, config, lambda e: None
    )
    assert output.text == "37" and output.input_tokens == 21 and output.output_tokens == 1
    assert output.cost_usd == pytest.approx(0.000023)


@pytest.mark.asyncio
async def test_cli_requires_both_permissions(tmp_path, monkeypatch):
    monkeypatch.delenv("BENCHLAB_ALLOW_HOST_PROCESS", raising=False)
    agent = AgentConfig(name="cli", adapter="subprocess", executable="python")
    config = ExperimentConfig(
        name="t",
        systems=[SystemSpec(agent_id=agent.id)],
        isolation="workspace",
        allow_host_process=True,
    )
    with pytest.raises(PermissionError):
        await registry.execute_system(
            config.systems[0],
            None,
            agent,
            get_tasks("starter-v1")[0],
            tmp_path,
            config,
            lambda e: None,
        )


@pytest.mark.asyncio
async def test_subprocess_runs_fixture_and_records_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCHLAB_ALLOW_HOST_PROCESS", "1")
    monkeypatch.setenv("PRIVATE_SECRET_KEY", "never-leak-this")
    fixture = tmp_path / "fixture.py"
    fixture.write_text(
        "import os,sys\nfrom pathlib import Path\nassert 'PRIVATE_SECRET_KEY' not in os.environ\nassert sys.stdin.read()\nPath('report.txt').write_text('ready')\nprint('37')"
    )
    agent = AgentConfig(
        name="fixture", adapter="subprocess", executable=sys.executable, args=[str(fixture)]
    )
    config = ExperimentConfig(
        name="t",
        systems=[SystemSpec(agent_id=agent.id)],
        isolation="workspace",
        allow_host_process=True,
    )
    output = await registry.execute_system(
        config.systems[0], None, agent, get_tasks("starter-v1")[0], tmp_path, config, lambda e: None
    )
    assert output.text.strip() == "37"
    assert output.files["report.txt"] == "ready"


@pytest.mark.asyncio
async def test_workspace_task_independent_state(tmp_path):
    task = get_tasks("starter-v1", ["workspace-normalize"])[0]
    config = ExperimentConfig(name="t", systems=[SystemSpec(model_id="demo-reference")])
    output = await registry.execute_system(
        config.systems[0],
        ModelConfig(name="d", adapter="demo", model="reference", demo=True),
        None,
        task,
        tmp_path,
        config,
        lambda e: None,
    )
    assert (await verify(task, output, tmp_path, config)).passed
    (tmp_path / "normalized.json").write_text("[]")
    assert not (await verify(task, output, tmp_path, config)).passed


@pytest.mark.asyncio
async def test_trusted_plugin_registration(tmp_path):
    from benchlab.schemas import AdapterOutput, CompatibilityResult

    async def execute(*args):
        return AdapterOutput(text="37")

    async def probe(config):
        return CompatibilityResult(compatible=True)

    registry.register_model_adapter("test-plugin", execute, probe, version="1.0")
    model = ModelConfig(name="plugin", adapter="test-plugin", model="local")
    config = ExperimentConfig(name="t", systems=[SystemSpec(model_id=model.id)])
    assert (await registry.probe_model(model)).compatible
    assert (
        await registry.execute_system(
            config.systems[0],
            model,
            None,
            get_tasks("starter-v1")[0],
            tmp_path,
            config,
            lambda e: None,
        )
    ).text == "37"
    with pytest.raises(ValueError):
        registry.register_model_adapter("incompatible", execute, probe, version="2.0")


@pytest.mark.asyncio
async def test_subprocess_timeout_is_bounded(tmp_path, monkeypatch):
    import time

    monkeypatch.setenv("BENCHLAB_ALLOW_HOST_PROCESS", "1")
    agent = AgentConfig(
        name="slow",
        adapter="subprocess",
        executable=sys.executable,
        args=["-c", "import time; time.sleep(60)"],
    )
    config = ExperimentConfig(
        name="t",
        systems=[SystemSpec(agent_id=agent.id)],
        isolation="workspace",
        allow_host_process=True,
        task_timeout_seconds=0.1,
    )
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        await registry.execute_system(
            config.systems[0],
            None,
            agent,
            get_tasks("starter-v1")[0],
            tmp_path,
            config,
            lambda e: None,
        )
    assert time.monotonic() - started < 5


def test_cli_json_parsers_and_safe_argv(monkeypatch):
    monkeypatch.setattr(registry, "executable_prefix", lambda agent: ["codex"])
    agent = AgentConfig(name="codex", adapter="codex-cli", executable="codex")
    args = registry.cli_argv(agent, None, "echo unsafe; & malicious")
    assert args[-1] == "echo unsafe; & malicious"
    assert "--sandbox" in args and args[args.index("--sandbox") + 1] == "read-only"
    assert (
        registry.parse_cli(
            "codex-cli", '{"type":"item.completed","item":{"type":"agent_message","text":"37"}}'
        )
        == "37"
    )
    assert registry.parse_cli("opencode-cli", '{"type":"text","part":{"text":"37"}}') == "37"
    with pytest.raises(ValueError):
        registry.parse_cli("codex-cli", '{"type":"thread.started"}')


@pytest.mark.asyncio
async def test_ollama_usage_and_provider_failure(tmp_path, monkeypatch):
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert body["stream"] is False and body["options"]["num_predict"] == 2048
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": "37"},
                "prompt_eval_count": 20,
                "eval_count": 1,
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        registry,
        "http_client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    model = ModelConfig(
        name="local", adapter="ollama", model="fixture", base_url="http://localhost:11434"
    )
    config = ExperimentConfig(name="t", systems=[SystemSpec(model_id=model.id)])
    result = await registry.execute_system(
        config.systems[0], model, None, get_tasks("starter-v1")[0], tmp_path, config, lambda e: None
    )
    assert result.text == "37" and result.input_tokens == 20 and result.cost_usd is None
    monkeypatch.setattr(
        registry,
        "http_client",
        lambda **kwargs: original(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, json={"error": "unauthorized"})
            ),
            **kwargs,
        ),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await registry.execute_system(
            config.systems[0],
            model,
            None,
            get_tasks("starter-v1")[0],
            tmp_path,
            config,
            lambda e: None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter", ["openai-compatible", "ollama"])
async def test_experiment_seed_forwarded_and_override(tmp_path, monkeypatch, adapter):
    seeds = []

    def handler(request):
        body = json.loads(request.content)
        seeds.append(body["options"]["seed"] if adapter == "ollama" else body["seed"])
        return httpx.Response(
            200,
            json={"message": {"content": "37"}}
            if adapter == "ollama"
            else {"choices": [{"message": {"content": "37"}}]},
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        registry,
        "http_client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    model = ModelConfig(
        name="fixture", adapter=adapter, model="test", base_url="http://localhost:9000"
    )
    for seed, parameters in [(12, {}), (99, {}), (12, {"seed": 7})]:
        system = SystemSpec(model_id=model.id, parameters=parameters)
        config = ExperimentConfig(name="seed", systems=[system], seed=seed)
        await registry.execute_system(
            system, model, None, get_tasks("starter-v1")[0], tmp_path, config, lambda e: None
        )
    assert seeds == [12, 99, 7]


@pytest.mark.asyncio
async def test_native_rejects_ignored_parameters_before_launch(tmp_path):
    agent = AgentConfig(name="cli", adapter="subprocess", executable=sys.executable)
    system = SystemSpec(agent_id=agent.id, parameters={"temperature": 0.7})
    config = ExperimentConfig(name="t", mode="native", systems=[system])
    result = registry.validate_system_config(system, None, agent, config)
    assert not result.compatible and "parameters" in " ".join(result.reasons)
    with pytest.raises(ValueError, match="parameters"):
        await registry.execute_system(
            system, None, agent, get_tasks("starter-v1")[0], tmp_path, config, lambda e: None
        )


def test_native_model_binding_is_not_claimed_controlled():
    model = ModelConfig(
        name="local",
        adapter="openai-compatible",
        model="same-name",
        base_url="http://localhost:1234/v1",
        api_key_env="LOCAL_KEY",
    )
    for adapter in ["codex-cli", "opencode-cli", "subprocess"]:
        agent = AgentConfig(name="cli", adapter=adapter, executable="fixture")
        system = SystemSpec(agent_id=agent.id, model_id=model.id)
        config = ExperimentConfig(name="t", mode="agent", systems=[system], isolation="workspace")
        result = registry.validate_system_config(system, model, agent, config)
        assert not result.compatible
        if adapter == "subprocess":
            assert "model_flag" in " ".join(result.reasons)
        else:
            assert "endpoint" in " ".join(result.reasons)
    agent = AgentConfig(
        name="cli", adapter="subprocess", executable="fixture", model_flag="--model"
    )
    assert not registry.validate_system_config(system, model, agent, config).compatible
    assert registry.validate_system_config(
        system, model, agent, config.model_copy(update={"mode": "native"})
    ).compatible
