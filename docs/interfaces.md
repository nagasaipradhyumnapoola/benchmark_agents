# CLI, REST and Python SDK

All interfaces use the same engine and persisted schema. Run `uv run bench-agents --help` and each subcommand's `--help` for exact options. Normal CLI records are JSON; diagnostics/errors are on stderr with nonzero status where appropriate.

| Command | Behavior |
| --- | --- |
| `bench-agents terminal` | Guided model and agent setup, real progress, results, comparison and ZIP export; see [Testing](testing.md) |
| `bench-agents demo` | Execute two explicit deterministic systems through real verification; negative fixtures retained |
| `bench-agents doctor` | Detect local runtime/storage/optional dependencies; installed does not imply exercised |
| `bench-agents models list/add/probe` | Inspect, register from a config file and probe endpoints |
| `bench-agents agents list/add/probe` | Inspect/register executables and probe discovery |
| `bench-agents benchmarks list` | List runnable benchmark packs and requirements |
| `bench-agents run --config experiment.json` | Validate, execute and independently verify; task failures exit 1 |
| `bench-agents run --model MODEL_ID --trials 3` | Evaluate registered endpoint with starter tasks |
| `bench-agents experiments list/show ID` | Retrieve persisted records and runs |
| `bench-agents compare RUN_A RUN_B` | Condition-aware comparison and uncertainty |
| `bench-agents report ID --format zip --out evidence.zip` | Export evidence; formats json/csv/html/zip |
| `bench-agents cancel ID` | Persist cancellation observed by the active worker |
| `bench-agents worker` | Process durable queue without browser; single daemon per workspace |
| `bench-agents ui` | Launch API and web from source checkout |
| `bench-agents ui --api-only` | Start REST API only, including from an installed wheel |

REST OpenAPI lives at `http://127.0.0.1:8000/docs` and `/openapi.json`. Main resources are `/api/models`, `/api/agents`, `/api/benchmarks`, `/api/experiments`, `/api/runs`, `/api/compare`, `/api/diagnostics`, `/api/settings` and `/api/metrics`. POST `/api/demo` queues a zero-credential experiment; POST `/api/experiments/validate` checks compatibility without launching. See the [shared contracts](contracts.md) for exact payloads and return shapes. IDs are opaque; list responses are arrays. Poll events by monotonic `after` sequence. Export endpoints are ordinary attachments.

Python example:

```python
import asyncio
from benchlab.sdk import Laboratory
from benchlab.schemas import ExperimentConfig, SystemSpec

async def main():
    lab = Laboratory()  # same BENCH_AGENTS_DATA_DIR as the API/CLI
    experiment = await lab.run(ExperimentConfig(
        name="Local configured model",
        systems=[SystemSpec(model_id="local-ollama")],
        trials=3,
    ))
    print(lab.store.list_runs(experiment["id"]))

asyncio.run(main())
```

`examples/sdk_demo.py` is credential-free. `Laboratory.report()` returns `(bytes, media_type, filename)`. Never load an untrusted plugin/import string or execute code from an imported config. `/api/import` performs schema validation only and never starts a job.
