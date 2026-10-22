# BenchLab architecture and design contract

## Intent and implementation authority

The complete user brief is preserved in `docs/requirements.md`. The user explicitly directs autonomous implementation and sensible decisions without an additional design approval round; that direction overrides optional skill approval gates. The existing repository contains only README and AGENTS.md. Work proceeds on `feat/benchlab-v1`; every commit is pushed.

## Decisions

Use one Python distribution in `src/benchlab/`, subdivided by stable domain boundaries, and a separately built Next.js app in `apps/web/`. An async engine owns job execution; SQLite owns durable records; CLI, API and web all use the same service. SQLite transactions claim queued work; interrupted in-flight work is recorded accurately on recovery. No external account is required. Experimental upstream integrations remain explicitly labeled and retain their own scorers.

Alternatives: multiple Python workspace distributions increase packaging friction without independent release requirements; a hosted queue/database violates the simplest local-first experience. Keep repository/storage protocols extensible; SQLite is the tested default. Python 3.12 is the reproducible environment for optional scientific dependencies. Generated code never runs directly on the host; Docker is required for code verification. Native CLI agent execution requires explicit host-process authorization.

## Six stable abstractions

System under test = `ModelConfig`/`AgentConfig` + versioned adapter; objective = `TaskDefinition`; environment = isolated workspace + `EnvironmentProvider`; observations = append-only `TraceEvent`; verifier = independent `VerificationResult` contract; record = immutable `RunManifest`, `ExperimentConfig` and persisted run/results.

## Ownership

- Root: schemas, settings, API, CLI/SDK, integration tests, docs, release, coordination and commits.
- Core worker: `store.py`, `engine.py`, `analysis.py`, `reports.py`, core tests.
- Adapter worker: `adapters/`, `benchmarks/`, `verification.py`, `sandbox.py`, adapter/verifier tests and integration research.
- Frontend worker: `apps/web/`, frontend tests and design references.

Workers do not modify other owned files or commit; root integrates and pushes tested commits. Shared changes are coordinated explicitly.

## Primary interfaces

`Store(data_dir: Path)` provides model/agent catalog CRUD and durable experiments, runs, results, events and artifacts. `Engine(store)` provides `validate(config)`, `submit(config)`, `execute(experiment_id)`, `work_once()`, `recover()`, `cancel(experiment_id)`. Synchronous store operations return dictionaries; domain configuration and task objects are Pydantic. Engine methods are async except cancel/recover, which may be synchronous. Workspaces are under the store's data directory. See `docs/contracts.md` for exact signatures and HTTP payloads.

## Security and measurement

Bind to loopback; restrict Origin/Host; no shell strings through API. Credentials are referenced by environment variable name, never stored or returned. Explicit host execution opt-in, strict Docker resource/network policy, path containment, symlink rejection, capped artifact size and redaction at ingestion/export. Public fixtures are public. Demo adapters are never listed as actual intelligence measurements. Usage and cost remain null when unobserved; hardware/energy unavailable stays unavailable. Native-product and controlled comparisons carry separate condition fingerprints and are not silently combined.

## Visual contract

Brand: BenchLab / Experimental systems laboratory. Deep black canvas (#0b0c0e), graphite surfaces (#131518), charcoal elevations (#1b1e22), neutral borders (#2b2e33), off-white text (#f1f2f3), secondary silver (#a5aab3). One reserved subdued semantic palette for status and charts. Geist Sans + Mono; 13–16px body, 28–34px page titles. 4px spacing scale, 6–10px radius. Restrained persistent 232px sidebar, compact utility header and max-width content; overview uses a genuine experiment activity panel, narrow metric strip, task evidence table and capability inventory. Comparison uses statistical plots/tables; replay uses timeline/inspector. No decorative scores, no bright gradients, no identical card grid for every screen.

At 1024px condense navigation; 768px use a sheet; 390px stack panels, scroll tables inside contained regions and keep 44px targets. Keyboard-visible focus, explicit labels, accessible modal titles, reduced motion, genuine loading/error/empty states. shadcn Radix primitives, Lucide icons, semantic Tailwind v4 tokens. API polling while jobs are active, durable page refresh.

## Verification and release gate

TDD backend/schema/security and lifecycle tests; real backend browser flows; test at 1440/1024/768/390; independent failure fixtures; fresh disposable installation; five audit passes with evidence. Current known external requirement: Docker Linux daemon is stopped. Hosted credentials/local model downloads are not assumed. Never mark an unexercised provider or large benchmark verified. Version remains 0.1.0 development until all acceptance criteria pass.
