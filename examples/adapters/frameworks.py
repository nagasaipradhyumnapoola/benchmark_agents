"""Run installed evaluation frameworks with their native scores; never imports remote task code."""

import argparse
import asyncio
import json
from pathlib import Path

from benchlab.benchmarks.external import run_inspect_starter, run_lm_eval


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("framework", choices=["inspect", "lm-eval"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-args", default="")
    parser.add_argument("--tasks", default="hellaswag")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--allow-host-process", action="store_true")
    args = parser.parse_args()
    if args.framework == "inspect":
        result = await run_inspect_starter(
            args.model, args.output, allow_host_process=args.allow_host_process
        )
    else:
        result = await run_lm_eval(
            args.model,
            args.model_args,
            args.tasks.split(","),
            args.output,
            allow_host_process=args.allow_host_process,
            limit=args.limit,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
