"""Run with `uv run python examples/sdk_demo.py`. This measures pipeline behavior only."""

import asyncio
import json

from benchlab.sdk import Laboratory


async def main():
    lab = Laboratory()
    experiment = await lab.demo()
    runs = lab.store.list_runs(experiment["id"])
    print(json.dumps(lab.compare(*(run["id"] for run in runs)), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
