# Test Bench Agents

Start with one task and one model. Add an agent only after the model connection works. A fresh workspace contains no saved systems or results; the public benchmark definitions are available immediately.

## Terminal: the quickest path

From the repository directory:

```shell
uv sync --locked --python 3.12
uv run bench-agents terminal
```

1. Choose **1 — Connect a model**. Give it a display name, choose OpenAI-compatible or Ollama, and enter the endpoint URL and exact provider model ID. For an authenticated service, enter the **environment variable name**, such as `BENCH_AGENTS_PROVIDER_KEY`; the key must already be available in the shell that launched Bench Agents. Leave this blank for an unauthenticated local service. Do not paste a key into a name or URL.
2. Check the discovery result. **READY** means that discovery and the selected ID passed the available checks; generation still needs a run. **BLOCKED** includes the reason to fix, such as an unreachable server, missing ID or unavailable credential.
3. Choose **3 — Test a model**, select the model, then **single reasoning task**. Keep the recommended limits: one trial, 30 seconds per task, 300 seconds total. Review compatibility and confirm the run. This sends a real request to your configured provider and may incur that provider's charges.
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

1. **Register model** → enter endpoint and model ID → save → **Probe compatibility**. Saving alone does not prove connectivity.
2. Choose **Build an experiment with this model**. Name it, select **Use one quick text task**, and keep one trial. The advanced section contains isolation, retries and technical configuration.
3. **Validate compatibility** → resolve any blocking reasons → **Launch experiment**. The live monitor reports execution and task checks separately. Refreshing retains the experiment.
4. Open **Execution replay** for failed output and verification evidence; use **Reports** to export. Use **Comparison studio** after a second run with matched conditions.
5. To pair a trusted harness, register it in **Agent explorer** with the same bindings described above. Build in agent mode, choose the shared model and agent, authorize host execution, validate and launch. Both the backend setting and experiment authorization are required.

The optional offline demonstration is under **Documentation**. It creates clearly labeled records only when clicked. To keep the live workspace free of fixtures, use the isolated offline command below instead.

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

Stop any running web server before rebuilding. For browser tests, stop the usual API first. In a new PowerShell terminal, choose a **new test directory for each complete run** because the first test checks empty startup:

```powershell
$env:BENCH_AGENTS_DATA_DIR = ".bench-agents/browser-check-$(Get-Date -Format yyyyMMddHHmmss)"
$env:BENCH_AGENTS_ALLOW_HOST_PROCESS = "1"
uv run uvicorn benchlab.api:app_factory --factory --host 127.0.0.1 --port 8000
```

Start the built web server in another terminal with `npm run start --prefix apps/web`. In a third terminal:

```shell
npm ci
npx playwright install chrome
npm run test:e2e
```

The browser suite checks empty onboarding, forms, a real HTTP-backed controlled agent run, explicit demo execution, verification failures, cancellation, refresh, comparison, replay, ablation, downloads, import, keyboard access, accessibility scans and all twelve routes at four widths. Its Python HTTP fixture is started and stopped by the suite. Saved test configurations are intentionally confined to the test workspace.

Stop the test API and start `bench-agents ui` from your normal shell, without the temporary data-directory setting, to return to the clean live workspace. Do not point browser tests at data you intend to keep.

## Remaining external checks

**Real-model smoke: BLOCKED — endpoint unavailable.** To complete it later, provide an existing authorized endpoint:

- OpenAI-compatible base URL: `http[s]://HOST:PORT/v1`, without userinfo, query or fragment. It must support `GET /models` with the exact ID in `data[].id` and `POST /chat/completions`.
- Model ID: the exact provider-advertised string; a placeholder or marketing name is insufficient.
- Credential variable: `BENCH_AGENTS_PROVIDER_KEY` in the backend shell, referenced by name in the model configuration. Omit `api_key_env` for a credential-free local endpoint.
- Ollama alternative: `http://127.0.0.1:11434`, with an already installed model ID from `/api/tags`; the adapter generates through `/api/chat`.

No 7B/14B weights are loaded and no paid provider is substituted. Docker runtime tests and container builds remain blocked by the host's Docker Desktop startup failure. Four opt-in Docker tests stay skipped until a working Linux daemon is available. No reset or data deletion is required by this guide. See [the audit](audits.md) for exact verification boundaries.
