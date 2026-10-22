# MASTER BUILD INSTRUCTION — OPEN-SOURCE AI BENCHMARKING LABORATORY

## YOUR ROLE

You are GPT-6.1 Sol. Act simultaneously as a principal software architect, senior full-stack engineer, AI evaluation researcher, infrastructure engineer, security engineer, and exceptionally skilled product designer.

Your responsibility is to DESIGN, BUILD, INTEGRATE, TEST, DEBUG, VERIFY, DOCUMENT, and PREPARE FOR OPEN-SOURCE RELEASE one complete application.

You are accountable for the final working system—not merely its architecture, screenshots, scaffolding, or individual components.

**This is an implementation assignment. Do not stop after preparing a plan.**

The user expects a complete, polished, technically credible public V1.0 release with a real backend, executable benchmarking engine, real integrations, excellent user experience, automated testing, and thorough documentation.

Do not produce an attractive frontend connected to fabricated data.

Do not make unsupported claims about completeness.

Do not rush to declare success.

---

# 1. PRODUCT MISSION

Build a free, open-source, local-first, extensible AI benchmarking laboratory.

The platform must evaluate:

1. AI model versus AI model.
2. AI agent versus AI agent.
3. Model–agent combinations.
4. Agent harnesses and configurations.
5. Execution quality, reliability, efficiency, cost, security, and failure recovery.
6. Performance changes caused by controlled architectural experiments.

The platform should allow researchers and developers to answer:

- Which model performs better for a particular category?
- Which agent achieves better verified results?
- How much does the agent harness affect a model's performance?
- Which model–agent combination performs best within a defined budget?
- Where did an execution fail?
- What caused the observed failure?
- Which configuration change improved the outcome?
- Are the results reproducible?
- What hardware, compute, memory, and infrastructure are required?

**Core positioning: Test any supported model. Evaluate any supported agent. Understand failures. Verify improvements.**

This is not merely a leaderboard.

It is an experimental system for studying AI capabilities and autonomous execution.

## Long-term architectural requirement

Design the core around six stable abstractions:

- System under test
- Objective/task
- Environment
- Observations
- Verifier
- Experiment record

Future models, tools, modalities, agents, and environments must be extendable through versioned adapters.

Do not hardcode the platform around today's specific models or agent products.

---

# 2. EXECUTION RULES

Before implementation:

1. Inspect the current repository and environment.
2. Read all existing instructions, README files, AGENTS.md files, package manifests, and relevant configuration.
3. Identify existing code and user modifications.
4. Preserve unrelated changes.
5. Create a requirements checklist and architecture plan.
6. Establish clear module ownership and data contracts.
7. Research the current official APIs and documentation for selected frameworks.
8. Confirm actual installation and execution requirements.

Then proceed with implementation.

Do not repeatedly ask for decisions already specified in this prompt.

Make sensible engineering decisions, document them, and continue.

Ask only when a genuinely blocking decision, external authorization, credential, destructive operation, or non-recoverable permission requirement arises.

Do not bypass access controls or approval restrictions.

Never expose or invent API keys.

Do not run unreviewed third-party installation scripts.

Keep brief progress updates and maintain a persistent implementation checklist.

If the task exceeds one coding session, checkpoint the exact implementation status and continue from that state in the next session. Do not restart completed work.

---

# 3. DEVELOPMENT SKILLS — REQUIRED

Inspect and use the relevant instructions from these repositories.

## Engineering and architecture

https://github.com/obra/superpowers

https://github.com/anthropics/skills

https://github.com/fastapi/fastapi

## AI evaluation

https://github.com/huggingface/skills

https://github.com/mlflow/skills

## Infrastructure and data

https://github.com/docker/skills

https://github.com/supabase/agent-skills

## Frontend and design

https://github.com/Leonxlnx/taste-skill

https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

https://github.com/pbakaus/impeccable

https://github.com/vercel-labs/agent-skills

https://github.com/shadcn-ui/ui

## Testing and security

https://github.com/microsoft/playwright-cli

https://github.com/trailofbits/skills

### Skill instructions

Use the repository's appropriate skill files, not every skill indiscriminately.

In particular, apply:

