# Multiple models and agents implementation plan

> **For agentic workers:** Use subagent-driven-development for the independent backend and frontend tasks, with root integration and review. User authorization persists: implement autonomously, keep only main, push every commit immediately.

**Goal:** Let a normal user connect local or hosted models and benchmark multiple agents against multiple models using explicit, reviewable pairs.

**Architecture:** Reuse the durable engine's explicit SystemSpec list. Build the selected models × compatible custom agents on the website and terminal, cap at 16 systems, preview tasks × trials × pairs, then run through existing preflight and verification. Execute pairs sequentially under the total budget to respect the user's memory constraint. Preserve native products in separate native mode. Support environment references and write-only API-key entry held only in process memory.

**Tech stack:** Existing Python/FastAPI/Pydantic, Rich/Typer, React/Next.js; no additional dependency or paid service.

## Constraints and rulings

- Ruling: user already opted for autonomous implementation and main as the only branch; work directly on main and coordinate all commits in root.
- Ruling: use all selected model-agent combinations with an explicit preview, rather than silently selecting a single shared model. A matrix contains at most 16 unique explicit pairs.
- Local means an existing endpoint; never start inference, load weights or download models. Hosted endpoints use the supported OpenAI-compatible protocol. Keep actual endpoint and exact model ID configurable.
- Optional ModelConfig.connection_type is local/hosted/null metadata only; execution still follows the selected adapter and URL.
- Entered keys remain in backend/terminal memory and are referenced by generated BENCH_AGENTS_SESSION_* names in persisted configuration. Never save or return the secret. Re-entry after restart is explicit. Existing environment references remain supported.
- All current host-process double opt-ins, output verification, budget/cancellation rules and real-model/Docker verification gates remain in force.
- Browser tests use isolated data. Leave the live default workspace empty.

## Task 1: Backend matrix and model connection contracts

Owner: backend implementer. Files: credentials.py (new), settings.py, service.py, schemas.py, api.py, adapters/registry.py, tests/test_model_connections.py and tests/test_matrix.py. Write failing tests first.

Interfaces: POST /api/models/connect receives {config: ModelConfig, api_key?: string|null}, returns the saved registration; POST /api/models/{id}/credential receives {api_key: string} and returns {configured: true, scope: "session"}. Keys must be 1–8192 characters and are write-only. credentials.remember_key(value, reference=None) -> reference, get_key(reference) -> str|None, forget_key(reference), secret_values() -> iterable. service.connect_model(store, model, api_key=None) -> saved registration. References use BENCH_AGENTS_SESSION_ plus UUID hex. Resolution/redaction cover provider discovery/generation and explicit agent key binding. Matrix preflight rejects missing pair members, duplicates and native products. Prove two models × two agents with real HTTP/subprocess calls.

- [ ] Failing API key persistence/redaction/re-entry tests and matrix pairing tests.
- [ ] Implement contracts and prove positive/negative behavior without external inference.
- [ ] Static checks and focused tests; report exact results to root; no commits.

## Task 2: Website selection and credential UX

Owner: frontend implementer. Files: apps/web/src/** and apps/web/tests/** only. Write failing component tests first. Root owns build/E2E/docs.

Add local/hosted connection choice and no-key/session-key/environment authentication. Use backend interfaces above. Existing model registration aliases remain supported server-side. Re-enter a forgotten session key from the model inspector. Matrix mode exposes model and controlled agent multi-selection, generates explicit pairs, previews the selected systems and task/trial count, gates empty/oversized selections and excludes native products. Clear validation whenever selection changes. Preserve current model, single-shared-model agent, native and demo behavior. Avoid exposing expected task answers in selection UI.

- [ ] Failing 2×2 selection, native exclusion, limit and session-key form tests.
- [ ] Implement forms, pair preview and understandable mode names using current styling.
- [ ] Frontend tests/typecheck/format; report results; no build/commits.

## Task 3: Terminal, integration and review

Owner: root. Files: terminal.py, terminal_ui.py, terminal tests, tests/e2e, fixture servers, README/testing/configuration/audit documentation and evidence.

- [ ] Test multi-selection of models/agents, matrix limits and cancellation of launch; add menu action 8 without changing existing menu numbers.
- [ ] Add hidden session-key entry and re-entry while preserving environment references; use shared credential resolution and connection helper.
- [ ] Exercise browser 2×2 matrix through two HTTP endpoints/keys and real subprocesses, inspect saved exact pair bindings, four results, reports and comparison.
- [ ] Review backend/frontend security and specification compliance, fix findings, run appropriate complete suites/static/build/package checks.
- [ ] Stop test services, restore empty live preview, update evidence and docs, commit/push main, verify only main remains and tree is clean.

## Review focus

1. Each pair reaches its selected URL/model/key; no key or expected answer enters records/reports.
2. No zero-model/zero-agent/duplicate/over-16 matrix is launched; selection changes invalidate old validation.
3. Native products cannot masquerade as controlled bindings.
4. Repeated/unknown keys and backend restart produce honest, recoverable authentication state.
5. Work is sequential and budget-bound, so large matrices do not load model weights or claim equal opportunities after budget starvation.

## Added user scope: community proposals

The user additionally requests public suggestions, open-source agent sharing and recommended model pairings. Add a Community route, strict metadata-only local drafts and a repository-backed published catalog. Users review a GitHub issue draft before manually submitting; accepted entries enter the packaged catalog through a maintainer-reviewed pull request. A local draft is not labeled publicly published. Source URLs/licenses, exact suggested model names and optional evidence links are shared; credentials, private runtime settings and automatic agent execution are excluded. Catalog begins empty. Router and new components/tests belong to the community implementer; root owns API/nav integration and full browser coverage. This adds a thirteenth route without a public unauthenticated execution server.
