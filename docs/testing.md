# Test Bench Agents

Start with one task and one model. Add an agent only after the model connection works. A fresh workspace contains no saved systems or results; the public benchmark definitions are available immediately.

## Terminal: the quickest path

From the repository directory:

```shell
uv sync --locked --python 3.12
uv run bench-agents terminal
```

1. Choose **1 — Connect a model**. Give it a display name, choose OpenAI-compatible or Ollama, select local or hosted, and enter the endpoint URL and exact provider model ID. Authentication choices are no key, environment-variable reference, or hidden session-key entry. A session key stays only in this terminal process; an environment key must already be available in its shell. Do not paste a key into a name or URL.
2. Check the discovery result. **READY** means that discovery and the selected ID passed the available checks; generation still needs a run. **BLOCKED** includes the reason to fix, such as an unreachable server, missing ID or unavailable credential.
3. Choose **3 — Test models**, select one or more models by number, then **single reasoning task**. Keep the recommended limits: one trial, 30 seconds per task, 300 seconds total. Review compatibility and confirm the run. This sends a real request to your configured provider and may incur that provider's charges.
4. Read the result table. `1/1 verified` means that this task passed its independent check. `completed` means execution finished; it does not mean every output passed. Failed rows include the recorded reason. Unknown token counts and costs stay unavailable.
5. Choose **6 — Inspect/export results** and export a ZIP report. After a second run, use **7 — Compare saved runs**. Comparisons explain incompatible conditions rather than hiding them.

Connections and results persist after exiting. The browser and terminal share `.bench-agents` by default when started from the same repository directory. Use the same `BENCH_AGENTS_DATA_DIR` in both processes if you choose another location.

## Connect an agent to the model

Agents execute code with your OS privileges. For a trusted harness, explicitly enable host execution in the shell **before launching the terminal or API**. In PowerShell:

```powershell
$env:BENCH_AGENTS_ALLOW_HOST_PROCESS = "1"
uv run bench-agents terminal
```

On Bash, use `export BENCH_AGENTS_ALLOW_HOST_PROCESS=1`. Each experiment also asks for explicit authorization. A fresh task directory and restricted environment do not provide a filesystem or network sandbox.

Choose **2 — Connect an agent**, then **Custom subprocess harness**. Enter the executable and optional full script path. The harness receives plain prompt text on stdin and returns final plain text on stdout. Diagnostic logs belong on stderr. Arguments are separate strings, never a shell command.

For the included [one-request HTTP harness](../examples/adapters/minimal_chat_agent.py), use:

| Prompt | Value |
| --- | --- |
| Executable | Full path printed by `uv run python -c "import sys; print(sys.executable)"` |
| Script path | Full local path to `examples/adapters/minimal_chat_agent.py` |
| Additional arguments | `[]` |
| Model flag | `--model` |
| Endpoint environment variable | `HARNESS_BASE_URL` |
| API key environment variable | `HARNESS_API_KEY` |
| Additional environment allowlist | Blank unless your own harness explicitly needs it |

Choose **4 — Test model + agent**, select the saved endpoint and harness, and run the single-task check. Bench Agents passes the selected model ID and URL through these bindings and passes the credential through the configured target variable when needed. The example is an integration harness, not an autonomous coding agent.

For an installed Codex or OpenCode product, use its adapter and **5 — Test native agent**. Configure its authorized provider and isolated profile explicitly. Native products use their own settings; they cannot be presented as controlled endpoint comparisons. Credentialed native execution remains unverified in this environment.

## Website: the same workflow

Install Node.js 24, then build and launch:

```shell
npm ci --prefix apps/web
npm run build --prefix apps/web
uv run bench-agents ui
```

