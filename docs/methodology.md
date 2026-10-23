# Benchmark methodology

Bench Agents compares observable system behavior against an explicit objective, environment and independent verifier. It does not measure private reasoning or collapse unrelated capabilities into an intelligence score.

## Original public starter set

`starter-v1` version 1.0.0 contains ten original public fixtures. The default eight cover inventory arithmetic, HTTP knowledge, Spanish instructions, numeric JSON extraction, tool-selection planning, ordered ledger state, retry-state planning and an explicit untrusted-instruction constraint. These are a small public demonstration/contract suite, not a representative held-out capability benchmark. Workspace normalization and Docker code behavior verification are opt-in tasks. Task counts, versions and selected IDs are preserved in each manifest.

The deterministic reference and deliberately flawed adapters exist exclusively for offline demonstration and tests. Both go through ordinary execution and verifier code. They cannot mix with real observations. Expected results are kept outside provider prompts and native writable workspaces. Public fixtures are not secret; memorization and contamination are possible.

## Outcomes and failure accounting

`completed` describes finished orchestration. Only independent verification sets a task's `passed` value. Failed, timed-out, rejected and budget-exhausted task records remain visible. Cancellation preserves partial results and does not invent unattempted future systems. Interrupted jobs are marked interrupted; restart does not silently claim success.

Token/cost caps stop subsequent tasks after reported usage. A single in-flight provider call can exceed a reported-usage cap before usage is returned; this is not a hard provider spending guarantee. Unknown usage under a requested cap fails closed. A shared experiment budget can starve later scheduled systems; those runs must not be ranked as equal opportunities. Allocate sufficient budget or run independent matched trials.

## Measurement provenance

Durations are wall-clock observations, including verification for task-completion metrics. Token counts are provider-reported. Cost requires both usage counts and user-supplied prices and is an estimate calculated from them. Null means unavailable, never zero. Native CLI tools may not expose usage/tool/human-intervention events; no measurements are fabricated. Host diagnostics are not per-run CPU/GPU/energy measurements. Uninstrumented resources remain unavailable.

`/api/metrics` lists typed metric definitions and provenance. Event records include timestamps, trace/span identifiers, observable operation type and evidence; they are compatible with OpenTelemetry concepts, not a claim that private provider traces were accessed.

## Comparisons and uncertainty

Condition fingerprints cover objective/task versions, selected tasks, environment/resources/network, evaluation mode, sampling parameters, seed, timeout, retry policy, budgets and controlled model identity where applicable. Strict comparison rejects mismatches, unfinished runs, mixed demo/real provenance and starvation from ordered budgets. Native-product and controlled-model runs are distinct conditions. Provider discovery does not establish generation, tool support, context size or authentication beyond what the probe actually observed.

Wilson 95% intervals describe the observed task pass fraction under an independent Bernoulli-task assumption. Correlated tasks and repeated identical fixtures violate independence; intervals do not establish general model-population performance. Median latency is shown when observed; p95 is withheld below 20 samples. Paired exact McNemar calculations are exploratory and have no multiple-comparison correction. Category summaries preserve capability distinctions. Pareto eligibility requires observed quality, cost and latency; missing cost produces no invented frontier membership.

Baseline-linked ablations enumerate changed knobs and report observed paired improvements/regressions only with matching task/environment identity. Changed treatment conditions remain explicit; this is not a randomized causal claim. Inert/unsupported configuration options must be rejected rather than presented as effective interventions.

## Upstream frameworks

Inspect AI and lm-eval retain their official scorers, metric names, versions and raw result artifacts. Their outputs are not silently converted into starter pass/fail. Dataset/model licensing and restrictions remain separate. Large-suite execution, credentialed agents and real-model performance require the exact additional setup documented in the integration matrix. A successful fixture/CLI parser test is not evidence an entire upstream benchmark was run.
