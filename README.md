# 🔬 BenchLab

<div align="center">

**A local-first, evidence-driven experimentation laboratory for evaluating AI models, autonomous agents, and execution harnesses with independent verification.**

[![Release Status](https://img.shields.io/badge/status-development--0.1.0-amber.svg)](docs/implementation-status.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![Node: 24 LTS](https://img.shields.io/badge/Node-24_LTS-339933.svg?logo=node.js&logoColor=white)](apps/web/package.json)
[![Next.js 16](https://img.shields.io/badge/Next.js-16.4-black.svg?logo=next.js&logoColor=white)](apps/web/package.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](pyproject.toml)
[![Architecture: Local--First](https://img.shields.io/badge/Storage-SQLite_%2B_Artifacts-003B57.svg?logo=sqlite&logoColor=white)](docs/architecture.md)
[![Zero Cloud Telemetry](https://img.shields.io/badge/Telemetry-Zero_External-gray.svg)](SECURITY.md)

[Quickstart](#quickstart) · [Why BenchLab?](#why-benchlab) · [Architecture & Abstractions](#system-architecture) · [Interactive Workspace](#interactive-workspace-tour) · [Core Capabilities](#core-capabilities) · [Local Models](#running-local-models) · [Agent Harnesses](#evaluating-agent-harnesses) · [CLI Reference](#cli-reference) · [Python SDK](#python-sdk) · [Verification & Security](#verification-engine--sandboxing) · [Documentation](#documentation-index)

</div>

---

BenchLab is an open-source experimental laboratory designed to evaluate models, autonomous agents, and execution harnesses under controlled, reproducible conditions. Instead of collapsing diverse capabilities into an opaque, self-reported leaderboard score, BenchLab executes tasks across isolated environments, captures observable trace events, evaluates outcomes with decoupled verifiers, and exports audit-grade evidence packages.

**Release gate:** this is a tested development build, version 0.1.0. The real-model smoke test is **BLOCKED — endpoint unavailable**. Docker sandbox runtime tests are blocked by this host's Docker Desktop startup error. Local HTTP fixtures verify the provider/harness pipeline; they do not verify model intelligence. See [audit evidence and remaining gates](docs/audits.md).

The browser dashboard, terminal CLI, and Python SDK operate against a unified local SQLite workspace. **No hosted accounts, paid cloud subscriptions, or external database services are required for local operation and offline demonstrations.**

![BenchLab Research Workspace](docs/evidence/overview-1440.png)
<p align="center"><em>BenchLab research workspace: 12 API-backed screens featuring live polling, trace replay, and statistical comparisons. Demonstration results are labeled.</em></p>

---

## Why BenchLab?

Traditional evaluation approaches often suffer from data contamination, brittle LLM-as-a-judge biases, unverified execution claims, and a complete lack of failure visibility. BenchLab is engineered from the ground up as a scientific instrument:

| Feature / Dimension | Traditional Leaderboards | Raw Eval Scripts | BenchLab Laboratory |
| :--- | :--- | :--- | :--- |
| **Verification Authority** | Model self-assessment / LLM judge | Ad-hoc script assertions | **Decoupled independent verifiers** (exact, JSON/schema, file state, Docker Python) |
| **Execution Evidence** | Single summary percentage | Terminal log printouts | **Append-only trace stream**, event inspection, and workspace filesystem diffs |
| **Failure Diagnostics** | Opaque pass / fail count | Unstructured stack traces | **Explicit failure classification** (timeout, token budget, tool failure, verification rejection) |
| **Statistical Rigor** | Point estimates | Simple arithmetic means | **Wilson 95% confidence intervals**, paired exact McNemar tests, condition fingerprinting |
| **Interface Unification** | Web-only or CLI-only | Python-only | **Shared SQLite engine**: Next.js 16 Web UI, Typer CLI, and Python SDK share identical state |
| **Data Privacy & Secrets** | Hosted cloud databases | Plaintext API keys in configs | **100% local-first**, loopback bound, API keys mapped to environment variable names |
| **Zero-Cost Out of the Box** | Requires paid provider keys | Requires heavyweight downloads | **Deterministic offline demo** exercising the full queue, execution, and verification pipeline |

---

## System Architecture

BenchLab is organized around a durable, local-first engine with decoupled adapters and strict trust boundaries:

```mermaid
flowchart TD
    subgraph UI ["User Interfaces"]
        WEB["Next.js 16 Web App<br/>(12 Interactive Screens)"]
        CLI["Typer CLI<br/>(benchlab command)"]
        SDK["Python SDK<br/>(Laboratory class)"]
    end

    subgraph Service ["Service & Orchestration Layer"]
        API["FastAPI REST Server<br/>(Loopback /api)"]
        ENGINE["Durable Execution Engine<br/>(Queue, Budgets, Timeouts, Retries)"]
    end

    subgraph Storage ["Durable Local Storage (.benchlab/)"]
        SQLITE[("SQLite Database<br/>benchlab.sqlite3")]
        ARTIFACTS["Local Artifact Store<br/>(Diffs, Exports, Logs)"]
    end

    subgraph Execution ["Execution Subsystems"]
        SUT_MODEL["Model Adapters<br/>• Ollama HTTP<br/>• OpenAI-Compatible"]
        SUT_AGENT["Agent Adapters<br/>• Subprocess CLI<br/>• Codex CLI Noninteractive<br/>• OpenCode CLI"]
        SANDBOX["Isolated Environments<br/>• Workspaces Directory<br/>• Bounded Docker Sandbox"]
    end

    subgraph Verification ["Independent Verification Pipeline"]
        OBS["Trace Observation Stream<br/>(OpenTelemetry conventions)"]
        VERIFIER["Decoupled Verifiers<br/>• Exact String<br/>• JSON Schema / Equality<br/>• Filesystem State<br/>• Docker Python Execution"]
    end

    subgraph Analysis ["Statistical Engine & Reporting"]
        STATS["Wilson 95% Intervals<br/>Paired McNemar Tests<br/>Condition Fingerprinting"]
        EXPORTS["Audit Evidence Exports<br/>• JSON • CSV • HTML • ZIP"]
    end

    WEB --> API
    CLI --> ENGINE
    SDK --> ENGINE
    API --> ENGINE

    ENGINE <--> SQLITE
    ENGINE <--> ARTIFACTS

    ENGINE --> SUT_MODEL
    ENGINE --> SUT_AGENT
    SUT_MODEL & SUT_AGENT --> SANDBOX

    SANDBOX --> OBS
    OBS --> VERIFIER
    VERIFIER --> ENGINE

    ENGINE --> STATS
    STATS --> EXPORTS
```

### The Six Core Abstractions

BenchLab avoids coupling to specific model endpoints or agent products by building on six versioned architectural contracts:

1. **System Under Test (`ModelConfig` / `AgentConfig`)**: Declarative contracts for model endpoints and agent executables with versioned adapters (`openai-compatible`, `ollama`, `subprocess`, `codex-cli`, `opencode-cli`).
2. **Objective & Task (`TaskDefinition`)**: Self-contained, immutable evaluation units with versioned specifications, category tags, expected constraints, and capability prerequisites.
3. **Environment (`EnvironmentProvider`)**: Ephemeral workspace filesystem isolation with optional containerized execution boundaries (`network: none`, non-root, read-only root).
4. **Observations (`TraceEvent`)**: Normalized, append-only event stream recording durations, token usage, tool invocations, and workspace filesystem modifications.
5. **Verifier (`VerificationResult`)**: Decoupled verification engines that evaluate outputs independently. The expected answers are never supplied to the evaluated systems.
6. **Experiment Record (`RunManifest` & Persisted Run)**: Immutable, reproducible manifests combining the experiment configuration, trial runs, condition fingerprints, and raw artifacts.

---

## Interactive Workspace Tour

BenchLab provides 12 specialized research screens designed with a graphite-and-black aesthetic (Geist typography, shadcn/ui primitives, Tailwind CSS v4, and Recharts):

````carousel
![BenchLab Research Workspace](docs/evidence/overview-1440.png)
<!-- slide -->
![Head-to-Head Comparison](docs/evidence/comparison-desktop.png)
<!-- slide -->
![Execution Replay & Trace Inspector](docs/evidence/replay-desktop.png)
<!-- slide -->
![Live Run Monitor](docs/evidence/live-results-desktop.png)
<!-- slide -->
![Benchmark Library](docs/evidence/benchmarks-desktop.png)
````

### Production Screen Directory

* **Overview & Activity Feed (`/`)**: Real-time experiment status, system health diagnostics, recent benchmark activity, and verified capability inventory.
* **Head-to-Head Comparison (`/compare`)**: Statistical distributions, Wilson score intervals, category breakdown comparisons, and paired condition checking.
* **Execution Replay & Trace Inspector (`/replay`)**: Granular timeline scrubbing, event inspection, prompt/response inspection, and side-by-side workspace filesystem diffs.
* **Run Monitor (`/monitor`)**: Live queue tracking, streaming task events, real-time pass/fail states, and cooperative cancellation controls.
* **Benchmark Library & Builder (`/benchmarks`)**: Catalog of runnable packs, task inspection, requirement checks, and custom benchmark composition.
* **Model & Agent Registries (`/models`, `/agents`)**: Endpoint management, discovery probes, capability declarations, and authorization controls.
* **Reports & Evidence Exports (`/reports`)**: Standalone audit packages downloadable in JSON, CSV, CSP-compliant HTML, or compressed ZIP format.

---

## Quickstart

### Prerequisites

* **Python 3.12** with [uv](https://docs.astral.sh/uv/) package manager
* **Node.js 24 LTS** and `npm`
* **Docker** *(optional for basic starter tasks; required for containerized code execution)*

### Installation

Clone the repository and install locked dependencies:

```powershell
# Windows (PowerShell)
git clone https://github.com/nagasaipradhyumnapoola/benchmark_agents.git
cd benchmark_agents
git switch feat/benchlab-v1
uv sync --locked --python 3.12
npm ci --prefix apps/web
npm run build --prefix apps/web
```

```bash
# macOS / Linux (Bash)
git clone https://github.com/nagasaipradhyumnapoola/benchmark_agents.git
cd benchmark_agents
git switch feat/benchlab-v1
uv sync --locked --python 3.12
npm ci --prefix apps/web
npm run build --prefix apps/web
```

### 1. Run the Zero-Credential Offline Demonstration

Verify the entire pipeline—queue, worker, task execution, independent verifiers, and reporting—without configuring external services or API keys:

```powershell
uv run benchlab demo
```

> [!NOTE]
> The offline demo runs deterministic reference systems alongside intentionally flawed systems against real verifiers. **Demo pass rates measure pipeline correctness and verification discrimination, not artificial intelligence.**

### 2. Launch the Research Workspace

Start the local API and Next.js web dashboard in a single command:

```powershell
uv run benchlab ui
```

At the default API port, this uses the production build when present. Without a build, or with a custom API port, it launches the development server; the first page compiles on demand and can be slow on memory-constrained machines. Dev/build scripts disable Next.js telemetry by default.

* **Web Dashboard:** [http://127.0.0.1:3000](http://127.0.0.1:3000)
* **REST API OpenAPI Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

To run backend and frontend independently across separate terminals:

```powershell
# Terminal 1: Backend API (FastAPI)
uv run uvicorn benchlab.api:app_factory --factory --host 127.0.0.1 --port 8000

# Terminal 2: Frontend Dashboard (Next.js)
npm run dev --prefix apps/web
```

---

## Running Local Models

BenchLab connects to locally hosted models (via Ollama, vLLM, llama.cpp, or LocalAI) with zero cloud telemetry.

### Ollama Endpoint Setup

1. Start your local Ollama server and pull your model of choice:
   ```powershell
   ollama pull llama3.2:3b
   ```

2. Register the endpoint configuration using [`examples/ollama-model.json`](examples/ollama-model.json):
   ```json
   {
     "id": "local-ollama",
     "name": "Local Ollama Llama 3.2",
     "adapter": "ollama",
     "model": "llama3.2:3b",
     "base_url": "http://127.0.0.1:11434",
     "capabilities": ["text"],
     "demo": false
   }
   ```

3. Register, probe connectivity, and run a benchmark:
   ```powershell
   uv run benchlab models add examples/ollama-model.json
   uv run benchlab models probe local-ollama
   uv run benchlab run --model local-ollama --benchmark starter-v1 --trials 3 --name "Ollama Baseline"
   ```

### OpenAI-Compatible Endpoints (vLLM, llama.cpp, External APIs)

For endpoints exposing `/v1/chat/completions`, create a configuration referencing the **environment variable name** holding the API key:

```json
{
  "id": "configured-endpoint",
  "name": "Local vLLM Server",
  "adapter": "openai-compatible",
  "model": "meta-llama/Llama-3.2-3B-Instruct",
  "base_url": "http://127.0.0.1:1234/v1",
  "api_key_env": "BENCHLAB_PROVIDER_KEY",
  "capabilities": ["text"],
  "demo": false
}
```

```powershell
$env:BENCHLAB_PROVIDER_KEY = "your-key-if-required"
uv run benchlab models add examples/openai-compatible-model.json
uv run benchlab models probe configured-endpoint
uv run benchlab run --model configured-endpoint --benchmark starter-v1 --trials 3
```

> [!SECURITY]
> Configure secrets through environment variables. BenchLab stores their names and applies best-effort redaction to records and reports. Do not paste credentials into descriptions, arguments, output or configuration values.

---

## Evaluating Agent Harnesses

BenchLab evaluates autonomous agent harnesses and coding CLI products (`subprocess`, `codex-cli`, `opencode-cli`).

### Dual-Consent Security Policy

Evaluating native CLI executables involves privileged host processes. BenchLab enforces a strict two-tier authorization gate:
1. **Host Environment Consent:** `BENCHLAB_ALLOW_HOST_PROCESS=1` must be explicitly exported in the server/worker environment.
2. **Experiment Consent:** The experiment configuration must explicitly include `"allow_host_process": true` (or `--allow-host-process` via CLI).

### CLI Harness Execution

```powershell
$env:BENCHLAB_ALLOW_HOST_PROCESS = "1"
uv run benchlab agents add examples/codex-agent.json
uv run benchlab agents probe configured-codex
uv run benchlab run --config examples/native-experiment.json
```

Native agent execution also requires an authorized provider configuration. The fresh task profile does not inherit existing CLI login files. This example was contract-tested; a credentialed Codex run was not performed. See [integration requirements](docs/integrations.md).

* **Process execution:** Generic subprocesses receive prompts on stdin; Codex/OpenCode receive one prompt argument and return JSONL. Known Windows npm launchers resolve to their native executable or Node entry point without a command shell.
* **Environment Sanitization:** Full host environment inheritance is blocked. `HOME`, `USERPROFILE`, and config directories are quarantined to a clean, isolated task workspace.
* **Filesystem Diffing:** Any file modifications in the workspace are captured as unified diffs and persisted as observable evidence.

---

## CLI Reference

The `benchlab` CLI shares the exact same database and execution engine as the web application:

| Command | Arguments & Flags | Description |
| :--- | :--- | :--- |
| `benchlab demo` | None | Runs the deterministic, zero-credential offline demonstration. |
| `benchlab doctor` | None | Inspects runtime health, storage permissions, and optional dependencies. |
| `benchlab ui` | `--port 8000`, `--api-only`, `--web-dir PATH` | Launches the local API and Next.js web application. |
| `benchlab run` | `--model ID`, `--agent ID`, `--benchmark ID`, `--trials N`, `--config PATH` | Executes a benchmark against a model or agent system. |
| `benchlab compare` | `RUN_ID_A RUN_ID_B [RUN_ID_C ...]` | Performs condition-aware statistical comparison across runs. |
| `benchlab report` | `EXPERIMENT_ID --format json\|csv\|html\|zip --out PATH` | Generates a portable, audit-grade evidence export. |
| `benchlab cancel` | `EXPERIMENT_ID` | Signals cooperative cancellation to running workers. |
| `benchlab worker` | None | Runs a headless background worker daemon processing the SQLite queue. |
| `benchlab models list` | None | Lists all registered model endpoints. |
| `benchlab models add` | `CONFIG_PATH` | Registers a model endpoint from a JSON or TOML file. |
| `benchlab models probe` | `MODEL_ID` | Checks connectivity and advertised model ID; capabilities/context are declared, not proven by discovery. |
| `benchlab agents list` | None | Lists all registered agent harness configurations. |
| `benchlab agents add` | `CONFIG_PATH` | Registers an agent executable configuration. |
| `benchlab agents probe` | `AGENT_ID` | Checks executable availability and supported launcher resolution. |
| `benchlab benchmarks list` | None | Lists available benchmark packs and requirement gates. |
| `benchlab experiments list` | None | Lists persisted experiments and high-level status. |
| `benchlab experiments show` | `EXPERIMENT_ID` | Displays complete manifest, run records, and trial details. |

---

## Python SDK

BenchLab provides a Python SDK (`Laboratory`) enabling programmatic benchmark execution, comparison, and analysis:

```python
import asyncio
from benchlab.sdk import Laboratory
from benchlab.schemas import ExperimentConfig, SystemSpec

async def main():
    # Connects to the local SQLite store (.benchlab/ by default)
    lab = Laboratory()

    # Define an experiment
    config = ExperimentConfig(
        name="Local Llama Evaluation",
        benchmark_id="starter-v1",
        systems=[
            SystemSpec(model_id="local-ollama"),
        ],
        trials=3,
        task_timeout_seconds=30,
    )

    # Submit and execute asynchronously
    experiment = await lab.run(config)
    print(f"Experiment completed: {experiment['id']} - Status: {experiment['status']}")

    # Retrieve and compare runs
    runs = lab.store.list_runs(experiment["id"])
    run_ids = [run["id"] for run in runs]
    comparison = lab.compare(*run_ids)
    print("Wilson 95% Pass Interval:", comparison["summary"])

    # Export a self-contained ZIP evidence package
    zip_bytes, media_type, filename = lab.report(experiment["id"], format="zip")
    with open("evidence_package.zip", "wb") as f:
        f.write(zip_bytes)
    print(f"Exported evidence package: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Verification Engine & Sandboxing

BenchLab separates generation and verification. Requests contain task prompts rather than verifier expected answers. Public fixtures and trusted local plugin source remain inspectable; this is not a formal anti-cheat boundary.

```mermaid
flowchart LR
    TASK["Task Prompt"] --> SUT["System Under Test<br/>(Model or Agent)"]
    SUT --> RAW["Generated Output / State"]
    RAW --> VERIFIER["Independent Verifier Engine"]
    EXPECTED["Ground Truth / Criteria<br/>(Hidden from SUT)"] --> VERIFIER
    VERIFIER --> RESULT["VerificationResult<br/>(passed: bool, score, details)"]
```

### Supported Verifier Strategies

1. **Exact match (`exact`)**: Case-sensitive comparison after stripping surrounding whitespace.
2. **JSON equality / schema (`json`, `schema`)**: Parse JSON, validate a configured schema, and compare expected object values where supplied. Ledger/recovery fixtures use this path to verify structured responses.
3. **Filesystem state (`file-json`)**: Read a contained file from the actual workspace and independently compare parsed values.
4. **Containerized Python (`python`)**: Run generated Python in Docker, require completion evidence, and compare serialized function outputs in the trusted verifier. Runtime validation is blocked on Docker Desktop on this host.

### Docker Sandbox Isolation Policy

When evaluating generated code, BenchLab enforces hardened container boundaries:
* **Network Isolation:** `--network none` prevents external container networking; loopback within a container remains possible.
* **Filesystem Protection:** Read-only root filesystem (`--read-only`) with a volatile non-executable tmpfs.
* **Privilege De-escalation:** Runs as non-root user (`UID 65534 / nobody`), drops all Linux capabilities (`--cap-drop ALL`), and enforces `--security-opt no-new-privileges`.
* **Zero Host Mounts:** No host filesystem volumes or Docker sockets are ever mounted into the container.
* **Resource Caps:** Bounded memory (256MB default), CPU quota, execution timeout, and capped captured output.

---

## Starter Task Suite (`starter-v1`)

BenchLab includes 10 original, public, Apache-2.0 starter tasks covering diverse capabilities:

| Task ID | Category | Target Capability | Verification Type |
| :--- | :--- | :--- | :--- |
| `reasoning-inventory` | Reasoning | Inventory arithmetic | Exact string equality |
| `knowledge-protocol` | Knowledge | HTTP status semantics | Exact string equality |
| `multilingual-es` | Language | Spanish instructions | JSON equality |
| `structured-invoice` | Extraction | Invoice structure | JSON schema & equality |
| `tool-weather` | Tool selection | Tool selection plan | JSON equality; no live tool invocation |
| `multistep-ledger` | Multi-step | Ledger response | JSON equality; no live environment transitions |
| `recovery-retry` | Recovery | Retry plan | JSON equality; no live rate-limit recovery |
| `safety-boundary`| Safety | Untrusted instruction response | JSON equality and forbidden-content check |
| `workspace-normalize` | Filesystem | Workspace file reorganization and clean-up | Independent disk verification |
| `coding-dedupe` | Code execution | Stable Python deduplication | Docker function-result checks; no complexity proof |

---

## Scientific Rigor & Measurement Standards

* **Wilson 95% Confidence Intervals:** Every reported pass rate includes a binomial Wilson confidence interval to communicate sample uncertainty.
* **Paired McNemar Tests:** Paired system comparisons calculate exact two-sided p-values to determine whether differences are statistically distinguishable.
* **Condition Fingerprinting:** Runs are tagged with an immutable SHA-256 fingerprint of all parameters (temperature, sampling seed, timeouts, task definitions, and system prompts). The comparison engine warns or blocks when attempting to compare incompatible conditions.
* **Transparent Metrics:** Token counts are provider-reported; costs are calculated from explicit pricing models. Unobserved values remain `null` rather than masquerading as zero.

---

## Directory Structure

```text
benchmark_agents/
├── apps/
│   └── web/                   # Next.js 16 research dashboard (React 19, Tailwind v4, shadcn/ui)
│       ├── src/app/           # 12 production application screens & route handlers
│       ├── src/components/    # Radix primitives, data tables, charts, and diff viewers
│       └── tests/             # Vitest frontend component and navigation tests
├── src/
│   └── benchlab/              # Python backend core library
│       ├── adapters/          # Model & agent adapters (Ollama, OpenAI, Subprocess, Codex)
│       ├── benchmarks/        # Benchmark packs & catalog (starter-v1)
│       ├── api.py             # FastAPI REST endpoints & loopback middleware
│       ├── cli.py             # Typer terminal CLI commands
│       ├── engine.py          # Durable async job execution, worker queue, and recovery
│       ├── sandbox.py         # Hardened Docker container sandbox execution
│       ├── schemas.py         # Versioned Pydantic data contracts
│       ├── sdk.py             # High-level Python SDK (Laboratory)
│       ├── store.py           # SQLite persistence layer and artifact store
│       └── verification.py    # Independent evaluation engine
├── docs/                      # Architectural specifications & technical manuals
│   ├── architecture.md        # Technical architecture and design contracts
│   ├── configuration.md       # Configuration reference and environment variables
│   ├── contracts.md           # API, SDK, and SQLite schema contracts
│   ├── evidence/              # UI screenshots and test execution artifacts
│   ├── integrations.md        # Integration guides for models, agents, and external suites
│   ├── methodology.md         # Statistical evaluation and verification methodology
│   ├── plugins.md             # Custom adapter and benchmark plugin development
│   └── troubleshooting.md     # Diagnostic procedures and common resolutions
├── examples/                  # Sample configurations and SDK scripts
├── tests/                     # Backend, integration, security and browser tests
├── compose.yaml               # Container deployment definition (zero host-socket mount)
├── pyproject.toml             # Python build configuration and dependencies
└── README.md                  # Project overview and documentation
```

---

## Development & Test Suite

BenchLab enforces comprehensive automated testing across Python and TypeScript stacks:

```powershell
# Run backend pytest suite with coverage
uv run pytest --cov=benchlab --cov-report=term-missing

# Run Python linter and type-checker
uv run ruff check src tests examples
uv run mypy src/benchlab

# Run frontend Vitest suite
npm test --prefix apps/web

# Run frontend TypeScript check and production build
npm run typecheck --prefix apps/web
npm run build --prefix apps/web

# Install browser-test dependencies and Chrome, then run with API and web running
npm ci
npx playwright install chrome
npx playwright test
```

---

## Documentation Index

Explore the complete technical documentation in [`docs/`](docs/):

* [**Architecture & Design Contract**](docs/architecture.md): Deep-dive into the six abstractions, domain boundaries, and storage engine.
* [**Evaluation Methodology**](docs/methodology.md): Statistical treatments, Wilson intervals, failure accounting, and provenance.
* [**Configuration Guide**](docs/configuration.md): Storage directories, environment variables, and credential management.
* [**CLI, REST & SDK Interfaces**](docs/interfaces.md): Interface signatures, HTTP payloads, and programmatic examples.
* [**Trusted Plugin Development**](docs/plugins.md): Guide to creating custom model adapters, agent adapters, and task packs.
* [**Integrations Reference**](docs/integrations.md): Provider setups, Codex/OpenCode integration, and Inspect AI workflows.
* [**Troubleshooting & Diagnostics**](docs/troubleshooting.md): Resolving runtime issues, Docker configuration, and recovery procedures.
* [**Security Policy & Threat Model**](SECURITY.md): Loopback binding, host process opt-in, and sandboxing rules.
* [**Contributing Guidelines**](CONTRIBUTING.md): Branching strategy, testing requirements, and review criteria.

---

## License & Notices

Original BenchLab code and the `starter-v1` task suite are licensed under the **[Apache-2.0 License](LICENSE)**.

Third-party libraries, evaluated upstream frameworks, models, and datasets retain their respective original licenses. See **[NOTICE.md](NOTICE.md)** for detailed legal disclosures and acknowledgments.
