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
  base_url: "http://127.0.0.1:11434/v1",
  api_key_env: null,
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
  return null;
}
function RegistrationForm({
  kind,
  done,
}: {
  kind: "models" | "agents";
  done: () => void;
}) {
  const [config, setConfig] = useState<ModelConfig | AgentConfig>(
    kind === "models" ? { ...modelDefaults } : { ...agentDefaults },
  );
  const [advanced, setAdvanced] = useState("");
  const [error, setError] = useState<string | null>(null);
  const action = useAction(`/${kind}`, done);
  function update(key: string, value: unknown) {
    setConfig((c) => ({ ...c, [key]: value }));
  }
  function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const merged = { ...config, ...(advanced ? JSON.parse(advanced) : {}) };
      const message = validateRegistration(merged);
      if (message) {
        setError(message);
        return;
      }
      setError(null);
      action.mutate(merged);
    } catch {
      setError("Advanced configuration must be a JSON object.");
    }
  }
  return (
    <form onSubmit={submit} className="stack">
      <div className="form-grid">
        <label className="field">
          <span>Display name</span>
          <Input
            required
            maxLength={120}
            value={config.name}
            onChange={(e) => update("name", e.target.value)}
          />
        </label>
        <label className="field">
          <span>Adapter</span>
          <select
            value={config.adapter}
            onChange={(e) => update("adapter", e.target.value)}
          >
            {(kind === "models"
              ? ["openai-compatible", "ollama", "demo"]
              : ["subprocess", "codex-cli", "opencode-cli", "demo"]
            ).map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </label>
        {"model" in config ? (
          <>
            <label className="field">
              <span>Provider model identifier</span>
              <Input
                required
                value={config.model}
                onChange={(e) => update("model", e.target.value)}
              />
            </label>
            <label className="field">
              <span>Endpoint base URL</span>
              <Input
                type="url"
                value={config.base_url ?? ""}
                onChange={(e) => update("base_url", e.target.value || null)}
              />
              <small>
                Credential-free HTTP(S) URL. Provider requests use the backend.
              </small>
            </label>
            <label className="field">
              <span>API key environment variable</span>
              <Input
                placeholder="OPENAI_API_KEY"
                value={config.api_key_env ?? ""}
                onChange={(e) => update("api_key_env", e.target.value || null)}
              />
              <small>
                Enter a variable name. Configure its value in the server
                environment.
              </small>
            </label>
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
                value={config.executable ?? ""}
                onChange={(e) => update("executable", e.target.value || null)}
              />
              <small>
                Executable path; arguments are a separate JSON array.
              </small>
            </label>
            <label className="field">
              <span>Model flag</span>
              <Input
                value={config.model_flag ?? ""}
                onChange={(e) => update("model_flag", e.target.value || null)}
              />
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
              <span>Native product mode</span>
            </label>
          </>
        )}
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
                : '{"args": ["--json"], "description": "JSON protocol harness"}'
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
function Probe({ kind, id }: { kind: string; id: string }) {
  const action = useAction<Compatibility>(`/${kind}/${id}/probe`);
  return (
    <div>
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
          <Status value={action.data.compatible ? "completed" : "failed"} />
          <JsonView value={action.data} />
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
                  environment variables.
                </DialogDescription>
              </DialogHeader>
              <RegistrationForm kind={kind} done={() => setOpen(false)} />
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
                description="Register an endpoint or execution harness to start evaluating."
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
                  <Probe kind={kind} id={current.id} />
                </div>
                <JsonView value={current.config} />
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
                    href={`/experiments/new?${singular}=${current.id}`}
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
