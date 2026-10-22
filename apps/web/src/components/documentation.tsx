"use client";
import Link from "next/link";
import { DemoButton, PageTitle, Panel } from "./common";
export function Documentation() {
  return (
    <>
      <PageTitle
        title="Documentation"
        description="From the first offline run to reproducible evaluations of configured systems."
        action={<DemoButton />}
      />
      <div className="split">
        <Panel title="A practical guide to BenchLab">
          <article className="prose">
            <h2 id="first-run">Your first experiment</h2>
            <p>
              BenchLab stores configurations, jobs, task results and events in
              one local SQLite workspace. The browser, CLI and Python SDK share
              that evidence. Start with the offline demonstration to exercise
              execution and independent verification without credentials.
            </p>
            <ol>
              <li>
                Choose <strong>Run offline demonstration</strong>. The backend
                queues reference and deliberately flawed deterministic adapters.
              </li>
              <li>
                Follow the experiment in{" "}
                <Link href="/experiments">Live experiments</Link>. Completed
                means orchestration finished; task success is reported
                separately.
              </li>
              <li>
                Open each run in <Link href="/replay">Execution replay</Link> to
                inspect the outputs and verifier evidence.
              </li>
              <li>
                Select both runs in{" "}
                <Link href="/compare">Comparison studio</Link>. Demo results
                validate the pipeline; they do not measure model intelligence.
              </li>
              <li>
                Download JSON, CSV, HTML or an evidence bundle from{" "}
                <Link href="/reports">Reports</Link>.
              </li>
            </ol>
            <h2 id="models">Configure a real model</h2>
            <p>
              Register an <code>openai-compatible</code> endpoint for OpenAI,
              vLLM or llama.cpp servers exposing the chat-completions protocol,
              or <code>ollama</code> for the native Ollama API. Supply the
              provider model identifier exactly. For a local OpenAI-compatible
              Ollama endpoint, the base URL typically includes <code>/v1</code>;
              the native adapter uses the server root.
            </p>
            <p>
              Set a provider API key in the backend environment, then enter its
              variable name in the model form. Never paste the secret value.
              Declare capabilities the adapter can actually fulfill. Run{" "}
              <strong>Probe compatibility</strong> from the inspector before
              creating an experiment.
            </p>
            <pre>
              {
                "OPENAI_API_KEY=<set locally, never commit>\n# Register its variable name: OPENAI_API_KEY\n# Example local base URL: http://127.0.0.1:11434/v1"
              }
            </pre>
            <h2 id="agents">Configure an agent</h2>
            <p>
              The <code>subprocess</code> adapter launches a configured
              executable with a JSON request on stdin and expects a JSON
              response on stdout. Arguments remain an array, never a shell
              command. Environment variables are passed only by an explicit
              allowlist. The <code>codex-cli</code> and{" "}
              <code>opencode-cli</code> registrations are experimental bridges;
              probe the actual installed executable and do not assume every
              release is compatible.
            </p>
            <p>
              Host execution needs two deliberate settings: enable{" "}
              <code>BENCHLAB_ALLOW_HOST_PROCESS=1</code> in the server
              environment and check experiment host-process authorization in the
              builder. Controlled agent comparisons use the same registered
              model. Native products retain their own conditions and must be
              evaluated in native mode.
            </p>
            <h2 id="benchmark">Build and launch an experiment</h2>
            <p>
              Select registered systems, a versioned suite, individual tasks,
              trial count and budget in{" "}
              <Link href="/experiments/new">Experiment builder</Link>. Choose
              workspace isolation for non-code tasks and hardened Docker for
              generated-code verification. Validate compatibility, read every
              reason or warning, then launch.
            </p>
            <p>
              A wall-clock budget covers the whole experiment. Task timeouts and
              retry limits are separate. Token or cost caps require usage
              observability. No provider fallback occurs: unavailable systems
              fail explicitly. Cancellation interrupts the in-flight adapter and
              preserves recorded evidence.
            </p>
            <h2 id="interpretation">Interpret comparisons carefully</h2>
            <p>
              Success rates come from independent exact, structured-output,
              policy, state or sandbox verifiers. Failed executions remain in
              the denominator. Confidence bounds use Wilson intervals; they
              assume independent task outcomes. Public fixture samples are small
              and correlated tasks or repeated trials limit inference. P95
              latency needs at least 20 observations.
            </p>
            <p>
              Condition fingerprints compare suite version, task IDs,
              environment, parameters and evaluation mode. A mismatch stays
              visible. The optimization lab creates a new baseline-linked
              ablation; changed conditions are evidence to inspect, not proof of
              causal improvement. Cost and token values remain unavailable
              unless observed. Hardware and energy are not estimated.
            </p>
            <h2 id="external">External evaluation integrations</h2>
            <p>
              Optional benchmark packages retain upstream datasets and scorers.
              Inspect <Link href="/settings">Diagnostics</Link> and the
              benchmark catalog for installation status. Setup-required
              integrations cannot be launched through the native starter engine.
              Pin dataset and package revisions and preserve upstream licensing
              before running or publishing results.
            </p>
            <h2 id="adapter">Build a versioned adapter</h2>
            <p>
              Implement <code>execute_system</code> and a compatibility probe in
              the Python adapter registry. Accept typed system, task and
              configuration contracts; emit normalized trace events with
              provenance; return <code>AdapterOutput</code>. Provider prompts
              must never receive expected answers. Independent verifiers run
              after adapter execution in the trusted core.
            </p>
            <p>
              The stable extension points are the system under test, task,
              environment, observation, verifier and experiment record. Preserve
              the manifest, isolate task workspaces, avoid shell strings and
              record failures rather than replacing them with invented outputs.
            </p>
            <h2 id="troubleshooting">Troubleshooting</h2>
            <ul>
              <li>
                <strong>API unavailable:</strong> start the backend on loopback
                port 8000. Next.js forwards same-origin <code>/api</code>{" "}
                requests to it.
              </li>
              <li>
                <strong>Docker unavailable:</strong> start a Linux Docker daemon
                and rerun diagnostics. Code execution refuses to run directly on
                the host.
              </li>
              <li>
                <strong>Provider probe failed:</strong> verify base URL, model
                identifier, environment reference and server logs. Registered is
                not the same as connected.
              </li>
              <li>
                <strong>Host process denied:</strong> check both server policy
                and experiment consent. Only explicitly allowed environment
                names reach the child process.
              </li>
              <li>
                <strong>Interrupted run:</strong> restart the worker. Recovery
                preserves interruption instead of marking the run successful.
              </li>
              <li>
                <strong>Missing usage:</strong> the provider did not expose
                enough usage or pricing. Unavailable measurements remain
                unavailable.
              </li>
            </ul>
            <h2 id="api">API and local tools</h2>
            <p>
              The backend exposes its interactive OpenAPI reference at{" "}
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noreferrer"
              >
                127.0.0.1:8000/docs
              </a>
              . Every workspace page uses that same local service. Inspect the
              repository README and CLI <code>--help</code> for installation,
              SDK examples and exact execution commands.
            </p>
          </article>
        </Panel>
        <div>
          <Panel title="On this page">
            <nav
              className="panel-body stack text-xs"
              aria-label="Documentation sections"
            >
              {[
                ["first-run", "First experiment"],
                ["models", "Configure a model"],
                ["agents", "Configure an agent"],
                ["benchmark", "Build and launch"],
                ["interpretation", "Interpret comparisons"],
                ["external", "External integrations"],
                ["adapter", "Build an adapter"],
                ["troubleshooting", "Troubleshooting"],
                ["api", "API and tools"],
              ].map(([id, label]) => (
                <a className="subtle-link" href={`#${id}`} key={id}>
                  {label}
                </a>
              ))}
            </nav>
          </Panel>
        </div>
      </div>
    </>
  );
}