- Test-driven development
- Systematic debugging
- Verification before completion
- Python/FastAPI best practices
- Model and agent evaluation
- Docker security and containerization
- React/Next.js best practices
- Web design guidelines
- `design-taste-frontend`
- `ui-ux-pro-max`
- Impeccable's relevant visual critique and polish workflows
- shadcn/ui component practices
- Playwright browser testing
- Security auditing
- Open-source release readiness

Install skills project-locally when supported. Inspect their contents and dependencies, pin trusted revisions where practical, and avoid executing unfamiliar scripts without review.

If an installation fails, use the corresponding official documentation and continue safely. Report the limitation.

### Design skill priority

When design guidance conflicts, follow this order:

1. Explicit visual requirements in this prompt.
2. Accessibility, correctness, and usability.
3. The project's approved design system.
4. Taste Skill and UI UX Pro Max.
5. General frontend design suggestions.

Do not let a generic design skill override the required black-and-gray aesthetic.

---

# 4. TECHNOLOGY STACK

Use a maintainable, open-source-friendly monorepo.

## Frontend

- Next.js with TypeScript
- React
- Tailwind CSS
- shadcn/ui
- Appropriate shadcn chart components
- Lucide icons where compatible with the configured component system
- Accessible data tables and visualization components
- TanStack Query where server-state management is needed
- Lightweight client-side state management only where appropriate

Use the current official shadcn CLI and documentation.

Inspect `components.json`, the selected primitive base, aliases, icon configuration, and available components.

Use actual shadcn components rather than recreating inferior substitutes.

## Backend

- Python
- FastAPI
- Pydantic
- Typer for the CLI
- Async orchestration where appropriate
- Structured application logging
- Explicit typed interfaces and schemas

## Storage

- SQLite for default local operation
- DuckDB/Parquet for analytical workloads and archived results where useful
- Filesystem-based artifact storage
- Optional PostgreSQL and external object storage through configurable adapters

No database account should be necessary for the default local experience.

## Execution

- Docker for applicable sandboxed tasks
- Isolated task workspaces
- Resource limits
- Configurable timeouts
- Environment reset and cleanup
- Versioned runtime images

## Observability

Use OpenTelemetry-compatible conventions for model calls, agent operations, tools, failures, timing, and execution spans.

Implement a normalized internal event schema for cross-agent comparisons.

## Packaging

- Python package and CLI
- Web application
- Docker Compose configuration where appropriate
- Reproducible dependency lockfiles
- Cross-platform developer scripts
- GitHub Actions

Use stable, compatible versions selected from current official documentation. Do not blindly force the latest version of every dependency.

---

# 5. BENCHMARKING ENGINES

Study and integrate established evaluation infrastructure where appropriate.

Reference repositories:

https://github.com/harbor-framework/harbor

https://github.com/harbor-framework/terminal-bench

https://github.com/EleutherAI/lm-evaluation-harness

https://github.com/huggingface/lighteval

https://github.com/SWE-bench/SWE-bench

https://github.com/xlang-ai/OSWorld-V2

https://github.com/ethz-spylab/agentdojo

Also study the official Inspect AI framework and supported benchmark integrations.

## Critical integration rule

Do not rewrite mature benchmarking frameworks unnecessarily.

Build adapters around their supported public APIs and execution contracts.

Preserve each benchmark's official scoring semantics.

Check compatibility, licensing, dataset restrictions, environment requirements, and benchmark versioning.

Do not claim an integration works merely because its name appears in a dropdown.

Every advertised integration must have executable functionality and tests.

If an external benchmark requires unusually large resources, gated datasets, proprietary credentials, or additional infrastructure, expose its exact requirements and a genuine setup workflow.

Unsupported or unavailable combinations must be clearly labeled.

---

# 6. COMPLETE V1.0 FUNCTIONAL REQUIREMENTS

## A. Model benchmarking

Implement model-to-model comparisons.

Support, through adapters:

- Ollama/local inference
- OpenAI-compatible inference endpoints
- Configurable hosted API providers using user-supplied credentials
- Extensible custom model adapters

The initial working catalog must include enough adapters to run real comparisons between independently configured model endpoints.