Open [Bench Agents](http://127.0.0.1:3000). The overview explains the setup order and shows the actual inventory.

1. **Register model** → choose **Local server** or **Hosted API** → enter endpoint and model ID → choose authentication → save → **Probe compatibility**. A hosted OpenAI-compatible service can use a hidden session API key; a local service can choose no key. Environment references remain available. Saving alone does not prove connectivity.
2. Choose **Build an experiment with this model**. Name it, select **Use one quick text task**, and keep one trial. The advanced section contains isolation, retries and technical configuration.
3. **Validate compatibility** → resolve any blocking reasons → **Launch experiment**. The live monitor reports execution and task checks separately. Refreshing retains the experiment.
4. Open **Execution replay** for failed output and verification evidence; use **Reports** to export. Use **Comparison studio** after a second run with matched conditions.
5. To pair a trusted harness, register it in **Agent explorer** with the same bindings described above. Build in agent mode, choose the shared model and agent, authorize host execution, validate and launch. Both the backend setting and experiment authorization are required.

The optional offline demonstration is under **Documentation**. It creates clearly labeled records only when clicked. To keep the live workspace free of fixtures, use the isolated offline command below instead.

## Multiple models and agents

Register the model endpoints separately: a local server, hosted API, or a mixture. Each keeps its own exact model ID, URL and optional credential. Register each trusted subprocess harness with its explicit model flag and endpoint/key environment mappings. Enable host execution only for the trusted harnesses as described above.

On the website:

1. Open **Experiment builder** and choose **Multiple agents × multiple models**.
2. Select the models and controlled agents independently. Two models × two agents creates four explicit pairs; each pair is displayed before launch. Native CLI products remain in native mode.
3. Choose **Use one quick text task** and one trial for setup verification. The preview should show **4 task checks** for a 2×2 selection.
4. Authorize host processes, validate compatibility, review reasons/warnings and launch. Every selected pair gets the same task selection and limits, using its own model connection.
5. Check all four run rows, inspect their manifests, then compare their run IDs and export the report. A provider failure remains a failed result rather than silently changing the model.

In the terminal, choose **8 — Test multiple models + agents**. Enter comma-separated model numbers and agent numbers, or `all`. Review the combination list and check count, select tasks and limits, authorize execution, then confirm the launch. Actions 3 and 4 also accept multiple models or multiple agents respectively. Maximum: 16 systems per experiment; larger selections are blocked before discovery or execution.

Pairs run sequentially to avoid exhausting RAM or overloading inference servers. The total budget applies to all pairs; increase it deliberately for a larger matrix. Session keys belong to the process where they were entered. After a backend restart, use **Re-enter session API key → Update session key** in the model inspector and probe again. A different terminal process prompts for missing session keys before running.

## Share a community suggestion

For actual source publishing and one-click import, use **Agent Hub**. Community is the separate reviewed suggestion catalog.

Open **Community**, choose agent/pairing/benchmark, and enter a title, description, public source, license and suggested exact model names. Agent entries require a source and license. Save the local draft, then choose **Review GitHub submission**. Review the shown metadata before **Open GitHub to submit yourself**; GitHub sign-in and manual submission are required. Download JSON if you want to prepare a catalog pull request instead.

Saving a draft does not publish it. Accepted catalog recommendations arrive through a repository update and remain labeled unverified. Source links do not execute or install code. See [Community contributions](community.md) for the review and publication workflow.

## Automated checks

The full host-safe deterministic collection runs without a model, key, Node.js or Docker:

```shell
uv run python scripts/full_offline.py
```

Expected: reference **9/9**, deliberately flawed system **0/9**. The tenth task needs Docker and remains blocked here. The script writes only to `.bench-agents/full-offline`, a separate database from the live workspace.

Backend, terminal, HTTP/subprocess integration and security checks:

```shell
uv sync --locked --python 3.12 --extra inspect
uv run pytest --cov=benchlab --cov-report=term-missing
uv run ruff check src tests examples scripts
uv run mypy src/benchlab
uv build
```

`tests/test_terminal_flow.py` uses a real loopback HTTP server and a real subprocess harness to exercise interactive registration, controlled pairing, one task, verification, persistence and ZIP export. No real model intelligence is simulated as a passing external smoke test.

Frontend checks:

```shell
npm test --prefix apps/web
npm run typecheck --prefix apps/web
npm run format:check --prefix apps/web
npm run build --prefix apps/web
```

Stop your usual dashboard/API before rebuilding and running browser tests. The runner refuses occupied ports rather than stopping another service. After the build, install the browser dependencies and run:

```shell
npm ci
npx playwright install chrome
uv run python scripts/test_browser.py
```

The runner creates new Lab and Hub directories under `.bench-agents/browser-checks/<timestamp>`, starts them on 8000/8101 and the built website on 3000, then stops its owned services on success or failure. Its environment excludes provider keys. Do not point browser tests at data you intend to keep.

The 21 browser tests cover empty onboarding, forms, real HTTP/subprocess execution, a 2×2 matrix across local and API-key fixture connections, Community review/exports, account registration, source publication, pinned import, benchmarking the imported agent and sharing the versioned result. They also cover cancellation, persistence, comparison, replay, ablation, downloads, keyboard access, accessibility scans and fourteen routes at four widths. Fixture HTTP services start and stop automatically. Start `uv run bench-agents ui` afterward to return to your normal workspace.

## Agent Hub: complete developer walkthrough

`bench-agents ui` starts a separate empty local Hub on 8100 unless `BENCH_AGENTS_HUB_URL` selects another registry. Start the registry independently with `uv run bench-agents hub`.

1. Open **Agent Hub → Create account**. Browsing and import need no account; publication, comments and shared results require one.
2. **Publish an agent**: enter details, a unique slug, semantic version and license. Describe inputs, outputs and model requirements in the README. Paste Python/Node.js source or upload text files and set the entrypoint. The harness reads a prompt from stdin and returns final text on stdout.
3. Add recommended exact model IDs. Under **Model bindings, arguments and dependencies**, supply the model flag and environment variable names your harness expects; credential values belong in private model registrations. Declare dependencies for users to review separately.
4. Inspect the published source and digest. **Import agent** registers it without execution or dependency installation. Edited imported source/configuration cannot run under that release identity; publish a new version or register a separate custom harness for changes.
5. Connect an authorized endpoint in **Model explorer**. Review dependencies and trust the code before enabling the backend host-process setting. Choose **Benchmark imported agent**, select a model and one quick task, authorize the experiment, validate and launch.
6. Inspect replay/evidence after completion. **Share this benchmark in Agent Hub** previews the actual local model, benchmark and pass count. Sign in and share. The report stays tied to its original registry and version and is labeled self-reported. This action sends no keys or raw private traces.
7. Use release section links for usage, source, benchmark summaries and discussion. Owners can **Publish new version**; existing releases cannot be overwritten.

For a shared registry, follow [Self-hosting Agent Hub](hub-server.md). Public moderation, quotas and account recovery remain deployment responsibilities. Arbitrary frameworks may need a compatible wrapper and separate dependency setup.

## Remaining external checks

**Real-model smoke: BLOCKED — endpoint unavailable.** To complete it later, provide an existing authorized endpoint:

- OpenAI-compatible base URL: `http[s]://HOST:PORT/v1`, without userinfo, query or fragment. It must support `GET /models` with the exact ID in `data[].id` and `POST /chat/completions`.
- Model ID: the exact provider-advertised string; a placeholder or marketing name is insufficient.
- Credential variable: `BENCH_AGENTS_PROVIDER_KEY` in the backend shell, referenced by name in the model configuration. Omit `api_key_env` for a credential-free local endpoint.
- Ollama alternative: `http://127.0.0.1:11434`, with an already installed model ID from `/api/tags`; the adapter generates through `/api/chat`.

No 7B/14B weights are loaded and no paid provider is substituted. Docker runtime tests and container builds remain blocked by the host's Docker Desktop startup failure. Four opt-in Docker tests stay skipped until a working Linux daemon is available. No reset or data deletion is required by this guide. See [the audit](audits.md) for exact verification boundaries.
