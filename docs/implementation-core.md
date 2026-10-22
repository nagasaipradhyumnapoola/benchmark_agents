# Core implementation checkpoint

Implemented in `src/benchlab/store.py`, `engine.py`, `analysis.py`, and `reports.py` against `docs/contracts.md`.

## Durable records and ownership

SQLite WAL stores configuration snapshots, experiments, immutable run manifests, append-only results/events and artifact metadata. Demo model/agent inventory is seeded idempotently. Historical configuration IDs cannot be edited/deleted once referenced by an experiment. Queued jobs are claimed in an immediate SQLite transaction. Status mutations also run in immediate transactions; terminal cancellation cannot be overwritten by stale completion. An OS file lock per experiment prevents duplicate execution by API/CLI engine instances and is released by process termination. Recovery skips active owners, marking abandoned running experiments/runs interrupted.

Events use per-run monotonic sequence numbers allocated under a write transaction. Artifacts are restricted to audited UTF-8 content, redacted at ingestion, capped at 10 MiB, and stored under generated UUID filenames. Path traversal, ambiguous filenames, symlinks and cross-run artifact IDs are rejected. Run workspaces are separately created per run/task; executable task verification is delegated to the hardened verifier/sandbox implementation.

## Execution and measurements

Every system × trial creates a persisted manifest/run. Selected tasks execute serially. Compatibility checks include catalog IDs, adapter probes, demo/real segregation, capabilities, controlled agent model consistency, Docker availability for code tasks and two host-process opt-ins. Default starter tasks exclude code and therefore permit the offline demonstration without Docker.

The experiment wall-clock deadline bounds each adapter plus verifier await; task timeouts and retry limits are separate. Verification failures never become successes from a zero process exit. Adapter exceptions/timeouts and skipped budget tasks remain failure records. A verifier exception does not repeat a billable adapter call. Usage is charged immediately when observed; unavailable usage under an enforced token/cost budget stops subsequent tasks. A provider can exceed a token/cost budget within a single request before reporting its usage; this is an observed-usage stop policy, not a provider-side hard spending guarantee.

Cancellation interrupts an adapter await, records an in-progress cancellation result, and updates persisted statuses. A persisted cancellation observer also interrupts execution when cancellation comes from a different engine/CLI process; task boundaries check cancellation and yield to cooperative scheduling. Cancellation leaves partial execution visible and does not invent results for unattempted future systems.

Summaries use Wilson 95% intervals, median latency, p95 only with at least 20 latency samples, and null for unavailable tokens/cost. Comparisons require distinct completed runs with matching nonempty condition fingerprints and matching task sets. Controlled agent conditions include the selected model. Fingerprints include benchmark/task versions, environment/resources, mode, parameters, seed, timeout and budgets. Paired exact McNemar calculations are exploratory, without multiple-comparison correction; task independence is a limitation. Pareto membership requires observed quality/cost/latency and actual dominance.

## Exports

JSON and HTML include complete records, manifests, failures, event/artifact metadata, uncertainty and demo provenance. CSV includes experiment metadata even before execution, per-task observations, manifest/events/artifacts/summary JSON columns, and confidence bounds. Spreadsheet-leading formulas receive an apostrophe. HTML escapes every embedded record. ZIP includes all three reports and redacted artifact contents. Stored/exported credentials are redacted.

## Evidence and limitations

Tests were introduced before module implementation and failure regressions were observed before their fixes. Core tests cover persistence/reopen, seeded inventory, transactional concurrent queue claims, immutable identities/manifests, monotonic events, artifact containment/redaction/size limits, terminal state protection, multi-system trials, deliberately incorrect demo results, local and cross-engine cancellation, concurrent ownership/recovery, timeout retries, full budget failure accounting, failed-verifier usage accounting, controlled-model fingerprints, Wilson calculations, paired/Pareto comparisons, null metrics, HTML escaping, CSV formula safety, and ZIP exports.

Latest full suite checkpoint before final CSV/status regression additions: **49 passed, 4 skipped**, with upstream Starlette/Inspect deprecation warnings. Final verification results are reported to the parent integrator separately. Core Ruff and mypy checks were run; Windows OS-lock branch exercised here. POSIX lock branch is implemented but requires Linux CI verification. Real hosted providers, actual model intelligence, CLI products and Docker execution are not claimed exercised by these core demo tests. Optional provider/framework/sandbox evidence belongs to the adapter and integration audit.

No commits created by this worker; root owns integration, commits and immediate pushes.