Evaluation categories should include:

- Mathematical and logical reasoning
- Coding
- Knowledge and factual accuracy
- Instruction following
- Structured output generation
- Function/tool calling
- Multilingual tasks
- Multimodal tasks for compatible models
- Latency and throughput
- Resource and cost efficiency

For each capability, distinguish between built-in runnable tests, imported external benchmark packs, and unsupported capabilities.

Do not claim to measure private internal reasoning. Measure observable outputs and behavior.

## B. Agent benchmarking

Implement agent-to-agent comparisons through a normalized adapter API.

Provide working integration paths for compatible CLI agents and custom agents.

Prioritize adapters for commonly used coding-agent interfaces, including OpenCode, Codex CLI, and other tools where their current CLI interfaces, authentication, and execution policies permit integration.

A general subprocess/CLI adapter must allow developers to integrate their own tools without modifying the core.

Evaluate:

- Verified task completion
- Tool usage
- Code correctness
- Debugging and recovery
- Human intervention
- Time to verified completion
- Execution cost
- Long-horizon reliability
- Safety and permission compliance
- Artifact quality where independently evaluable

Preserve the native behavior of closed-source tools during full-product comparisons.

## C. Model–agent compatibility

Before executing a benchmark, probe compatibility.

Identify:

- Model endpoint availability
- API support
- Tool-calling support
- Structured output support
- Modality requirements
- Context limitations
- Agent model-selection restrictions
- Authentication requirements
- Runtime/resource limitations

Never silently substitute an unsupported model or agent.

Display compatibility status and specific reasons for incompatibility.

## D. Experiment comparison modes

Implement these as actual usable workflows:

1. Model versus model under fixed evaluation conditions.
2. Agent versus agent using the same model where technically possible.
3. Full native-product versus full native-product.
4. Model × agent combination comparisons.
5. Configuration ablation experiments.
6. Repeated reliability experiments.
7. Comparison with saved historical baselines.

Controlled and native-product comparisons must be labeled separately.

Prevent misleading comparisons across incompatible conditions.

## E. Experiment configuration

Users must be able to configure:

- Models
- Agents
- Benchmarks
- Task subsets
- Run count
- Execution budgets
- Timeouts
- Token limits
- Resource limits
- Isolation settings
- Retry policies
- Available tools
- Verification settings
- Experiment tags and descriptions

Provide validation before launching expensive or unsupported experiments.

## F. Execution management

Implement:

- Job creation
- Queueing
- Running
- Cancellation
- Timeouts
- Failure handling
- Retry policies
- Resource cleanup
- Status persistence
- Crash recovery
- Historical run retrieval
- Live execution progress

A page refresh must not destroy backend execution state.

An interrupted experiment must have an accurate persisted status.

Never display a run as successful merely because the agent process exited normally.

## G. Verification

Implement independently executed verification.

Use, as appropriate:

- Exact-match checks
- Unit and integration tests
- Task-specific executable verifiers
- Schema validation
- Environment state inspection
- Artifact checks
- Security-policy checks
- Human-review rubrics
- Optional calibrated model-based judges

Do not make an LLM judge the sole source of truth for objectively verifiable tasks.

Separate task execution from protected verification logic.

Record verifier version, evidence, and failure reason.

Do not call public test fixtures genuinely secret or contamination-free when they are not.

---

# 7. EXECUTION TRACING AND DIAGNOSTICS

Implement a normalized event timeline.

Capture observable events such as:

- Model request and response metadata
- Tool calls
- Terminal commands
- File modifications
- Test execution
- External requests where permitted
- Errors
- Retries
- Permission denials
- Checkpoints
- Human interventions
- Verification attempts
- Completion and termination

Implement interactive execution replay.

Users should be able to:

- Open a run
- Inspect the timeline
- Expand an event
- Examine commands and outcomes
- Inspect file diffs and artifacts
- Find errors
- Navigate directly to failure events
- Compare two executions side by side
- Download the evidence package

## Failure classification

Implement a transparent taxonomy:

