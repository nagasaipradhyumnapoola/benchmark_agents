import os
import sys

from benchlab.adapters.registry import process_environment, validate_system_config
from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig, SystemSpec


def test_selected_endpoint_and_credential_bind_to_explicit_harness_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_PROVIDER_SECRET", "credential-private-test-value")
    model = ModelConfig(
        name="bound",
        adapter="openai-compatible",
        model="configured-model",
        base_url="http://localhost:1234/v1",
        api_key_env="TEST_PROVIDER_SECRET",
    )
    agent = AgentConfig(
        name="controlled",
        adapter="subprocess",
        executable=sys.executable,
        model_flag="--model",
        model_base_url_env="HARNESS_BASE_URL",
        model_api_key_env="HARNESS_KEY",
    )
    system = SystemSpec(model_id=model.id, agent_id=agent.id)
    config = ExperimentConfig(name="binding", mode="agent", systems=[system], isolation="workspace")
    assert validate_system_config(system, model, agent, config).compatible
    environment = process_environment(agent, tmp_path, model)
    assert environment["HARNESS_BASE_URL"] == model.base_url
    assert environment["HARNESS_KEY"] == os.environ["TEST_PROVIDER_SECRET"]
    assert "TEST_PROVIDER_SECRET" not in environment


def test_controlled_harness_rejects_name_only_model_binding():
    model = ModelConfig(
        name="bound",
        adapter="openai-compatible",
        model="configured-model",
        base_url="http://localhost:1234/v1",
    )
    agent = AgentConfig(
        name="name-only", adapter="subprocess", executable=sys.executable, model_flag="--model"
    )
    system = SystemSpec(model_id=model.id, agent_id=agent.id)
    config = ExperimentConfig(name="binding", mode="agent", systems=[system], isolation="workspace")
    result = validate_system_config(system, model, agent, config)
    assert not result.compatible
    assert any("model_base_url_env" in reason for reason in result.reasons)
