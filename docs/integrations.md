# Integrations and measured support

Bench Agents's built-in experiment engine runs `starter-v1`: ten original Apache-2.0 public tasks. The default selection is eight text tasks. The ninth coding task (`coding-dedupe`) requires Docker; `workspace-normalize` is an explicitly selected filesystem task requiring the `workspace` capability. JSON tool-selection/recovery tasks measure a plan or state response, not actual live tool use. Public fixtures are not held-out or contamination-resistant intelligence benchmarks.

## Model providers

Register `adapter: openai-compatible` with a credential-free `base_url` ending in `/v1`, a provider model ID and optional `api_key_env`. The adapter POSTs `/chat/completions`; it sends the prompt and supported sampling parameters, never verifier expected answers. Usage comes from the response. Cost is calculated only when both token counts and both configured token prices exist. Discovery probes `/models`; successful discovery does not prove generation or tool capabilities. Contract tests use HTTP MockTransport, not paid provider calls.

Register `adapter: ollama` with `base_url: http://127.0.0.1:11434` and an already pulled model. The adapter calls `/api/chat` with `stream: false` and observes prompt/evaluation token counts. Download models explicitly using `ollama pull <model>`; Bench Agents never starts downloads. See [Ollama API](https://docs.ollama.com/api).

## Native agents and subprocesses

`subprocess` executes a configured executable and argv directly with no shell, passes only the prompt on stdin, and uses stdout as the final response. `codex-cli` builds `codex exec --json --sandbox read-only --skip-git-repo-check [--model ID] PROMPT`; `opencode-cli` builds `opencode run --format json [--model provider/model] PROMPT`. Local `--help` for both installed products was checked on 2026-10-22. JSONL parsers retain final agent-message/text events. Native products remain separate experimental conditions; specifying a model does not establish control over the product's entire harness.

Both the server environment `BENCH_AGENTS_ALLOW_HOST_PROCESS=1` and experiment `allow_host_process: true` are mandatory. These are privileged host processes, not Docker sandboxes. Use a dedicated OS account/VM for untrusted agents. Child processes are killed on timeout/cancellation. The child environment contains basic process-path variables plus explicitly named `env_allowlist` values. HOME, USERPROFILE, CODEX_HOME and XDG_CONFIG_HOME point inside the fresh task workspace, so existing user profiles and auth files are not silently reused. Add necessary API-key *names* to the allowlist and prepare credentials explicitly. Never put secret values in args/configs. Prompt content is always one argument or stdin. Workspace changes emit actual file diffs; output snapshots reject symlinks and cap text sizes. Artifact snapshots are observations, not verifier evidence: the file-state verifier reads disk independently.

Codex/OpenCode executable discovery and CLI/parser contracts are tested. Credentialed end-to-end agent calls were not exercised; auth/provider availability remains user-specific. Official references: [Codex noninteractive](https://developers.openai.com/codex/noninteractive), [OpenCode CLI](https://opencode.ai/docs/cli/).

## Docker coding verification

Explicitly pre-pull `docker pull python:3.12.10-slim`. No automatic pull or host fallback occurs. Containers use no host mounts, network none, read-only root filesystem, non-root UID 65534, all capabilities dropped, no-new-privileges, capped memory/swap/CPU/PIDs/file descriptors, a small noexec tmpfs, output limit and named-container cleanup on cancellation. Generated submission and trusted tests arrive on stdin and execute only inside Docker. An unavailable runtime fails verification visibly.

Current machine limitation: Docker Desktop fails at Inference manager initialization (`docker-inference`, ERROR_CANT_ACCESS_FILE). Runtime integration remains unverified; no Docker data was reset. Contract tests cover the fail-closed behavior and argv policy.

## Established framework execution

These are explicit optional Python workflows, not pretend benchmark choices in the web launcher. They retain upstream scoring names and mark results `comparable_to_starter: false`. Inspect and lm-eval scores are not flattened into pass/fail or mixed into starter comparison statistics.

Install Inspect with `uv sync --extra inspect`. Its [Task/Sample/generate/scorer/eval_async API](https://inspect.aisi.org.uk/tasks.html) executes two original starter prompts using upstream `match` scoring and writes genuine Inspect JSON logs. Real framework execution with its mockllm provider is tested and clearly demo-marked, with deliberately wrong responses receiving upstream zero scores. Example PowerShell:

```powershell
$env:BENCH_AGENTS_ALLOW_HOST_PROCESS='1'
uv run python examples/adapters/frameworks.py inspect --model mockllm/model --output .bench-agents/inspect-demo --allow-host-process
# Replace mockllm/model with a configured Inspect provider/model for real evaluation.
```

The [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) runner builds the current `lm-eval run` CLI with explicit model backend, model args, task names, output path, sample logs and optional limit. JSON result parser preserves metric values and task versions, rejects empty results and constrains returned artifact paths. Setup in a separate Python 3.12 environment: `uv pip install lm-eval`; confirm `lm-eval run --help`, then:

```powershell
$env:BENCH_AGENTS_ALLOW_HOST_PROCESS='1'
uv run python examples/adapters/frameworks.py lm-eval --model hf --model-args pretrained=gpt2 --tasks hellaswag --limit 2 --output .bench-agents/lm-eval-smoke --allow-host-process
```

This path requires installed lm-eval backend dependencies, model weights, task datasets and enough RAM/VRAM for that model. Downloads/network are controlled by upstream libraries; sample limit 2 is a smoke test, not a valid published benchmark score. CLI argv/result contracts are tested; a full dataset/model run has not been exercised here. The lm-eval framework is MIT, Inspect MIT; dataset/model licenses remain independent. Review each selected dataset card and pin framework/model/dataset revisions for publication.

## Researched external suites, unavailable in launcher

| Framework/suite | Actual setup/resource boundary | Status |
| --- | --- | --- |
| [Harbor](https://docs.harborframework.com/getting-started/quick-start) | `uv tool install harbor`, `harbor run --help`; select a versioned dataset/agent/model and sandbox provider. Local container tasks need a working Docker daemon; provider agents need credentials. MIT framework, independently licensed task assets. | Official workflow researched; no integrated runner claimed. |
| [Terminal-Bench](https://github.com/harbor-framework/terminal-bench) | Harbor-compatible terminal tasks, environment images, per-task verifiers and resources; versioned task dataset plus Docker or supported remote sandbox. Framework MIT; check task licenses. | Blocked on unavailable Docker; not installed/executed. |
| [SWE-bench](https://www.swebench.com/SWE-bench/guides/evaluation/) | Official `swebench.harness.run_evaluation` consumes JSONL predictions, dataset name, run ID and worker count; repository/container images and substantial disk/memory required. MIT harness; repository/dataset licenses also apply. | No suite run or integrated adapter claimed. |
| [Lighteval](https://github.com/huggingface/lighteval) | Separate environment: `pip install lighteval`, inspect `lighteval eval --help` and choose an authorized provider/model and licensed task. The current official README explicitly excludes Windows support; local backends need model memory and optional dependencies. | Researched; unsupported in this Windows launcher; not installed or executed. No remote example was invoked. |
| [OSWorld-V2](https://github.com/xlang-ai/OSWorld-V2) | A separate computer-use VM environment, task assets, supported agent/provider and platform setup from its official README; substantial VM resources. Never run desktop benchmark actions against the user's working desktop. | Research reference only; no runner or score claimed. |
| [AgentDojo](https://github.com/ethz-spylab/agentdojo) | Separate environment: `pip install agentdojo`, `python -m agentdojo.scripts.benchmark --help`; select suites, user tasks, defense/attack and an authorized model. Official API is still evolving. MIT framework; inspect task/model assets separately. | Research reference only; no paid calls, integrated runner or score claimed. |

No upstream dataset or implementation was copied into starter tasks.

## Trusted extensions

Import a trusted local module before constructing Engine/API and call `register_model_adapter(name, execute, probe, version='1.0')`, `register_agent_adapter(...)`, or `register_benchmark(id, tasks, metadata, version='1.0')`. Execute uses the same async eight-argument contract as `execute_system`; probe accepts configuration and returns CompatibilityResult. Registration rejects duplicate names or unsupported contract versions. HTTP configurations choose an existing registered name; HTTP never imports a module or executes an import string. See `examples/adapters/local_plugin.py`. Plugin execution is trusted application code and must enforce its own resource/security boundaries; untrusted plugins need a separate process/container architecture.

Coding verification compares serialized function results in the trusted host rather than accepting Python exit status as success. A per-run completion marker also rejects early `sys.exit(0)`; missing/malformed output, execution errors and suppression of output fail. The public harness is not a formal anti-cheat boundary against malicious runtime introspection or Python monkeypatching, and these public tasks should not be used as adversarial leaderboard security proofs. Four adversarial Docker-runtime cases are opt-in tests and remain skipped on this host.