- Model output failure
- Invalid tool arguments
- Tool/environment failure
- Context/state loss
- Repeated unsuccessful action
- Test failure
- Incomplete implementation
- Premature completion
- Timeout/resource exhaustion
- Permission/safety failure
- Infrastructure failure
- Unknown or ambiguous failure

Differentiate confirmed observations from suspected causes.

Never fabricate access to private chain-of-thought information.

## Optimization laboratory

Allow users to compare controlled configuration changes such as:

- Context strategy
- Memory strategy
- Tool availability
- Verification policy
- Retry policy
- Prompt configuration
- Model routing
- Reviewer configuration

The system should show whether an intervention improved verified outcomes under comparable conditions.

Recommendations must be evidence-linked and appropriately qualified.

---

# 8. METRICS AND SCIENTIFIC METHODOLOGY

Implement a typed metric registry with documented definitions.

Core metrics:

- Verified success rate
- Task completion time
- Time to verified result
- Failure rate
- Recovery rate
- Human interventions
- Tool-call counts
- Repeated/failed tool calls
- Token usage where available
- Cost per task
- Cost per verified success
- Median and tail latency when supported by sample size
- CPU/RAM usage
- GPU/VRAM usage where instrumentation is available
- Energy measurements where actually instrumented
- Permission violations
- Reproducibility information

Do not invent missing provider usage or hardware measurements.

Store measurement provenance and indicate whether values are observed, provider-reported, calculated, estimated, or unavailable.

## Statistical requirements

Include:

- Repeated trials
- Paired comparisons where appropriate
- Confidence intervals
- Sample-size warnings
- Variability visualization
- Task-level results
- Failed-run accounting
- Dataset and environment version tracking
- Budget-adjusted comparisons
- Appropriate uncertainty around rankings

Never produce false statistical precision.

Do not collapse unrelated capabilities into a universal intelligence score.

Create category-specific leaderboards and cost–quality Pareto comparisons.

---

# 9. DATA MODEL AND PLUGIN ARCHITECTURE

Design versioned contracts for:

- ModelAdapter
- AgentAdapter
- BenchmarkPack
- TaskDefinition
- EnvironmentProvider
- Verifier
- Metric
- TraceEvent
- RunManifest
- Experiment
- RunResult
- Artifact
- ReportExporter

A run manifest must preserve the exact tested configuration.

Document plugin development and include at least one working example for each primary extension point.

Keep experimental implementations outside the stable core.

Provide schema validation and adapter conformance tests.

A contributor should be able to add a model or benchmark without rewriting the dashboard, scheduler, storage engine, or reporting layer.

---

# 10. SECURITY AND PRIVACY

This is a system that executes AI-generated commands. Treat it as security-sensitive infrastructure.

Implement secure defaults:

- Isolated workspaces
- Least-privilege execution
- No unrestricted host filesystem mounts
- Explicit resource and time limits
- Restricted networking by default where appropriate
- Separate verifier execution
- Controlled artifact collection
- API-key isolation
- Sensitive-value redaction
- No secrets in frontend bundles
- No credentials embedded in reports
- Local storage by default
- No mandatory telemetry
- Explicit permission checks for external actions
- Safe cancellation and cleanup

Do not describe Docker as an absolute security boundary.

Document its limitations and the applicable threat model.

Do not run destructive benchmark tasks against real user data or production systems.

Sensitive data must never be automatically uploaded to a hosted service.

Include automated negative tests for representative security failures.

---

# 11. UI/UX — CRITICAL DESIGN DIRECTIVE

The UI must feel like a premium engineering instrument.

It should be visually competitive with excellent professional developer tools.

It must not look like a generic AI-generated SaaS dashboard.

## Mandatory component framework

**Use shadcn/ui throughout the application.**

Use its official CLI, documented component APIs, semantic tokens, and appropriate composition patterns.

Do not hand-build inferior replacements for available components.

## Mandatory design direction

Create a refined, dark, monochrome product using:

- Deep black
- Graphite
- Charcoal
- Slate gray
- Silver-gray highlights
- Subtle black-to-gray gradients
- Soft neutral borders
- Carefully controlled shadows

Suggested token direction:

- Background: near-black
- Primary surfaces: graphite
- Elevated surfaces: charcoal
- Text: clean off-white
- Secondary text: muted silver
- Borders: restrained neutral gray
- Accent: primarily monochromatic

