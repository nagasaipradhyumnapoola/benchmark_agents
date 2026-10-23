# Shared implementation contracts (v1)

All HTTP paths begin `/api`. GET list endpoints return arrays, not wrapper objects. Error responses use FastAPI `detail`. All timestamps are UTC ISO strings. UUID strings identify records. Config schemas live in `src/benchlab/schemas.py` and must not be redefined by workers.

## Store

`Store(data_dir: Path)` creates `bench-agents.sqlite3`, `.data_dir: Path`, `.artifacts_dir: Path`, `.workspaces_dir: Path`.

- `list_models() -> list[dict]`; `save_model(config: ModelConfig) -> dict`; `get_model(id: str) -> dict`; `delete_model(id)`
- `list_agents()`, `save_agent(config: AgentConfig)`, `get_agent(id)`, `delete_agent(id)`
- `create_experiment(config: ExperimentConfig) -> dict`; `list_experiments() -> list[dict]`; `get_experiment(id) -> dict`; `update_experiment(id, **fields) -> dict`
- `create_run(experiment_id: str, manifest: RunManifest) -> dict`; `list_runs(experiment_id: str | None = None) -> list[dict]`; `get_run(id) -> dict`; `update_run(id, **fields) -> dict`
- `add_event(run_id: str, event: TraceEvent) -> dict`; `list_events(run_id: str, after: int = 0) -> list[dict]` event includes monotonic `sequence`.
- `add_result(run_id: str, result: TaskResult) -> dict`; `list_results(run_id: str) -> list[dict]`
- `add_artifact(run_id: str, name: str, content: bytes, media_type: str = 'text/plain') -> dict`; `list_artifacts(run_id: str) -> list[dict]`; `artifact_path(run_id: str, artifact_id: str) -> Path`
- `claim_next() -> dict | None` atomic queued→running experiment transition; `recover() -> int` marks interrupted jobs/runs and returns count.

Rows expose `id`, configs under `config`, experiment `name`, `mode`, `status`, `created_at`, `updated_at`, `demo`; run `experiment_id`, `system_id`, `system_name`, `trial`, `status`, `manifest`, `metrics`, `error`, `started_at`, `finished_at`. `get_*` raise KeyError when absent. New stores have empty inventories. Only an explicit demo request installs two labeled demo models (`demo-reference`, `demo-flawed`) idempotently; optional demo agents are test fixtures rather than startup data.

## Adapters / benchmarks

`benchlab.benchmarks.catalog.list_benchmarks() -> list[dict]` and `get_tasks(benchmark_id: str, task_ids: list[str] | None = None) -> list[TaskDefinition]`. Built-in id = `starter-v1`; 8–12 meaningful public tasks across reasoning, knowledge, multilingual, structured output, tool selection, multistep, recovery, safety and coding.

`benchlab.adapters.registry.execute_system(system: SystemSpec, model: ModelConfig | None, agent: AgentConfig | None, task: TaskDefinition, workspace: Path, config: ExperimentConfig, emit: Callable[[TraceEvent], None]) -> AdapterOutput` (async). Emits normalized events. `probe_model(config: ModelConfig) -> CompatibilityResult`, `probe_agent(config: AgentConfig) -> CompatibilityResult` async. No silent provider fallback; failing demo variant returns incorrect results.

`benchlab.verification.verify(task: TaskDefinition, output: AdapterOutput, workspace: Path, config: ExperimentConfig) -> VerificationResult` async; code checks require hardened Docker. Exact/schema/tool-policy/state verifiers execute in trusted core; no LLM judging. Never feed expected answers to provider prompts. `benchlab.sandbox.diagnostics() -> dict` sync and `run_python(code: str, test_code: str, timeout_seconds: float, memory_mb: int = 256, cpus: float = 1) -> dict` async. Sandbox refuses unavailable runtime.

## Engine

