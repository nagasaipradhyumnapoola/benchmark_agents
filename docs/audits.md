# Verification and release audit — 2026-10-23

This is the integration audit for the actual implementation, superseding intermediate worker checkpoints. Status: **tested development build, 0.1.0; V1.0 release gate remains blocked**. No real model capability score, credentialed native-product run or functioning Docker sandbox is claimed.

## Evidence ledger

| Check | Actual result | Evidence / reproduction |
| --- | --- | --- |
| Python suite including optional Inspect | 231 passed, 4 skipped; three upstream deprecation warnings | `uv run pytest --cov=benchlab --cov-report=json:docs/evidence/coverage.json`; 86% statement coverage |
| Static Python checks | Ruff and mypy pass | `uv run ruff check src tests examples scripts`; `uv run mypy src/benchlab` (29 source files) |
| Frontend components/forms/navigation | 33 passed | `npm test --prefix apps/web` |
| Frontend type/format/build | pass | `npm run typecheck --prefix apps/web`; `npm run format:check --prefix apps/web`; `npm run build --prefix apps/web` |
| Browser integration | 21 passed, 0 failures/skips/flakes | [browser-results.json](evidence/browser-results.json); real API on 8000 and production web on 3000 |
| Full host-safe deterministic suite | Reference 9/9, deliberately flawed 0/9 | [full-offline.json](evidence/full-offline.json); `uv run python scripts/full_offline.py` |
| Two independent provider HTTP endpoints | pass | `tests/test_http_integration.py`: actual loopback HTTP requests, model/seed/usage, independent verification, persisted comparison |
| Controlled agent pair | pass | Same test file: two real Python subprocess harnesses call the selected loopback endpoint through explicit model/URL bindings |
| Inspect upstream framework | pass with mockllm, explicit demo | `tests/test_external.py`; native scorer/log execution rejects deliberately wrong responses |
| lm-eval integration | CLI, subprocess-ingestion and result contracts pass using local fixtures | Full upstream dataset/model execution not run; no upstream score claimed |
| Python packaging | sdist and wheel build | `uv build` |
| Isolated wheel installation | pass | New venv; import from site-packages; SDK demo; installed CLI; API on 8001; four exports; [fresh-install.json](evidence/fresh-install.json) |
| Clean web installation | pass | Disposable `.bench-agents/fresh-web`, copied source/lockfiles, `npm ci --ignore-scripts`, production build, standalone startup on 3001, `/api/health` proxy response |
| One-command startup | pass | [cli-ui.json](evidence/cli-ui.json); actual `bench-agents ui` launches API and built dashboard through Node, no cmd shell; browser E2E runs against this startup |
| Dependency audits | no known vulnerabilities reported in tested runtime set | [python-audit.json](evidence/python-audit.json), [web-audit.json](evidence/web-audit.json), [browser-dependency-audit.json](evidence/browser-dependency-audit.json) |
| Docker configuration | Compose validates | `docker compose config --quiet`; no Docker socket mount |
| Docker runtime / container image build | **BLOCKED** | Desktop Inference-manager socket startup error; four explicit opt-in runtime tests skipped, not passed |
| Real-model smoke | **BLOCKED — endpoint unavailable** | [endpoint-status.json](evidence/endpoint-status.json); no weights loaded or paid provider substituted |

Dependency audits are point-in-time checks, not guarantees. Upstream Starlette TestClient and Inspect retry API deprecations remain warnings rather than failures. Windows was exercised locally; Linux/macOS execution and hosted GitHub Actions results are not claimed. CI includes Linux/Windows backend jobs.

The current refinement also verifies an empty default workspace ([empty-start.json](evidence/empty-start.json)), guided terminal registration → model/agent pairing → HTTP generation → independent verification → ZIP export (`tests/test_terminal_flow.py`), and the same complete user journey in the browser. The 18 browser checks ran against a separate fresh data directory. The default live workspace retains zero saved models, agents, experiments and runs; test fixtures remain confined to automated checks and explicit demonstrations. New validation regressions confirm that rejected credential-bearing URLs and unknown secret fields are not repeated in API error responses. A cp1252 regression covers redirected Windows terminal startup.

## Pass 1 — requirements traceability

