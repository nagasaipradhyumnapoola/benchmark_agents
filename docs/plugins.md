# Trusted extension development

Stable version-1 data schemas live in `benchlab.schemas`, typing protocols in `benchlab.plugins`, and shared interfaces in [contracts.md](contracts.md). Six abstractions anchor extensions: system under test, objective/task, environment, observations, verifier and experiment record. Do not couple a new model to UI, scheduler or SQLite internals.

For model or agent adapters, implement async `execute(system, model, agent, task, workspace, config, emit) -> AdapterOutput` and `probe(config) -> CompatibilityResult`, then import trusted registration code before constructing the engine/API:

```python
from benchlab.adapters.registry import register_model_adapter
register_model_adapter("my-adapter", execute, probe, version="1.0")
```

`register_agent_adapter` follows the same contract. Registration rejects duplicate names and unsupported versions. Return real output/usage with truthful provenance, respect budgets and cancellation, emit normalized events, and never receive expected answers as prompts. Test conformance with positive, negative and timeout cases. See `examples/adapters/local_plugin.py` for a runnable implementation.

Benchmark packs register validated original TaskDefinition objects with `register_benchmark(id, tasks, metadata, version="1.0")`. Include dataset/task version, license, capabilities, independent verifier type, exact runtime requirements and public/held-out status. Duplicate/unknown task IDs are rejected. Copy tasks before modifying local execution state. Never reuse an upstream benchmark name while changing its official scoring semantics.

`benchlab.plugins.register_environment(name, provider, version="1.0")`, `register_verifier(name, verifier, ...)` and `register_report_exporter(name, exporter, ...)` register the other primary extension points. Built-in names cannot be replaced. EnvironmentProvider prepares the assigned fresh workspace and cleans it in an async finally context, including interrupted tasks; set experiment `workspace_provider` to its registered name. It cannot redirect execution to another host directory or change the declared isolation boundary. A workspace provider does not replace Docker's protected code verifier. A Verifier returns a validated VerificationResult; select it with TaskDefinition.verifier. A ReportExporter receives redacted experiment/run dictionaries and returns bytes; select its name in SDK `lab.report(id, name)`. Custom export downloads are generic binary attachments, and plugins own content escaping and format conventions.

Run `uv run python examples/adapters/extension_points.py` to exercise environment, verifier, benchmark and exporter registration through the real SDK/engine using explicitly labeled demo generation. Tests also reject incorrect outputs and verify cleanup on interruption. Model/agent and benchmark examples are in `local_plugin.py`; the generic real HTTP harness is `minimal_chat_agent.py`. Every extension uses contract version 1.0. Filesystem fixtures must be contained in a fresh workspace. Generated code still requires a separately protected runtime. HTTP cannot supply executable plugin code.

Trusted Python plugins execute with the application's privileges. They are not a hostile plugin sandbox. HTTP configuration can select an already registered adapter, but cannot import modules or install dependencies. Server extension factory example: import your plugin, import `benchlab.api.create_app`, then return `create_app()` from a local factory and start uvicorn with `--factory`. No core scheduler/store/dashboard rewrite is required for a registered model or benchmark.