`Engine(store: Store)`; `validate(config: ExperimentConfig) -> CompatibilityResult` async checks IDs/capabilities/resources/budgets before queueing; `submit(config) -> dict` async validate+persist; `execute(experiment_id) -> dict` async; `work_once() -> bool` async; `recover() -> int`; `cancel(experiment_id) -> dict`.

Each system×trial gets a run, tasks execute serially initially. `config.systems` lists configurations; `system.model_id` for model/adapted agent, `agent_id` for agents, `label` optional. For agent comparisons same model enforced when controlled. Budget is total wall-clock per experiment, task timeout separate, token/cost budget if observable. Results persist output, verifier evidence and independent success; failures still count. Cancellation must interrupt an in-flight adapter await. State statuses: queued/running/completed/failed/cancelled/interrupted. Completed is orchestration completion, never synonymous with verification pass. Engine rehydrates ModelConfig/AgentConfig from store rows and resolves `get_tasks`. Demo engine still runs verifiers; no precomputed scores.

`analysis.summarize(results: list[dict]) -> dict`: total, passed, failed, success_rate, confidence_low, confidence_high (Wilson), duration_seconds, median_latency_seconds, p95_latency_seconds (null below 20), tokens, cost_usd, cost_per_success_usd, warning; null for unavailable measurements. `analysis.compare_runs(store, run_ids: list[str]) -> dict` returns runs/summary/task rows, comparable bool/reasons, paired differences and Pareto sets where justified. Fingerprint includes benchmark version/task IDs, environment, parameters and controlled/native mode; changes explicitly shown in ablation mode.

`reports.export_experiment(store, experiment_id: str, format: str) -> tuple[bytes, str, str]` JSON/CSV/HTML/zip; tuple content/media_type/filename. Include manifest, results/events/artifacts, demo marking, failure records and uncertainty; escape HTML, prevent spreadsheet formula injection, redact secrets.

## HTTP API

- GET `/health` -> {status,version}; GET `/overview` -> {experiments,models,agents,runs,metrics,recent_failures}
- GET/POST `/models`; GET/DELETE `/models/{id}`; POST `/models/{id}/probe`
- GET/POST `/agents`; GET/DELETE `/agents/{id}`; POST `/agents/{id}/probe`
- GET `/benchmarks`; GET `/benchmarks/{id}` -> benchmark with public task descriptions
- GET/POST `/experiments`; POST `/experiments/validate` (config body) -> CompatibilityResult; GET `/experiments/{id}` -> row + `runs`; POST `/experiments/{id}/cancel`; POST `/experiments/{id}/clone` (config overrides body) -> queued experiment
- POST `/demo` -> queued demo experiment; GET `/runs`; GET `/runs/{id}` -> row + results/events/artifacts; GET `/runs/{id}/events?after=0`
- GET `/runs/{id}/artifacts/{artifact_id}` -> safe FileResponse
- GET `/compare?run_ids=id1,id2` -> comparison; GET `/experiments/{id}/report?format=json|csv|html|zip` -> download
- GET `/diagnostics` -> runtime/storage/optional integrations, no credentials; GET `/metrics` -> typed metric definitions
- GET `/settings` -> public local settings; POST `/import` (JSON experiment config only; no execution until separately launched) -> validated config

Frontend same-origin Next.js rewrite `/api/:path*`→FastAPI localhost:8000. REST typed client uses TanStack Query with active-run polling. All twelve routes functional: `/`, `/models`, `/agents`, `/benchmarks`, `/experiments/new`, `/experiments`, `/compare`, `/replay`, `/optimize`, `/reports`, `/settings`, `/docs`. Dynamic experiment/run inspector can use search params. Empty overview guides model registration, optional agent setup and experiment creation. Demo execution is an explicit Documentation action. Export anchors same-origin. Model/agent forms use full config types, environment-var references for credentials. Config editing deletes/replaces only when no historical records depend on identity; prefer new registration version.