| Requirement in the original brief | Implementation / evidence | Status and practical boundary |
| --- | --- | --- |
| 1: local-first mission and six stable abstractions | `schemas.py`, `plugins.py`, `engine.py`, architecture/contracts docs | Implemented; trusted version-1 extensions rather than universal compatibility |
| 2–3: inspect, preserve, plan, install/use relevant skills | `AGENTS.md`, `docs/requirements.md`, plan, `.agents/skill-sources.json`; global skill installation report | 193 requested skills installed, 7 existing preserved; relevant guidance applied. Impeccable source critique used; unreviewed binary launcher not executed |
| 4: Python/API/CLI, Next/React/TS/shadcn, SQLite/artifacts, Docker, telemetry, packaging/CI | `src/benchlab`, `apps/web`, lockfiles, Dockerfile/Compose, `.github/workflows/ci.yml` | Default stack implemented/tested. DuckDB/Parquet/MLflow extras are optional dependencies, not claimed automatic data backends or tracing integrations. PostgreSQL/object storage not included |
| 5: established frameworks and suite setup | `benchmarks/external.py`, `docs/integrations.md`, framework tests | Executable Inspect wrapper; lm-eval subprocess/ingestion wrapper. Harbor, Terminal-Bench, SWE-bench, Lighteval, OSWorld-V2 and AgentDojo are explicitly researched/unavailable references |
| 6A: model comparison and categories | provider adapters, starter catalog, HTTP wire tests, comparison/category table | OpenAI-compatible/Ollama paths implemented; real endpoint smoke blocked. Reasoning/knowledge/Spanish/JSON/coding/file-state fixtures. Tool/recovery fixtures evaluate structured plans. Multimodal and live tool environment benchmarks unsupported |
| 6B: agent comparison | subprocess/Codex/OpenCode argv/parsers; real two-harness HTTP test | Controlled generic harness and native-product paths. Credentialed Codex/OpenCode execution unverified. No claims of hidden thought, native tool interception or general autonomous capability |
| 6C: compatibility | Engine.validate, discovery/probe, static binding validation, UI preflight | Availability/model IDs, declared capabilities/context, auth requirements, selected-model binding, host permissions and Docker gates. Generation/tool/modality support is not inferred from discovery |
| 6D: seven experiment modes | config modes, builder, optimization clone, repeated trials, comparisons | Model, controlled agent, native, matrix, ablation, reliability and baseline workflows. Every matrix system is explicit. Incompatible conditions and budget-starved runs cannot receive strict paired rankings |
| 6E: configuration and preflight | strict Pydantic schema, builder advanced JSON, CLI JSON/TOML | Budgets/timeouts/retries/tags/resources/task subsets. Unsupported builtin tool policies/ignored native parameters are rejected. Trusted tool-aware adapters may implement explicit policies |
| 6F: execution lifecycle | transactional queue, OS ownership locks, cancellation observer/recovery, store/engine tests | Implemented; supported deployment is one worker daemon per data directory |
| 6G: independent verification | exact, JSON/schema, file state, Docker Python; positive/negative verifier tests | Deterministic objective checks implemented. Human-review/model-judge rubrics are not built in; custom trusted verifiers can implement them. Docker runtime blocked |
| 7: normalized traces, replay, diagnosis and optimization | events/artifacts, replay filters/inspector, baseline-linked analysis | Observed operations only; CLI final-output parsing cannot expose every native tool/command. Taxonomy maps confirmed failures conservatively, preserves raw codes and uses unknown for unconfirmed causes. Ablations pair corresponding baseline system slots and enumerate changed knobs |
| 8: typed metrics, statistics, categories/Pareto | telemetry registry, analysis, comparison screen, statistical tests | Wilson, median/tail threshold, paired exact McNemar, category summaries, cost/quality/latency Pareto membership. Unknown usage/cost/resource/energy/intervention values remain unavailable. Provider-priced cost is calculated/estimated |
| 9: versioned data/plugin contracts | schemas and typing protocols; model/agent/benchmark and environment/verifier/export registration | Implemented with working extension examples and conformance tests. HTTP cannot import code; custom exporters use SDK with binary output. Plugins run with application privileges |
| 10: security/privacy | `SECURITY.md`, negative tests, runtime/resource controls, report escaping | Reviewed/fixes applied; Docker runtime gate still blocked; no formal anti-cheat or Internet-facing authentication claim |
| 11: design system/concepts | `docs/design.md`, concept PNG, Geist/shadcn/Tailwind, screenshot evidence | Code-native UI; graphite/black, real tables/timeline/plots. Manual Impeccable-inspired critique; no claim its binary audit ran |
| 12.1–12.4: overview/model/agent/library | overview/registry/benchmarks components | Inventory, real registration/probes, history, task requirements/filtering and launch navigation. Unsupported upstream suites stay out of executable choices |
| 12.5–12.6: builder/live monitor | builder/experiments components, API polling/cancel | Real validation/launch/progress/errors/timing. Host diagnostics are not per-run resource samples |
| 12.7–12.9: comparison/replay/optimization | comparison/replay/optimize components, E2E | Actual persisted evidence, category summaries, uncertainty, failure rows, replay/compare navigation, immutable clone and changed-condition analysis. Arbitrary memory/router/reviewer strategies require a supporting extension, not inert UI flags |
| 12.10–12.12: reports/settings/onboarding | reports/settings/documentation components | Real downloads, manifests, search, runtime diagnostics, schema-only import, setup/extension docs. Import never executes configuration |
| 13: responsive/accessibility | Playwright all 12 routes × 4 widths, axe on overview/builder/replay, component focus test | No viewport overflow in tested routes; internal technical-table scrolling is intentional. Broad assistive-technology certification is not claimed |
| 14–16: CLI/SDK/REST, maintainable monorepo, original task collection | CLI tests, fresh install, interfaces docs, starter and framework tests | Shared engine/storage; 10 original public fixtures (8 default text, 1 filesystem, 1 Docker). No fabricated upstream/real scores |
| 17: automated tests/browser/quality | evidence ledger above | Local tests/checks pass; four real Docker cases are skipped explicitly |
| 18: five reviews | this document, screenshots and fresh-install evidence | Separate requirement/correctness/security/UI/install passes performed. Independent backend review reproduced issues and fixes; reviewer account usage limit prevented full independent approval. No such approval is claimed |
| 19: open-source readiness | Apache LICENSE, NOTICE and retained shadcn MIT notice, contributor/security/changelog/templates/CI | Prepared for the authorized main-branch consolidation; no tagged V1.0 or package publication claimed |
| 20–23: build strategy, prohibitions, acceptance and handoff | runnable app/evidence, this ledger, setup commands | Implemented and verified within available resources; V1.0 remains blocked by the external runtime/endpoint gates and native-product credentialed verification |

