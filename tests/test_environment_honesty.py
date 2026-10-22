import sys

from benchlab.adapters.registry import validate_system_config
from benchlab.schemas import AgentConfig, ExperimentConfig, SystemSpec


def test_native_host_execution_cannot_claim_docker_isolation():
    agent = AgentConfig(name="native", adapter="subprocess", executable=sys.executable)
    system = SystemSpec(agent_id=agent.id)
    config = ExperimentConfig(name="native", mode="native", systems=[system], isolation="docker")
    result = validate_system_config(system, None, agent, config)
    assert not result.compatible
    assert any(
        "workspace" in reason.lower() and "host" in reason.lower() for reason in result.reasons
    )