Use accessible semantic colors only where needed to communicate status, warnings, errors, or distinguish chart series.

Do not introduce bright purple, pink, rainbow gradients, glowing neon, or gratuitous glassmorphism.

Use gradients with restraint: atmospheric depth, subtle surface differentiation, or purposeful focus—not decoration on every component.

Maintain legibility and accessible contrast.

## Typography

Use a disciplined typography system.

Consider Geist Sans for interface text and Geist Mono for technical content.

Typography should establish clear hierarchy through size, weight, spacing, and alignment.

No tiny illegible labels.

No oversized decorative headings inside dense workflows.

## Interface composition

The product should feel like a focused research workspace.

Use:

- Persistent, restrained navigation
- Thoughtfully designed tables
- Strong data hierarchy
- Precise typography
- Excellent filtering and search
- Carefully aligned metric summaries
- Compact but readable inspector panels
- Resizable or collapsible detail regions where useful
- Subtle hover/focus/selection states
- Meaningful loading, empty, error, and success states

Avoid excessive nested cards.

Do not build an entire dashboard from identical rounded rectangles.

Prefer purposeful layouts: tables, timelines, side panels, evidence viewers, charts, and comparison canvases.

## Design skills

Use:

- Taste Skill to establish visual direction and avoid generic output
- UI UX Pro Max to research layout patterns, typography, spacing, and interface conventions
- shadcn/ui rules for component composition
- Vercel React and web design guidelines
- Impeccable for final visual critique and polishing

Before implementation, produce a concise design system with tokens, components, typography, spacing, navigation, and responsive rules.

If image-generation concept tooling is available, develop readable concept references for the main dashboard, comparison view, and execution replay before coding.

Use concepts as references, but keep actual application controls and text code-native.

---

# 12. REQUIRED APPLICATION SCREENS

Implement all of the following with real backend integration.

## 1. Overview

- Recent experiments
- Model and agent inventory
- Run status
- Summary metrics
- Quick benchmark launch
- Recent failures
- Navigable reports

## 2. Model Explorer

- Registered models
- Capabilities
- Provider and local endpoint
- Configuration
- Resource information
- Historical benchmark results
- Model comparison actions

## 3. Agent Explorer

- Registered agents
- Adapter compatibility
- Agent configuration
- Available models
- Execution history
- Benchmark results
- Agent comparison actions

## 4. Benchmark Library

- Searchable benchmark catalog
- Categories
- Dataset versions
- Requirements
- Evaluation methods
- Installation status
- Task counts
- Run actions
- External benchmark setup guidance

## 5. Experiment Builder

A fully functional guided form for constructing experiments.

- Select evaluation mode
- Choose models/agents
- Select benchmark suites
- Configure budgets
- Configure trials
- Validate compatibility
- Show estimated resource requirements where available
- Launch actual backend jobs

## 6. Live Run Monitor

- Live status
- Progress
- Current task
- Events
- Errors
- Timing
- Resource readings
- Cancel action
- View trace

Use real event streaming or an appropriately designed polling mechanism.

## 7. Comparison Studio

- Model versus model
- Agent versus agent
- Model–agent matrix
- Side-by-side metrics
- Per-task results
- Confidence intervals
- Cost versus quality
- Failure comparisons

## 8. Execution Replay

- Timeline
- Event inspector
- Tool details
- Logs
- File diffs
- Verification evidence
- Side-by-side run comparison
- Artifact preview

## 9. Optimization Laboratory

- Baseline selection
- Configuration changes
- Controlled experiment definition
- Run comparisons
- Improvement/regression analysis
- Evidence-backed conclusions

## 10. Reports

- Historical results
- Filtering
- Reproducibility manifests
- Downloadable JSON, CSV, and HTML
- Human-readable summaries
- Clear methodology and limitations

## 11. Integrations and Settings

- Model endpoints
- Local runtime detection
- Agent executables
- Benchmark packages
- Storage settings
- Sandbox settings
- Credential configuration
- Diagnostics
- Import/export

## 12. Documentation and Onboarding

