# Troubleshooting

## Docker Desktop does not start

`bench-agents doctor` reports runtime availability without starting Docker or pulling images. The implementation host's Docker Desktop fails while initializing its Inference-manager socket with `ERROR_CANT_ACCESS_FILE`; [Docker's issue tracker](https://github.com/docker/desktop-feedback/issues/625) has a matching report. This host condition is separate from application execution. The default offline demo remains usable. Repair/start a supported Docker Linux daemon before claiming sandbox tests or running the optional coding task. A factory reset can destroy local Docker data; Bench Agents has not performed one.

Once the daemon works, explicitly review and pull `python:3.12.10-slim`, then run the opt-in sandbox tests documented in `tests/test_sandbox.py`. No automatic image pull or host code fallback occurs. The Compose web/API stack intentionally cannot control the host Docker daemon.

## Endpoint probe fails

Use the exact installed model ID. OpenAI-compatible base URLs normally include `/v1`; native Ollama uses the server root. Inspect `models probe ID` output. Configure the referenced credential environment variable in the backend process, restart it, then probe again. Never paste a key into a report or frontend field. Discovery success only proves advertised model visibility, not generation/tool/structured-output support.

## Native agent authorization/authentication

Both server and per-experiment host-process opt-ins are required. A subprocess executable runs without a shell and does not inherit your full environment or home profile. Supply necessary credential variable names explicitly and prepare the isolated product configuration. Codex/OpenCode native modes own their provider setup; unsupported controlled-model binding fails preflight rather than silently selecting another model. Do not weaken sandbox or permission policy to make a comparison appear controlled.

## Web cannot reach the API

Start the backend at `127.0.0.1:8000`, then web at `127.0.0.1:3000`. Configure `BENCH_AGENTS_API_URL` for another backend and rebuild/restart web. Host and Origin protections intentionally reject unknown remote origins. Give API/CLI/worker the same `BENCH_AGENTS_DATA_DIR`. Do not run `next build` concurrently with `next dev` against the same `.next` directory; stop/restart the dev server after a build.

## Interrupted or stuck experiments

Restart one backend worker for the workspace. Recovery marks abandoned in-flight work interrupted and retains its evidence; live OS locks are respected. Cancellation is persisted and observed across API/CLI engines. Logs and event records describe observed failures; inferred causes must remain qualified. An experiment's completed state does not mean every task passed.

## Optional framework dependencies

`uv sync --extra inspect` enables Inspect; `--extra analysis` adds DuckDB/Parquet libraries. lm-eval is intentionally a separately managed external runtime with task/model download requirements. Missing optional packages are reported, not installed automatically. Heavy benchmark suites need their own resources/licenses and are not made available by displaying their names.