## Pass 2 — benchmark correctness

The Agent Hub/matrix expansion adds 2×2 execution with independent endpoint credentials, session-key rotation/redaction, 48 Community cases, 55 standalone registry cases, cookie-proxy/import checks and source-integrity regressions. The real browser publishes a Python release, imports its pinned source, pairs it with a loopback HTTP endpoint, verifies its task and shares the derived version-specific result. Registry reports remain self-reported. The shared registry is self-hostable development software; no public hosted deployment, universal framework installer, moderator system or production-scale identity service is claimed.

Deliberate negative fixtures fail through the same verifiers as successful fixtures. Full offline execution covers every host-safe task. Real loopback HTTP tests exercise two independent endpoints and two subprocess harnesses, provider IDs, prompt isolation, seed forwarding, usage accounting, persistence and comparisons. These are protocol fixtures, not real intelligence measurements.

Regression checks cover fresh task workspaces, immutable model/config identities, repeated trials, retries/deadlines, unknown usage under caps, cancelled/interrupted state, concurrent execution ownership, recovery with live owners, independent file-state checks, zero-exit code false positives, report escaping/formula safety, incompatible conditions, ordered-budget starvation, category/recovery metrics, and extension cleanup. Manifest data includes task-definition SHA-256, runtime package versions, exact config/model/agent snapshots and fixed Docker verifier image identity when applicable. Source revision remains optional/unavailable unless supplied by packaging; upstream provider model aliases can still change and require user-managed revision pinning.

## Pass 3 — security/reliability

Fixed discovered issues: concurrent double execution; cross-engine cancellation; shutdown cancellation propagation; ignored model/seed/parameter binding; host processes falsely claiming Docker; Windows shell launchers; Windows OS environment casing breaking TLS; budget-starved comparisons; cross-system ablation attribution; early-exit coding false success; focus-inaccessible evidence scrollers; misleading README examples.

API Host/Origin checks and loopback defaults, environment-name credentials, best-effort ingestion/export redaction, symlink/path containment, artifact caps, escaped previews/HTML and CSV formula neutralization were inspected and negatively tested. Container contracts restrict privileges, resources and external network without mounting host paths. No Docker reset, user-data deletion, model download or paid dependency was introduced. Trusted native processes/plugins remain privileged; Docker is not an absolute boundary. Public tests are not secret or formally resistant to malicious Python introspection. Review `SECURITY.md` before evaluating untrusted code.

## Pass 4 — UI/UX

The final refinement applies Impeccable to the established graphite system: Discover & share navigation, a directory with filter rail and source metadata, grouped publication fields, release section links and mobile stacking. Desktop and 390px directory captures were inspected. Browser tests now cover fourteen routes at four widths and axe scans on overview, builder, Community, Hub directory, populated release and replay. The mechanical detector returned no findings. These checks do not establish every accessibility criterion. In-app documentation includes publication/import/model setup and result-sharing instructions.

