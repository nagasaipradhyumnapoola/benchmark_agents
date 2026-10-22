"""Exercise every host-safe deterministic fixture and report Docker code as blocked."""

import asyncio
import json
from pathlib import Path

from benchlab.benchmarks.catalog import TASKS
from benchlab.engine import Engine
from benchlab.schemas import ExperimentConfig, ModelConfig, SystemSpec
from benchlab.store import Store


async def main():
    store = Store(Path(".benchlab/full-offline"))
    systems = []
    for variant in ["reference", "flawed"]:
        model = store.save_model(
            ModelConfig(
                id=f"full-demo-{variant}",
                name=f"Full offline demo {variant}",
                adapter="demo",
                model=variant,
                capabilities=["text", "workspace"],
                demo=True,
            )
        )
        systems.append(SystemSpec(model_id=model["id"]))
    task_ids = [task.id for task in TASKS if not task.requires_execution]
    engine = Engine(store)
    experiment = await engine.submit(
        ExperimentConfig(
            name="Full deterministic offline pipeline audit",
            systems=systems,
            task_ids=task_ids,
            demo=True,
            isolation="workspace",
        )
    )
    await engine.execute(experiment["id"])
    runs = store.list_runs(experiment["id"])
    summaries = [
        {
            "system": run["system_name"],
            "tasks": len(store.list_results(run["id"])),
            "passed": sum(result["passed"] for result in store.list_results(run["id"])),
        }
        for run in runs
    ]
    assert (
        len(runs) == 2 and summaries[0]["passed"] == len(task_ids) and summaries[1]["passed"] == 0
    )
    assert len(task_ids) == 9
    print(
        json.dumps(
            {
                "status": "passed",
                "demo": True,
                "meaning": "Execution-pipeline verification only, not model intelligence",
                "experiment_id": experiment["id"],
                "runs": summaries,
                "blocked_tasks": [
                    {
                        "id": task.id,
                        "reason": "Requires a functioning Docker Linux sandbox; host fallback prohibited",
                    }
                    for task in TASKS
                    if task.requires_execution
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
