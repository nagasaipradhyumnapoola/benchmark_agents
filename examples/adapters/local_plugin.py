"""Trusted local registration example. Import before creating Engine/API application."""

from benchlab.adapters.registry import register_agent_adapter, register_model_adapter
from benchlab.benchmarks.catalog import register_benchmark
from benchlab.schemas import AdapterOutput, CompatibilityResult, TaskDefinition


async def execute(system, model, agent, task, workspace, config, emit):
    # Replace this explicit demo with your real provider. Never read task.expected here.
    return AdapterOutput(text="example deterministic demo", metadata={"demo": True})


async def probe(config):
    return CompatibilityResult(compatible=config.demo, warnings=["Example demo only"])


def register():
    register_model_adapter("example-local", execute, probe, version="1.0")
    register_agent_adapter("example-agent", execute, probe, version="1.0")
    register_benchmark(
        "example-pack",
        [
            TaskDefinition(
                id="example",
                name="Example",
                category="demo",
                prompt="Return example deterministic demo",
                verifier="exact",
                expected="example deterministic demo",
            )
        ],
        {"name": "Example pack", "version": "1.0.0", "installed": True, "available": True},
        version="1.0",
    )