- First-run guide
- Offline demonstration
- Configure a local model
- Configure an agent
- Run a benchmark
- Compare results
- Build an adapter
- Troubleshooting

Every navigation item must lead to a functional screen.

Do not leave buttons, tabs, filters, export actions, or menus inert.

---

# 13. RESPONSIVENESS AND ACCESSIBILITY

The interface must work on desktop and mobile.

Prioritize desktop research workflows while providing usable mobile layouts.

Test at approximately:

- 1440 px
- 1024 px
- 768 px
- 390 px

Required:

- No horizontal viewport overflow
- Readable tables
- Responsive comparison layouts
- Keyboard navigation
- Visible focus states
- Accessible dialogs and forms
- Screen-reader labels
- Proper empty and error states
- Reduced-motion support
- Logical tab order
- Touch-friendly controls

Complex technical views may use intentional internal scrolling or alternative mobile layouts.

Do not simply shrink desktop tables until text becomes unreadable.

Use subtle, performant motion only where it improves understanding.

---

# 14. DEVELOPER EXPERIENCE

The platform must be usable without opening the web UI.

Implement a documented CLI supporting workflows equivalent to:

- `benchlab demo`
- `benchlab doctor`
- `benchlab models list`
- `benchlab agents list`
- `benchlab benchmarks list`
- `benchlab run`
- `benchlab compare`
- `benchlab experiments list`
- `benchlab report`
- `benchlab ui`

These are the intended command semantics. Implement and test the actual commands rather than displaying fictional usage examples.

Provide:

- Clear `--help`
- Argument validation
- Useful error messages
- Machine-readable output
- Nonzero exit codes on actual failures
- Configuration files
- Environment-variable support
- Local offline operation

Include a documented Python SDK and REST API.

Create a zero-credential offline demonstration using deterministic mock implementations and clearly labeled demo results.

This demo validates the execution pipeline, not real model intelligence.

Real model and agent comparisons must use real configured systems.

---

# 15. REPOSITORY STRUCTURE

Create a logical, maintainable monorepo.

Suggested structure:

- `apps/web` — Next.js dashboard
- `apps/api` — FastAPI service
- `packages/core` — benchmark and experiment engine
- `packages/adapters` — model and agent integrations
- `packages/benchmarks` — benchmark packs and verifiers
- `packages/schemas` — shared data contracts
- `packages/telemetry` — execution events and tracing
- `packages/analysis` — metrics and statistical analysis
- `packages/cli` — command-line interface
- `examples` — runnable integrations and examples
- `tests` — unit, integration, security, and end-to-end tests
- `docs` — user and contributor documentation
- `.github` — CI, templates, and automation

Adapt this structure if Python packaging conventions require different placement.

Do not force a structure that breaks packaging or imports.

Keep boundaries clear.

Avoid giant monolithic files, duplicated logic, circular dependencies, and unnecessary abstraction.

---

# 16. BENCHMARK TASKS AND DEMONSTRATIONS

Include a real, independently verified starter task collection covering multiple capabilities.

The suite should contain meaningful tasks, including:

- Reasoning
- Structured outputs
- Coding
- Tool selection
- Multi-step execution
- Error recovery
- Safety constraints

Include deterministic golden fixtures and negative cases.

Also provide tested adapters for established benchmark suites.

Validate imported tasks rather than assuming every upstream task remains runnable.

Do not generate dozens of trivial tasks merely to inflate benchmark counts.

Do not publish arbitrary pass rates from mock agents.

Demo data must be unmistakably identified as demonstration data in both the UI and exported reports.

---

# 17. TESTING REQUIREMENTS

Build a serious automated test suite.

## Backend

- Unit tests
- Integration tests
- Schema validation
- Adapter contract tests
- Experiment lifecycle tests
- Cancellation and timeout tests
- Failure recovery tests
- Statistical calculation tests
- Artifact persistence tests
- Security boundary tests

## Frontend

- Component tests
- Form validation tests
- Navigation tests
- State synchronization tests
- Responsive layout checks
- Accessibility checks
- Real backend integration tests

## End-to-end

Use Playwright.

Test at least:

