"use client";
import { useState } from "react";
import Link from "next/link";
import { Plus, Search, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAction, useApi } from "@/lib/api";
import type {
  AgentConfig,
  Compatibility,
  ModelConfig,
  Registration,
  Run,
} from "@/lib/types";
import {
  Demo,
  Empty,
  ErrorState,
  JsonView,
  Loading,
  PageTitle,
  Panel,
  Status,
} from "./common";
export const modelDefaults: ModelConfig = {
  name: "",
  adapter: "openai-compatible",
  model: "",
  base_url: "http://127.0.0.1:1234/v1",
  api_key_env: null,
  connection_type: "local",
  capabilities: ["text"],
  demo: false,
  description: "",
};
export const agentDefaults: AgentConfig = {
  name: "",
  adapter: "subprocess",
  executable: "",
  args: [],
  model_flag: null,
  capabilities: ["text"],
  env_allowlist: [],
  demo: false,
  native: false,
  description: "",
};
export function validateRegistration(
  config: ModelConfig | AgentConfig,
): string | null {
  if (!config.name.trim()) return "Name is required.";
  if (!config.adapter.trim()) return "Adapter is required.";
  if ("model" in config && !config.model.trim())
    return "Provider model identifier is required.";
  if (
    "api_key_env" in config &&
    config.api_key_env &&
    !/^[A-Za-z_][A-Za-z0-9_]*$/.test(config.api_key_env)
  )
    return "Use an environment variable name, never a secret value.";
  if (
    "env_allowlist" in config &&
    config.env_allowlist.some((s) => !/^[A-Za-z_][A-Za-z0-9_]*$/.test(s))
  )
    return "Environment allowlist accepts variable names only.";
  if (
    "model_flag" in config &&
    [config.model_base_url_env, config.model_api_key_env].some(
      (value) => value && !/^[A-Za-z_][A-Za-z0-9_]*$/.test(value),
    )
  )
    return "Model pairing accepts environment variable names only, never secret values.";
  return null;
}
function RegistrationForm({
  kind,
  done,
}: {
  kind: "models" | "agents";
  done: (id: string) => void;
}) {
  const [config, setConfig] = useState<ModelConfig | AgentConfig>(
    kind === "models" ? { ...modelDefaults } : { ...agentDefaults },
  );
  const [advanced, setAdvanced] = useState("");
  const [script, setScript] = useState("");
  const [argumentsJson, setArgumentsJson] = useState("[]");
  const [error, setError] = useState<string | null>(null);
  const [authentication, setAuthentication] = useState<
    "none" | "session" | "environment"
  >("none");
  const [apiKey, setApiKey] = useState("");
  const action = useAction<Registration<ModelConfig | AgentConfig>>(
    kind === "models" ? "/models/connect" : "/agents",
    (row) => {
      setApiKey("");
      done(row.id);
    },
  );
  function update(key: string, value: unknown) {
    setConfig((c) => ({ ...c, [key]: value }));
  }
  function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const overrides = advanced ? JSON.parse(advanced) : {};
      if (
        !overrides ||
        Array.isArray(overrides) ||
        typeof overrides !== "object"
      )
        throw new Error("overrides");
      let prepared = config;
      if ("executable" in config) {
        const args = JSON.parse(argumentsJson);
        if (
          !Array.isArray(args) ||
          !args.every((value) => typeof value === "string")
        ) {
          setError("Additional arguments must be a JSON array of text values.");
          return;
        }
        prepared = {
          ...config,
          args: [...(script.trim() ? [script.trim()] : []), ...args],
        };
      }
      const merged = { ...prepared, ...overrides };
      if (kind === "models") {
        if (authentication !== "environment")
          (merged as ModelConfig).api_key_env = null;
        if (
          authentication === "session" &&
          (!apiKey.trim() || apiKey.length > 8192)
        ) {
          setError("Enter a session API key of 1–8192 characters.");
          return;
        }
        if (
          authentication === "environment" &&
          !(merged as ModelConfig).api_key_env
        ) {
          setError("Enter the API key environment variable name.");
          return;
        }
        if (
          (merged as ModelConfig).connection_type === "hosted" &&
          merged.adapter !== "openai-compatible"
        ) {
          setError(
            "Hosted APIs require the OpenAI-compatible endpoint adapter.",
          );
          return;
        }
      }
      const message = validateRegistration(merged);
      if (message) {
        setError(message);
        return;
      }
      setError(null);
      action.mutate(
        kind === "models"
          ? {
              config: merged,
              ...(authentication === "session" ? { api_key: apiKey } : {}),
            }
          : merged,
      );
    } catch {
      setError(
        "Advanced configuration must be a JSON object and arguments must be a JSON array.",
      );
    }
  }
  return (
    <form onSubmit={submit} className="stack">
      <p className="registration-note">
        {kind === "models"
          ? "Save the address of a model you can access. After saving, probe compatibility to check that the backend can reach it."
          : "Connect a custom subprocess harness or an installed CLI product. Saving a configuration does not execute it."}
      </p>
      <div className="form-grid">
        {"model" in config ? (
          <label className="field full">
            <span>Connection type</span>
            <select
              aria-label="Connection type"
              value={config.connection_type ?? "local"}
              onChange={(e) => {
                const connection_type = e.target.value as "local" | "hosted";
                setConfig((current) => ({
                  ...current,
                  connection_type,
                  adapter: "openai-compatible",
                  base_url:
                    connection_type === "hosted" ? "" : modelDefaults.base_url,
                  api_key_env: null,
                }));
                setAuthentication(
                  connection_type === "hosted" ? "session" : "none",
                );
                setApiKey("");
              }}
            >
              <option value="local">Local server</option>
              <option value="hosted">Hosted API</option>
            </select>
            <small>
              Connect an existing server. Hosted providers must support the
              OpenAI-compatible API; use the provider's exact endpoint and model
              identifier.
            </small>
          </label>
        ) : null}
        <label className="field">
          <span>Display name</span>
          <Input
            required
            maxLength={120}
            placeholder={
              kind === "models" ? "My local model" : "My agent harness"
            }
            value={config.name}
            onChange={(e) => update("name", e.target.value)}
          />
        </label>
        <label className="field">
          <span>Adapter</span>
          <select
            value={config.adapter}
            onChange={(e) => {
              const adapter = e.target.value;
              setConfig((current) =>
                "model" in current
                  ? {
                      ...current,
                      adapter,
                      base_url:
                        adapter === "ollama"
                          ? "http://127.0.0.1:11434"
                          : adapter === "openai-compatible"
                            ? "http://127.0.0.1:1234/v1"
                            : current.base_url,
                    }
                  : { ...current, adapter },
              );
            }}
          >
            {(kind === "models"
              ? "model" in config && config.connection_type === "hosted"
                ? ["openai-compatible"]
                : ["openai-compatible", "ollama", "demo"]
              : ["subprocess", "codex-cli", "opencode-cli", "demo"]
            ).map((a) => (
              <option key={a} value={a}>
                {
                  (
                    {
                      "openai-compatible": "OpenAI-compatible endpoint",
                      ollama: "Ollama (native API)",
                      subprocess: "Custom subprocess harness",
                      "codex-cli": "Codex CLI (experimental)",
                      "opencode-cli": "OpenCode CLI (experimental)",
                      demo: "Offline demonstration adapter",
                    } as Record<string, string>
                  )[a]
                }
              </option>
            ))}
          </select>
        </label>
        {"model" in config ? (
          <>
            <label className="field">
              <span>Provider model identifier</span>
              <Input
                required
                placeholder="For example: qwen3:8b"
                value={config.model}
                onChange={(e) => update("model", e.target.value)}
              />
              <small>
                The exact model name accepted by your provider, separate from
                the display name.
              </small>
            </label>
            <label className="field">
              <span>Endpoint base URL</span>
              <Input
                type="url"
                value={config.base_url ?? ""}
                onChange={(e) => update("base_url", e.target.value || null)}
              />
              <small>
                For local OpenAI-compatible Ollama: http://127.0.0.1:11434/v1.
                Native Ollama uses the server root.
              </small>
            </label>
            <label className="field full">
              <span>Authentication</span>
              <select
                aria-label="Authentication"
                value={authentication}
                onChange={(e) => {
                  setAuthentication(e.target.value as typeof authentication);
                  setApiKey("");
                  update("api_key_env", null);
                }}
              >
                <option value="none">No API key</option>
                <option value="session">Enter API key for this session</option>
                <option value="environment">
                  Environment variable reference
                </option>
              </select>
              <small>
                Session keys stay only in memory in the running backend.
                Re-enter the key after the backend restarts. The saved
                configuration contains a reference, never the key.
              </small>
            </label>
            {authentication === "session" ? (
              <label className="field full">
                <span>Session API key</span>
                <Input
                  type="password"
                  required
                  maxLength={8192}
                  autoComplete="off"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <small>
                  Sent once to the backend and cleared after saving. Never saved
                  in browser storage or configuration JSON.
                </small>
              </label>
            ) : null}
            {authentication === "environment" ? (
              <label className="field">
                <span>API key environment variable</span>
                <Input
                  placeholder="OPENAI_API_KEY"
                  value={config.api_key_env ?? ""}
                  onChange={(e) =>
                    update("api_key_env", e.target.value || null)
                  }
                />
                <small>
                  Optional for local servers. Enter a variable name, not the
                  key. Set its value in the backend environment.
                </small>
              </label>
            ) : null}
            <label className="field">
              <span>Context window (tokens)</span>
              <Input
                type="number"
                min="1"
                value={config.context_window ?? ""}
                onChange={(e) =>
                  update(
                    "context_window",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
              />
            </label>
          </>
        ) : (
          <>
            <label className="field">
              <span>Executable</span>
              <Input
                placeholder="For example: python"
                value={config.executable ?? ""}
                onChange={(e) => update("executable", e.target.value || null)}
              />
              <small>
                Executable available to the backend, such as python or your
                installed CLI's full path.
              </small>
            </label>
            <label className="field">
              <span>Script path (optional)</span>
              <Input
                placeholder="For example: C:/agents/my_agent.py"
                value={script}
                onChange={(e) => setScript(e.target.value)}
              />
              <small>
                For a script-based harness. Passed as the first executable
                argument.
              </small>
            </label>
            <label className="field">
              <span>Model flag</span>
              <Input
                placeholder="For example: --model"
                value={config.model_flag ?? ""}
                onChange={(e) => update("model_flag", e.target.value || null)}
              />
              <small>
                For controlled comparisons. Native products use their own model
                settings.
              </small>
            </label>
            <label className="field">
              <span>Model endpoint environment variable</span>
              <Input
                placeholder="For example: MODEL_BASE_URL"
                value={config.model_base_url_env ?? ""}
                onChange={(e) =>
                  update("model_base_url_env", e.target.value || null)
                }
              />
              <small>
                Your harness reads the paired model's endpoint from this
                variable.
              </small>
            </label>
            <label className="field full">
              <span>Model API key environment variable</span>
              <Input
                placeholder="For example: MODEL_API_KEY"
                value={config.model_api_key_env ?? ""}
                onChange={(e) =>
                  update("model_api_key_env", e.target.value || null)
                }
              />
              <small>
                Your harness reads the paired model's API key from this
                variable. Enter its name, never the secret value.
              </small>
            </label>
            <label className="field full">
              <span>Environment allowlist</span>
              <Input
                placeholder="VARIABLE_ONE, VARIABLE_TWO"
                value={config.env_allowlist.join(", ")}
                onChange={(e) =>
                  update(
                    "env_allowlist",
                    e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  )
                }
              />
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={config.native}
                onChange={(e) => update("native", e.target.checked)}
              />
              <span>
                <strong>Native product mode</strong>
                <small>
                  Use the installed product's own model and settings. Leave
                  unchecked to pair a custom subprocess harness with a
                  registered model.
                </small>
              </span>
            </label>
          </>
        )}
      </div>
      <details className="details-disclosure">
        <summary>Advanced configuration</summary>
        <div className="form-grid">
          {kind === "agents" ? (
            <label className="field full">
              <span>Additional arguments (JSON)</span>
              <textarea
                rows={2}
                value={argumentsJson}
                onChange={(e) => setArgumentsJson(e.target.value)}
              />
              <small>
                An array such as ["--json"]. Arguments are passed directly
                without a shell.
              </small>
            </label>
          ) : null}
          <label className="field full">
            <span>Capabilities</span>
            <Input
              value={config.capabilities.join(", ")}
              onChange={(e) =>
                update(
                  "capabilities",
                  e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                )
              }
            />
            <small>
              Comma separated; declare only verified adapter capabilities.
            </small>
          </label>
          <label className="field full">
            <span>Description</span>
            <textarea
              rows={2}
              value={config.description}
              onChange={(e) => update("description", e.target.value)}
            />
          </label>
          <label className="field full">
            <span>Advanced configuration overrides (JSON)</span>
            <textarea
              rows={3}
              placeholder={
                kind === "models"
                  ? '{"input_cost_per_million": null, "output_cost_per_million": null}'
                  : '{"args": ["--json"], "description": "Subprocess harness"}'
              }
              value={advanced}
              onChange={(e) => setAdvanced(e.target.value)}
            />
            <small>
              All schema fields are accepted; unknown fields are rejected by the
              server.
            </small>
          </label>
          <label className="check-row">
            <input
              type="checkbox"
              checked={config.demo}
              onChange={(e) => update("demo", e.target.checked)}
            />
            <span>Explicit demonstration configuration</span>
          </label>
        </div>
      </details>
      {error ? (
        <p role="alert" className="notice error">
          {error}
        </p>
      ) : null}
      <ErrorState error={action.error} />
      <Button type="submit" disabled={action.isPending}>
        {action.isPending ? "Registering…" : "Register configuration"}
      </Button>
    </form>
  );
}
function Probe({
  kind,
  id,
  native = false,
  sessionCredential = false,
}: {
  kind: string;
  id: string;
  native?: boolean;
  sessionCredential?: boolean;
}) {
  const action = useAction<Compatibility>(`/${kind}/${id}/probe`);
  const [apiKey, setApiKey] = useState("");
  const credential = useAction<{ configured: boolean; scope: string }>(
    `/models/${id}/credential`,
    () => {
      setApiKey("");
      action.reset();
    },
  );
  return (
    <div>
      {sessionCredential ? (
        <form
          className="stack mb-4"
          onSubmit={(event) => {
            event.preventDefault();
            credential.mutate({ api_key: apiKey });
          }}
        >
          <p className="registration-note">
            This key is held only in memory in the running backend. Re-enter it
            after the backend restarts, then probe compatibility again.
          </p>
          <label className="field">
            <span>Re-enter session API key</span>
            <Input
              type="password"
              required
              maxLength={8192}
              autoComplete="off"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
            />
          </label>
          <Button
            type="submit"
            variant="outline"
            size="sm"
            disabled={!apiKey.trim() || credential.isPending}
          >
            Update session key
          </Button>
          <ErrorState error={credential.error} />
          {credential.isSuccess ? (
            <p role="status" className="registration-note">
              Session key updated. Probe compatibility to check the connection.
            </p>
          ) : null}
        </form>
      ) : null}
      <p className="registration-note mb-4">
        Configuration saved. Check compatibility before using it in an
        experiment.
      </p>
      <Button
        variant="outline"
        size="sm"
        disabled={action.isPending}
        onClick={() => action.mutate({})}
      >
        <ShieldCheck size={13} />
        {action.isPending ? "Probing…" : "Probe compatibility"}
      </Button>
      <ErrorState error={action.error} />
      {action.data ? (
        <div className="section-gap">
          <h3 className="text-sm">
            {action.data.compatible
              ? "Compatibility confirmed"
              : "Compatibility check failed"}
          </h3>
          {action.data.reasons.map((reason, i) => (
            <p className="registration-note mt-2" key={i}>
              {reason}
            </p>
          ))}
          {action.data.warnings.map((warning, i) => (
            <p className="registration-note mt-2" key={i}>
              {warning}
            </p>
          ))}
          {!action.data.compatible ? (
            <Link href="/docs#troubleshooting" className="subtle-link mt-3">
              Troubleshoot this connection →
            </Link>
          ) : (
            <div className="registration-next">
              <Link
                href={`/experiments/new?${kind === "models" ? "model" : "agent"}=${id}${native ? "&mode=native" : ""}`}
                className="subtle-link"
              >
                Build an experiment with this{" "}
                {kind === "models" ? "model" : "agent"} →
              </Link>
              {kind === "models" ? (
                <Link href="/agents" className="subtle-link">
                  Or register an agent to compare harnesses →
                </Link>
              ) : null}
            </div>
          )}
          <details className="details-disclosure">
            <summary>Technical probe evidence</summary>
            <JsonView value={action.data} />
          </details>
        </div>
      ) : null}
    </div>
  );
}
export function Registry({ kind }: { kind: "models" | "agents" }) {
  const query = useApi<Registration<ModelConfig | AgentConfig>[]>(`/${kind}`);
  const runs = useApi<Run[]>("/runs");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [open, setOpen] = useState(false);
  const rows =
    query.data?.filter((r) =>
      `${r.config.name} ${r.config.adapter} ${r.id}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) ?? [];
  const current = query.data?.find((r) => r.id === selected);
  const history =
    runs.data?.filter(
      (r) =>
        r.system_id === selected ||
        JSON.stringify(r.manifest.system ?? {}).includes(selected),
    ) ?? [];
  const singular = kind === "models" ? "model" : "agent";
  return (
    <>
      <PageTitle
        title={kind === "models" ? "Model explorer" : "Agent explorer"}
        description={`Inspect registered ${singular} configurations, compatibility and persisted execution history.`}
        action={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus size={15} />
                Register {singular}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[700px]">
              <DialogHeader>
                <DialogTitle>Register {singular} configuration</DialogTitle>
                <DialogDescription>
                  New versions preserve historical identity. Credentials stay in
                  environment references or memory in the running backend.
                </DialogDescription>
              </DialogHeader>
              <RegistrationForm
                kind={kind}
                done={(id) => {
                  setSelected(id);
                  setSearch("");
                  setOpen(false);
                }}
              />
            </DialogContent>
          </Dialog>
        }
      />
      <div className="toolbar">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-3 text-muted-foreground"
          />
          <Input
            aria-label={`Search ${kind}`}
            placeholder={`Search ${kind}…`}
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      <ErrorState error={query.error} retry={() => query.refetch()} />
      {query.isPending ? (
        <Loading />
      ) : (
        <div className="split">
          <Panel
            title={`Registered ${kind}`}
            detail={`${rows.length} configurations · select to inspect`}
          >
            {rows.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Name / identifier</th>
                      <th>Adapter</th>
                      <th>Capabilities</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id}>
                        <td>
                          <button
                            className="table-primary text-left"
                            onClick={() => setSelected(r.id)}
                          >
                            {r.config.name}
                          </button>
                          <small className="mono">
                            {r.id} {r.config.demo ? <Demo compact /> : null}
                          </small>
                        </td>
                        <td>{r.config.adapter}</td>
                        <td>{r.config.capabilities.join(", ")}</td>
                        <td>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelected(r.id)}
                          >
                            Inspect
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty
                title={
                  search
                    ? "No matching configurations"
                    : `No ${kind} registered`
                }
                description={
                  kind === "models"
                    ? "Use Register model to save your endpoint and model identifier, then probe the connection."
                    : "Use Register agent to connect a subprocess harness or installed CLI. Model-only experiments can run without an agent."
                }
                demo={!search}
              />
            )}
          </Panel>
          <Panel
            title={current ? current.config.name : "Configuration inspector"}
          >
            {current ? (
              <>
                <div className="panel-body">
                  <Probe
                    key={current.id}
                    kind={kind}
                    id={current.id}
                    native={"native" in current.config && current.config.native}
                    sessionCredential={
                      kind === "models" &&
                      "api_key_env" in current.config &&
                      !!current.config.api_key_env?.startsWith(
                        "BENCH_AGENTS_SESSION_",
                      )
                    }
                  />
                </div>
                <details className="details-disclosure">
                  <summary>Saved configuration (JSON)</summary>
                  <JsonView value={current.config} />
                </details>
                <div className="panel-body">
                  <h3 className="text-sm mb-3">Execution history</h3>
                  {history.length ? (
                    history.map((r) => (
                      <Link
                        className="inventory-item"
                        href={`/replay?run=${r.id}`}
                        key={r.id}
                      >
                        <span>Trial {r.trial}</span>
                        <Status value={r.status} />
                      </Link>
                    ))
                  ) : (
                    <p className="muted text-xs">
                      No persisted runs for this configuration.
                    </p>
                  )}
                  <Link
                    className="subtle-link mt-4"
                    href={`/experiments/new?${singular}=${current.id}${"native" in current.config && current.config.native ? "&mode=native" : ""}`}
                  >
                    Use in experiment →
                  </Link>
                </div>
              </>
            ) : (
              <div className="panel-body muted text-xs leading-6">
                Select a configuration to inspect its endpoint, capability
                declaration, probe result and execution history. Hardware use is
                unavailable unless observed by the runtime.
              </div>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}
