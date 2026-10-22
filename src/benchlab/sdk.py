"""Small Python SDK using the same durable engine as the CLI and HTTP server."""

from __future__ import annotations

from pathlib import Path

from benchlab.schemas import ExperimentConfig
from benchlab.settings import Settings


class Laboratory:
    def __init__(self, data_dir: str | Path | None = None):
        from benchlab.engine import Engine
        from benchlab.store import Store

        self.store = Store(Path(data_dir) if data_dir else Settings.from_env().data_dir)
        self.engine = Engine(self.store)

    async def run(self, config: ExperimentConfig) -> dict:
        experiment = await self.engine.submit(config)
        return await self.engine.execute(experiment["id"])

    async def demo(self) -> dict:
        from benchlab.service import demo_config

        return await self.run(demo_config())

    def compare(self, *run_ids: str) -> dict:
        from benchlab.analysis import compare_runs

        return compare_runs(self.store, list(run_ids))

    def report(self, experiment_id: str, format: str = "json") -> tuple[bytes, str, str]:
        from benchlab.reports import export_experiment

        return export_experiment(self.store, experiment_id, format)