Inspected actual desktop overview/comparison/replay and 390px loaded overview screenshots. An initial mobile screenshot captured loading skeletons; screenshot capture now waits for persisted experiment content. Internal scrolling preserves legible technical tables. Fixed keyboard focus for JSON/text evidence, preserved dark contrast and native text, and added real category comparisons. E2E covers first-run instructions, demo, model/agent forms, benchmark/builder, execution/cancel/failure, compare, replay tabs/filters, ablation, exports, persisted refresh, settings import, mobile sheet and error/empty states. Axe reports no violations in the three tested major workflows; it does not prove every accessibility criterion.

The refined website uses a quieter typographic Bench Agents identity, ruled sections, actual inventory counts, clear setup ordering, optional agent pairing and a single-task first test. Technical JSON sits behind details disclosures. Saving a registration is distinguished from confirming compatibility; run completion is distinguished from passed-task count. Native agent links select native mode and hide shared endpoint pairing. Interaction references were the official [Inspect log viewer](https://inspect.aisi.org.uk/log-viewer.html) for sample drill-down and [Promptfoo getting started](https://www.promptfoo.dev/docs/getting-started/) for provider-to-evaluation flow. The original terminal banner uses bold block lettering with a muted gold accent, informed by the hierarchy in the official [Hermes startup banner](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/banner.py); its code and artwork were not copied.

## Pass 5 — install/release

Built wheel/sdist and installed the wheel into a new venv without source imports. Exercised SDK positive/negative demo, installed CLI shared state, four exports and a real temporary API process, then stopped that process. Copied web source and lockfiles to a disposable directory, resolved clean dependencies, built every route, started standalone server on 3001, verified the web/API proxy and stopped the temporary web server. The main local workspace remains available on 3000/8000. Windows build failure from a running standalone preview locking `.next/standalone` was resolved by stopping the owned preview before rebuilding.

The Windows one-command launcher now resolves Node and the installed Next entry point directly, avoiding cmd launcher failures. At default API port 8000 it uses an existing production build; otherwise it starts dev mode. The custom-port dev API/proxy/demo passed, but the first cold page compile exceeded a 45-second request on this low-memory host. The built dashboard responds immediately and is used by the full browser suite. README installation now builds before `bench-agents ui`. Build/dev/start scripts disable Next.js telemetry. Final focused API and CLI regressions also passed after list ordering and launcher fixes.

## Remaining gates and exact setup

1. **Real-model smoke: BLOCKED — endpoint unavailable.** No 7B/14B weights were loaded. Supply an already authorized, affordable/local service. OpenAI-compatible base URL format: `http[s]://HOST:PORT/v1` (no embedded credentials/query); endpoints must implement `GET /models` with the exact ID in `data[].id` and `POST /chat/completions`. Set `ModelConfig.model` to that exact provider-advertised ID. The supplied config uses `api_key_env: BENCH_AGENTS_PROVIDER_KEY`; set that variable only in the backend shell if authentication is required, or remove api_key_env for a credential-free local service. Edit `examples/openai-compatible-model.json`, then run:

   ```powershell
   uv run bench-agents models add examples/openai-compatible-model.json
   uv run bench-agents models probe configured-endpoint
   uv run bench-agents run --model configured-endpoint --benchmark starter-v1 --trials 1 --name "Authorized real-model smoke"
   ```

   Ollama format: base URL `http://127.0.0.1:11434`, exact pre-existing model name from `/api/tags`, optional api_key_env only if that endpoint actually requires it. Do not start or download a model without checking memory and authorization. The current template ID is deliberately a placeholder, not a claimed working model.

2. **Docker runtime: BLOCKED.** Repair/start a supported Linux Docker daemon without resetting data. Explicitly review/pull `python:3.12.10-slim`; set `BENCH_AGENTS_TEST_DOCKER=1` and run `uv run pytest tests/test_sandbox.py -q`. Then test image builds/Compose and coding verification. Keep the four runtime tests unpassed until they actually run.

3. **Credentialed native products: UNVERIFIED.** Generic subprocess wire execution is verified. Codex/OpenCode discovery/argv/parsers are tested, but each product needs an explicit authorized provider and isolated profile. Preserve native vs controlled labeling and the dual host-process opt-in. No existing user login files are copied implicitly.

Large upstream suite runs, multimodal/desktop environments, full native tool instrumentation, hardware/energy metering, and PostgreSQL/object storage are outside the advertised tested built-ins. They are visible limitations, not simulated capabilities. Do not label this checkout V1.0 release-ready until the applicable remaining acceptance gates are exercised.