1. First-run onboarding
2. Offline demonstration
3. Model configuration
4. Agent configuration
5. Benchmark selection
6. Experiment creation
7. Experiment execution
8. Cancellation and failure handling
9. Result inspection
10. Head-to-head comparison
11. Execution replay
12. Report export
13. Page refresh and persisted state
14. Mobile navigation
15. Error and empty states

Run actual browser tests.

Capture screenshots of major pages and states.

Inspect the images, repair layout defects, and rerun.

Passing TypeScript compilation is not evidence of good UI.

## Code quality

Use appropriate linting, formatting, type checking, dependency auditing, and test coverage reporting.

The final build must have no known blocking errors.

---

# 18. FIVE MANDATORY REVIEW PASSES

Do not mark the project complete after the first successful build.

Perform these five independent verification passes.

## PASS 1 — Requirements audit

Compare every requirement in this prompt against actual implementation.

Create a traceability checklist.

For each feature record:

- Implemented code location
- Test or evidence
- Actual working status
- Any remaining limitation

Fix omissions.

## PASS 2 — Benchmark correctness audit

Re-run controlled experiments.

Verify:

- Task reset
- Budget enforcement
- Agent/model identification
- Real evaluation execution
- Independent verification
- Failure accounting
- Metric correctness
- Reproducibility metadata
- Report accuracy

Use deliberately failing test agents to prove that verifiers can reject incorrect results.

## PASS 3 — Security and reliability audit

Review:

- Credential handling
- Secret redaction
- Docker configuration
- Filesystem isolation
- Network restrictions
- Resource limits
- Cancellation
- Crash handling
- Dependency vulnerabilities
- Prompt-injection exposure
- Artifact handling

Fix discovered vulnerabilities and unsafe defaults.

## PASS 4 — UI/UX quality audit

Inspect every important screen in the running browser.

Use actual screenshots.

Check:

- Black/graphite gradient consistency
- Typography
- Component quality
- Alignment
- Table density
- Layout hierarchy
- Responsiveness
- Overflow
- Contrast
- Accessibility
- Motion
- Interaction completeness
- Loading/error states
- Chart readability
- Icon consistency

Apply Taste Skill, UI UX Pro Max, shadcn rules, and visual critique.

Continue polishing until the UI looks like a professional production engineering product.

No generic template appearance.

No decorative fake statistics.

No dead controls.

## PASS 5 — Fresh-install and release audit

Test as if you are a new open-source contributor.

Use a clean environment or disposable checkout.

Verify:

- Installation instructions
- Dependency resolution
- Configuration
- Offline demo
- CLI execution
- API startup
- Web startup
- Browser-to-backend connectivity
- Benchmark execution
- Report generation
- Automated tests
- Packaging
- Documentation
- License and contributor readiness

If a new developer cannot reproduce the advertised core workflow by following the README, the release is not ready.

---

# 19. OPEN-SOURCE RELEASE DELIVERABLES

Prepare the repository with:

- High-quality README
- Product overview
- Architecture documentation
- Local installation guide
- Quickstart
- Troubleshooting
- Configuration documentation
- Benchmark methodology
- Model adapter guide
- Agent adapter guide
- Benchmark authoring guide
- Security model
- Privacy explanation
- API documentation
- CLI documentation
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md
- SECURITY.md
- CHANGELOG.md
- LICENSE
- AGENTS.md
- GitHub issue templates
- Pull request template
- CI workflows
- Reproducible sample results
- Screenshots or a genuine product demonstration

Prefer Apache-2.0 if compatible with the chosen code and dependencies.

Check third-party licenses before incorporating code or datasets.

Prepare the repository for publication, but do not publish it or create external accounts without authorization.

Do not require a hosted account to use the core project.

Do not introduce a mandatory proprietary service.

---

# 20. BUILD STRATEGY

This is **one complete public V1.0**, not a series of incomplete public releases.

You may organize engineering internally into milestones.

However, do not substitute milestone completion for product completion.

Recommended implementation order:

