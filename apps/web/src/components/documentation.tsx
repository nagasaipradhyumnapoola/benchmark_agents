"use client";
import Link from "next/link";
import { DemoButton, PageTitle, Panel } from "./common";
export function Documentation() {
  return (
    <>
      <PageTitle
        title="Documentation"
        description="Connect a model, run a small test, and understand the evidence."
      />
      <div className="split">
        <Panel title="A practical guide to Bench Agents">
          <article className="prose">
            <h2 id="first-run">Your first experiment</h2>
            <p>
              Bench Agents stores your model settings, experiments, results and
              traces in one local SQLite workspace. The browser, terminal and
              Python SDK share the same records. A new workspace starts empty.
            </p>
            <ol>
              <li>
                Open <Link href="/models">Model explorer</Link> and choose{" "}
                <strong>Register model</strong>. Give the configuration a name,
                enter your provider's exact model identifier and endpoint, and
                save. Saving records settings; it does not confirm a working
                connection.
              </li>
              <li>
                In the selected model's inspector, choose{" "}
                <strong>Probe compatibility</strong>. Resolve any reported
                issues before continuing.
              </li>
              <li>
                Choose <strong>Build an experiment with this model</strong>.
                Name the experiment, keep model mode selected and choose{" "}
                <strong>Use one quick text task</strong> for a small first test.
                One trial is enough to check the setup.
              </li>
              <li>
                Choose <strong>Validate compatibility</strong>, review any
                issues, then <strong>Launch experiment</strong>. Follow the run
                in <Link href="/experiments">Live experiments</Link>.
              </li>
              <li>
                Check the passed-task count. A completed run means execution
                finished; each task still has an independent pass or failure.
                Open <Link href="/replay">Execution replay</Link> for the output
                and verification reason.
              </li>
              <li>
                After a second run, use{" "}
                <Link href="/compare">Comparison studio</Link> to compare
                outcomes. Export JSON, CSV, HTML or an evidence bundle in{" "}
                <Link href="/reports">Reports</Link>.
              </li>
            </ol>
            <p>
              Agents are optional. Add one in{" "}
              <Link href="/agents">Agent explorer</Link> when you want to
              compare execution harnesses with a shared model, or evaluate an
              installed product in native mode.
            </p>
            <h2 id="terminal">Use the terminal interface</h2>
            <p>
              From the repository directory, open the interactive workspace. Use
              its menus to browse models and agents, run an experiment, inspect
              results or compare runs.
            </p>
            <pre>
              <code>uv run bench-agents terminal</code>
            </pre>
            <p>
              The terminal and website use the same local workspace by default.
              If you choose a custom data directory, configure both interfaces
              to use it.
            </p>
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
              Choose a hidden session API key or reference a variable in the
              backend environment. Session keys need re-entry after restart.
              Keep secret values out of URLs, names and published source.
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
              executable, sends the task prompt as plain text on stdin, and
              reads the final response as plain text from stdout. Arguments
              remain an array, never a shell command. Environment variables are
              passed only by an explicit allowlist. The <code>codex-cli</code>{" "}
              and <code>opencode-cli</code> registrations are experimental
              bridges; probe the actual installed executable and do not assume
              every release is compatible. For Python harnesses, enter python as
              the executable and the full script path in Script path. Additional
              arguments are available under Advanced configuration.
            </p>
            <p>
              Host execution needs two deliberate settings: enable{" "}
              <code>BENCH_AGENTS_ALLOW_HOST_PROCESS=1</code> in the server
              environment and check experiment host-process authorization in the
              builder. Controlled agent comparisons use the same registered
              model. Set Model flag to the argument your harness accepts, and
              enter the environment variable names it uses for the model
              endpoint and API key. The selected model supplies those values at
              execution time. Native products retain their own conditions and
              must be evaluated in native mode.
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
            <h2 id="demonstration">Optional offline demonstration</h2>
            <p>
              If you want to check the pipeline without a model provider,
              explicitly launch the offline demonstration below. It creates
              reference and deliberately flawed deterministic adapters and
              clearly marks their results as demonstration evidence. These
              results do not measure model intelligence.
            </p>
            <DemoButton />
            <h2 id="agent-hub">Publish and import agents</h2>
            <p>
              <Link href="/hub">Agent Hub</Link> is the connected source
              registry. It starts empty. Browse and import without an account;
              create an account to publish, comment and share results.
            </p>
            <ol>
              <li>
                <strong>Publish an agent:</strong> provide a unique slug,
                semantic version, license, README and Python or Node.js source.
                The harness reads a prompt from stdin and writes its final
                answer to stdout. Add the script entrypoint and recommended
                model IDs.
              </li>
              <li>
                <strong>Configure model bindings:</strong> declare the model
                flag and endpoint/key environment variable names your harness
                expects. Declare dependencies; users review and install them
                separately. Credentials belong in private model settings.
              </li>
              <li>
                <strong>Import agent:</strong> inspect usage, source and the
                release digest first. Import stages that version locally without
                execution or dependency installation.
              </li>
              <li>
                <strong>Benchmark imported agent:</strong> connect a model,
                select one quick task and validate. Trusted host execution needs
                both the server setting and explicit experiment authorization.
              </li>
              <li>
                <strong>Share a completed run:</strong> use its Agent Hub link
                to publish the actual summary to the original release. Reports
                are self-reported; the registry did not run your benchmark.
              </li>
            </ol>
            <p>
              Owners publish new immutable versions for changes. Arbitrary
              frameworks may need a compatible wrapper and separate
              dependencies. Community suggestions use a reviewed GitHub catalog;
              publishing source happens in Agent Hub. The private Lab stays on
              your machine.
            </p>
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
                ["agent-hub", "Publish & import agents"],
                ["terminal", "Terminal interface"],
                ["models", "Configure a model"],
                ["agents", "Configure an agent"],
                ["benchmark", "Build and launch"],
                ["interpretation", "Interpret comparisons"],
                ["external", "External integrations"],
                ["adapter", "Build an adapter"],
                ["troubleshooting", "Troubleshooting"],
                ["demonstration", "Offline demonstration"],
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