1. Repository inspection and requirements.
2. Technical architecture and core schemas.
3. Design system and full-interface concepts.
4. Model and agent adapter contracts.
5. Experiment orchestration.
6. Secure runtime and task environments.
7. Verifiers and metrics.
8. Persistence and artifacts.
9. CLI and API.
10. Real benchmark integrations.
11. Trace recording and diagnostics.
12. Experiment comparison and statistics.
13. Fully integrated dashboard.
14. Optimization experiments.
15. Reports and exports.
16. Documentation and contributor experience.
17. Automated and browser-based testing.
18. Five verification passes.
19. Release-readiness audit.

At each stage, maintain a runnable application.

Implement backend and frontend contracts together.

Do not build the entire UI with static arrays and attempt to attach a backend at the end.

Do not silently replace a difficult capability with a mock.

Use mock implementations only for explicit offline demonstrations and tests.

---

# 21. ABSOLUTE PROHIBITIONS

Do not:

- Stop after writing the architecture.
- Deliver a frontend-only prototype.
- Claim arbitrary model/agent compatibility.
- Fake benchmark scores.
- Show mock metrics as real results.
- Present incomplete benchmark integrations as supported.
- Claim successful execution without independent verification.
- Hide unsuccessful experiments.
- Expose private credentials.
- Require paid API access for basic local usage.
- Leave UI controls nonfunctional.
- Ignore mobile and accessibility.
- Copy existing benchmark implementations without checking licenses.
- Misrepresent estimated measurements as observed.
- Fabricate citations, traces, screenshots, or test results.
- Delete unrelated repository changes.
- Bypass security or approval restrictions.
- Prioritize visual polish over correctness.
- Prioritize backend functionality while neglecting the UI.
- Declare completion when known blocking defects remain.

If external infrastructure, credentials, permissions, or resources prevent a capability from being exercised, preserve the implementation, mark the exact limitation, and request the minimum necessary user action.

Never claim that blocked functionality was successfully tested.

---

# 22. FINAL ACCEPTANCE CRITERIA

The project is ready for V1.0 only when:

1. A developer can install and run it locally.
2. The offline demonstration works without paid services.
3. Real configured models can be evaluated.
4. Real supported agents can execute benchmark tasks.
5. Model-vs-model comparison works.
6. Agent-vs-agent comparison works.
7. Supported model–agent combinations can be compared.
8. Experiment configuration and lifecycle management work.
9. Sandboxed execution and independent verification work.
10. Failures, retries, and artifacts are recorded.
11. Execution replay works.
12. Statistical comparison and analysis work.
13. Reports export correctly.
14. CLI, API, and dashboard operate on the same persisted experiment data.
15. All important frontend interactions are functional.
16. Automated tests pass.
17. Browser end-to-end tests pass.
18. Security review is completed.
19. A fresh installation reproduces the documented workflow.
20. The repository is ready for responsible open-source publication.

If any criterion fails, continue investigating and fixing it within the available authority.

---

# 23. REQUIRED FINAL HANDOFF

When implementation and verification are complete, provide:

1. Concise product summary.
2. Repository architecture.
3. Implemented features.
4. Supported models, agents, and benchmark integrations.
5. Exact local installation commands.
6. Exact commands to start the backend and frontend.
7. Exact commands for the offline demonstration.
8. Exact commands for a real benchmark.
9. Test results with pass/fail counts.
10. Browser QA summary and screenshots.
11. Security and licensing review summary.
12. Any genuine remaining limitations.
13. Open-source publication readiness status.

Include actual evidence.

Do not report an unverified feature as complete.

---

# FINAL DIRECTIVE

Build something developers will genuinely want to use, researchers will trust, and open-source contributors will enjoy extending.

The platform must be technically rigorous, visually exceptional, accessible, reproducible, and practical.

The graphite-and-black shadcn/ui interface should feel like a meticulously designed engineering instrument—not a generic SaaS template.

The benchmarking engine must produce trustworthy evidence—not vanity scores.

The architecture must be modular enough to support changing model and agent ecosystems for years.

**Own the project from the first repository inspection to the final verified release-ready state.**

Start now. Inspect the repository, load the relevant skills, establish the requirements and design contracts, and begin implementation.

Do not stop at a plan.

Do not claim perfection.

Prove correctness through working software, tests, reproducible experiments, and browser verification.