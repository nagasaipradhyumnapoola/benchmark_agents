"use client";
import { useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { FlaskConical, Play, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAction, useApi } from "@/lib/api";
import type {
  AgentConfig,
  Benchmark,
  Compatibility,
  Experiment,
  ExperimentConfig,
  ModelConfig,
  Registration,
  SystemSpec,
} from "@/lib/types";
import {
  Demo,
  ErrorState,
  JsonView,
  Loading,
  PageTitle,
  Panel,
  Status,
} from "./common";
export const defaultExperiment: ExperimentConfig = {
  name: "",
  mode: "model",
  systems: [],
  benchmark_id: "starter-v1",
  task_ids: [],
  trials: 1,
  budget_seconds: 300,
  task_timeout_seconds: 30,
  max_tokens: 2048,
  retries: 0,
  memory_mb: 256,
  cpus: 1,
  isolation: "workspace",
  allow_host_process: false,
  network: false,
  tools: [],
  seed: 42,
  demo: false,
};
export function validateExperiment(config: ExperimentConfig): string | null {
  if (!config.name.trim()) return "Name the experiment before validating.";
  if (!config.systems.length) return "Select at least one system to evaluate.";
  if (config.trials < 1 || config.trials > 50)
    return "Trials must be between 1 and 50.";
  if (config.budget_seconds <= 0)
    return "Wall-clock budget must be greater than zero.";
  if (config.task_timeout_seconds > config.budget_seconds)
    return "Task timeout cannot exceed the experiment budget.";
  return null;
}
export function Builder() {
  const params = useSearchParams();
  const router = useRouter();
  const models = useApi<Registration<ModelConfig>[]>("/models");
  const agents = useApi<Registration<AgentConfig>[]>("/agents");
  const suites = useApi<Benchmark[]>("/benchmarks");
  const [config, setConfig] = useState<ExperimentConfig>(() => ({
    ...defaultExperiment,
    benchmark_id: params.get("benchmark") || "starter-v1",
    systems: params.get("model")
      ? [{ model_id: params.get("model")! }]
      : params.get("agent")
        ? [{ agent_id: params.get("agent")! }]
        : [],
    mode: params.get("agent")
      ? params.get("mode") === "native"
        ? "native"
        : "agent"
      : "model",
  }));
  const catalog = useApi<Benchmark>(`/benchmarks/${config.benchmark_id}`);
  const [sharedModel, setSharedModel] = useState("");
  const [validation, setValidation] = useState<Compatibility | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [advanced, setAdvanced] = useState("");
  const validate = useAction<Compatibility>(
    "/experiments/validate",
    setValidation,
  );
  const launch = useAction<Experiment>("/experiments", (row) =>
    router.push(`/experiments?id=${row.id}`),
  );
  function update(key: string, value: unknown) {
    setConfig((c) => ({ ...c, [key]: value }));
    setValidation(null);
  }
  function systemToggle(system: SystemSpec) {
    const key = JSON.stringify(system);
    update(
      "systems",
      config.systems.some((s) => JSON.stringify(s) === key)
        ? config.systems.filter((s) => JSON.stringify(s) !== key)
        : [...config.systems, system],
    );
  }
  function payload() {
    const overrides = advanced ? JSON.parse(advanced) : {};
    if (!overrides || Array.isArray(overrides) || typeof overrides !== "object")
      throw new Error("overrides");
    const value = { ...config, ...overrides };
    value.demo = value.systems.some(
      (s: SystemSpec) =>
        models.data?.find((m) => m.id === s.model_id)?.config.demo ||
        agents.data?.find((a) => a.id === s.agent_id)?.config.demo,
    );
    return value;
  }
  function act(execute: boolean) {
    try {
      const data = payload();
      const error = validateExperiment(data);
      if (error) {
        setLocalError(error);
        return;
      }
      setLocalError(null);
      if (execute) launch.mutate(data);
      else validate.mutate(data);
    } catch {
      setLocalError("Advanced overrides must contain a valid JSON object.");
    }
  }
  const availableAgents =
    agents.data?.filter((agent) =>
      config.mode === "native"
        ? agent.config.native
        : config.mode === "agent"
          ? !agent.config.native
          : true,
    ) ?? [];
  const selectedDemo = config.systems.some(
    (s) =>
      models.data?.find((m) => m.id === s.model_id)?.config.demo ||
      agents.data?.find((a) => a.id === s.agent_id)?.config.demo,
  );
  return (
    <>
      <PageTitle
        title="Experiment builder"
        description="Define the systems, fixed conditions and execution budget before queueing a real job."
      />
      <ErrorState error={models.error || agents.error || suites.error} />
      {models.isPending || agents.isPending ? (
        <Loading />
      ) : (
        <div className="split">
          <div className="stack">
            {selectedDemo ? <Demo /> : null}
            <Panel
              title="Experiment definition"
              detail="One immutable configuration for reproducible execution"
            >
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  act(false);
                }}
              >
                <div className="form-section">
                  <div className="form-grid">
                    <label className="field">
                      <span>Experiment name</span>
                      <Input
                        required
                        maxLength={160}
                        placeholder="Reasoning baseline · revision 1"
                        value={config.name}
                        onChange={(e) => update("name", e.target.value)}
                      />
                    </label>
                    <label className="field">
                      <span>Evaluation mode</span>
                      <select
                        value={config.mode}
                        onChange={(e) => {
                          update("mode", e.target.value);
                          update("systems", []);
                        }}
                      >
                        {[
                          "model",
                          "agent",
                          "native",
                          "matrix",
                          "ablation",
                          "reliability",
                          "baseline",
                        ].map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field full">
                      <span>Description / hypothesis</span>
                      <textarea
                        rows={2}
                        value={config.description ?? ""}
                        onChange={(e) => update("description", e.target.value)}
                      />
                    </label>
                  </div>
                </div>
                <div className="form-section">
                  <h2>Systems under test</h2>
                  <p className="muted text-xs mb-3">
                    {config.mode === "model"
                      ? "Select the registered models to evaluate. For a first run, one model is enough."
                      : "Controlled agent comparisons use one shared model. Native mode uses each installed product's own model and settings."}
                  </p>
                  {(
                    config.mode === "model"
                      ? !models.data?.length
                      : !availableAgents.length
                  ) ? (
                    <div className="notice info">
                      <div>
                        <strong>
                          {config.mode === "model"
                            ? "Register a model before launching"
                            : "Register an agent before launching"}
                        </strong>
                        <p>
                          {config.mode === "model"
                            ? "Save your endpoint and model identifier, then check compatibility."
                            : "Add a custom harness or an installed CLI product in Agent explorer."}
                        </p>
                        <Link
                          className="subtle-link"
                          href={config.mode === "model" ? "/models" : "/agents"}
                        >
                          {config.mode === "model"
                            ? "Open Model explorer"
                            : "Open Agent explorer"}{" "}
                          →
                        </Link>
                      </div>
                    </div>
                  ) : null}
                  {["agent", "native", "matrix"].includes(config.mode) ? (
                    <>
                      {config.mode !== "native" ? (
                        <label className="field mb-3">
                          <span>Shared model for agent evaluation</span>
                          <select
                            value={sharedModel}
                            onChange={(e) => {
                              setSharedModel(e.target.value);
                              update(
                                "systems",
                                config.systems.map((s) => ({
                                  ...s,
                                  model_id: e.target.value || undefined,
                                })),
                              );
                            }}
                          >
                            <option value="">
                              Select model, or native product default
                            </option>
                            {models.data?.map((m) => (
                              <option value={m.id} key={m.id}>
                                {m.config.name}
                              </option>
                            ))}
                          </select>
                        </label>
                      ) : (
                        <p className="registration-note mb-4">
                          Native products use their own model and provider
                          settings. A registered model is not paired in this
                          mode.
                        </p>
                      )}
                      {availableAgents.map((a) => (
                        <label className="check-row" key={a.id}>
                          <input
                            type="checkbox"
                            checked={config.systems.some(
                              (s) => s.agent_id === a.id,
                            )}
                            onChange={() => {
                              const exists = config.systems.some(
                                (s) => s.agent_id === a.id,
                              );
                              update(
                                "systems",
                                exists
                                  ? config.systems.filter(
                                      (s) => s.agent_id !== a.id,
                                    )
                                  : [
                                      ...config.systems,
                                      {
                                        agent_id: a.id,
                                        model_id:
                                          config.mode === "native"
                                            ? undefined
                                            : sharedModel || undefined,
                                      },
                                    ],
                              );
                            }}
                          />
                          <span>
                            <strong>
                              {a.config.name}{" "}
                              {a.config.demo ? <Demo compact /> : null}
                            </strong>
                            <small>
                              {a.config.adapter} ·{" "}
                              {a.config.capabilities.join(", ")}
                            </small>
                          </span>
                        </label>
                      ))}
                    </>
                  ) : (
                    models.data?.map((m) => (
                      <label className="check-row" key={m.id}>
                        <input
                          type="checkbox"
                          checked={config.systems.some(
                            (s) => s.model_id === m.id,
                          )}
                          onChange={() => systemToggle({ model_id: m.id })}
                        />
                        <span>
                          <strong>
                            {m.config.name}{" "}
                            {m.config.demo ? <Demo compact /> : null}
                          </strong>
                          <small>
                            {m.config.adapter} ·{" "}
                            {m.config.capabilities.join(", ")}
                          </small>
                        </span>
                      </label>
                    ))
                  )}
                </div>
                <div className="form-section">
                  <h2>Benchmark and task selection</h2>
                  <label className="field">
                    <span>Benchmark suite</span>
                    <select
                      value={config.benchmark_id}
                      onChange={(e) => {
                        update("benchmark_id", e.target.value);
                        update("task_ids", []);
                      }}
                    >
                      {suites.data?.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name} · {b.version}
                        </option>
                      ))}
                    </select>
                    <small>
                      Choose individual tasks below. Empty selection executes
                      the eight standard text tasks. Coding and workspace tasks
                      require explicit selection.
                    </small>
                  </label>
                  <ErrorState error={catalog.error} />
                  <div className="task-grid">
                    {catalog.data?.tasks?.map((t) => (
                      <label className="check-row" key={t.id}>
                        <input
                          type="checkbox"
                          checked={config.task_ids.includes(t.id)}
                          onChange={() =>
                            update(
                              "task_ids",
                              config.task_ids.includes(t.id)
                                ? config.task_ids.filter((id) => id !== t.id)
                                : [...config.task_ids, t.id],
                            )
                          }
                        />
                        <span>
                          <strong>{t.name}</strong>
                          <small>
                            {t.category} ·{" "}
                            {t.requires_execution
                              ? "Docker required"
                              : t.verifier}
                          </small>
                        </span>
                      </label>
                    ))}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    className="mt-4 mr-3"
                    onClick={() => {
                      const task = catalog.data?.tasks?.find(
                        (t) =>
                          !t.requires_execution &&
                          !t.required_capabilities?.includes("workspace"),
                      );
                      if (task) update("task_ids", [task.id]);
                    }}
                    disabled={
                      !catalog.data?.tasks?.some(
                        (t) =>
                          !t.requires_execution &&
                          !t.required_capabilities?.includes("workspace"),
                      )
                    }
                  >
                    Use one quick text task
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    className="mt-3"
                    onClick={() =>
                      update(
                        "task_ids",
                        catalog.data?.tasks
                          ?.filter(
                            (t) =>
                              !t.requires_execution &&
                              !t.required_capabilities?.includes("workspace"),
                          )
                          .map((t) => t.id) ?? [],
                      )
                    }
                  >
                    Select standard text tasks
                  </Button>
                </div>
                <div className="form-section">
                  <h2>Budget and reproducibility</h2>
                  <div className="form-grid">
                    <label className="field">
                      <span>Trials</span>
                      <Input
                        type="number"
                        min="1"
                        max="50"
                        value={config.trials}
                        onChange={(e) =>
                          update("trials", Number(e.target.value))
                        }
                      />
                      <small>
                        Repeat each system under the same conditions. Start with
                        1.
                      </small>
                    </label>
                    <label className="field">
                      <span>Total wall-clock budget (s)</span>
                      <Input
                        type="number"
                        min="1"
                        max="86400"
                        value={config.budget_seconds}
                        onChange={(e) =>
                          update("budget_seconds", Number(e.target.value))
                        }
                      />
                      <small>Maximum time for the whole experiment.</small>
                    </label>
                  </div>
                  {["agent", "native", "matrix"].includes(config.mode) ? (
                    <>
                      {" "}
                      <label className="check-row">
                        <input
                          type="checkbox"
                          checked={config.allow_host_process}
                          onChange={(e) =>
                            update("allow_host_process", e.target.checked)
                          }
                        />
                        <span>
                          <strong>
                            Authorize host agent processes for this experiment
                          </strong>
                          <small>
                            Required for local CLI agent adapters; generated
                            code still requires Docker.
                          </small>
                        </span>
                      </label>
                    </>
                  ) : null}
                  <details className="details-disclosure">
                    <summary>Advanced limits, isolation and parameters</summary>
                    <div className="form-grid">
                      {(
                        [
                          ["task_timeout_seconds", "Task timeout (s)", 1, 3600],
                          ["max_tokens", "Max tokens per task", 1, 131072],
                          ["retries", "Retry limit", 0, 3],
                          ["seed", "Seed", 0, 2147483647],
                          ["memory_mb", "Sandbox memory (MiB)", 64, 32768],
                          ["cpus", "Sandbox CPU limit", 0.1, 16],
                        ] as const
                      ).map(([key, label, min, max]) => (
                        <label className="field" key={key}>
                          <span>{label}</span>
                          <Input
                            type="number"
                            min={min}
                            max={max}
                            step={key === "cpus" ? ".1" : "1"}
                            value={config[key]}
                            onChange={(e) =>
                              update(key, Number(e.target.value))
                            }
                          />
                        </label>
                      ))}
                      <label className="field">
                        <span>Total token budget (optional)</span>
                        <Input
                          type="number"
                          min="1"
                          value={config.max_total_tokens ?? ""}
                          onChange={(e) =>
                            update(
                              "max_total_tokens",
                              e.target.value ? Number(e.target.value) : null,
                            )
                          }
                        />
                      </label>
                      <label className="field">
                        <span>Total cost budget, USD (optional)</span>
                        <Input
                          type="number"
                          min="0.000001"
                          step="any"
                          value={config.max_cost_usd ?? ""}
                          onChange={(e) =>
                            update(
                              "max_cost_usd",
                              e.target.value ? Number(e.target.value) : null,
                            )
                          }
                        />
                        <small>
                          Requires provider usage and configured pricing.
                        </small>
                      </label>
                      <label className="field">
                        <span>Isolation</span>
                        <select
                          value={config.isolation}
                          onChange={(e) => update("isolation", e.target.value)}
                        >
                          <option value="workspace">
                            Workspace (non-code tasks)
                          </option>
                          <option value="docker">Hardened Docker</option>
                        </select>
                      </label>
                      <label className="field">
                        <span>Allowed tools (comma separated)</span>
                        <Input
                          value={config.tools.join(", ")}
                          onChange={(e) =>
                            update(
                              "tools",
                              e.target.value
                                .split(",")
                                .map((t) => t.trim())
                                .filter(Boolean),
                            )
                          }
                        />
                      </label>
                    </div>
                    <label className="check-row">
                      <input
                        type="checkbox"
                        checked={config.network}
                        onChange={(e) => update("network", e.target.checked)}
                      />
                      <span>
                        Request network access (runtime policy may reject)
                      </span>
                    </label>
                    <label className="field">
                      <span>Advanced experiment overrides (JSON)</span>
                      <textarea
                        rows={3}
                        value={advanced}
                        onChange={(e) => {
                          setAdvanced(e.target.value);
                          setValidation(null);
                        }}
                        placeholder={
                          '{"systems": [{"model_id": "registered-id", "parameters": {"temperature": 0}}]}'
                        }
                      />
                      <small>
                        Supports complete schema configuration, including matrix
                        systems and per-system parameters.
                      </small>
                    </label>
                  </details>
                </div>
                <div className="form-section">
                  {localError ? (
                    <p role="alert" className="notice error">
                      {localError}
                    </p>
                  ) : null}
                  <ErrorState error={validate.error || launch.error} />
                  {validation ? (
                    <div className="mb-4">
                      <div
                        className={`notice ${validation.compatible ? "info" : "error"}`}
                        role="status"
                      >
                        <div>
                          <strong>
                            {validation.compatible
                              ? "Ready to launch"
                              : "Resolve these issues before launching"}
                          </strong>
                          {validation.reasons.map((reason, i) => (
                            <p key={i}>{reason}</p>
                          ))}
                          {validation.warnings.map((warning, i) => (
                            <p key={i}>{warning}</p>
                          ))}
                        </div>
                      </div>
                      <details className="details-disclosure">
                        <summary>Technical validation evidence</summary>
                        <JsonView value={validation} />
                      </details>
                    </div>
                  ) : null}
                  <p className="registration-note">
                    {validation?.compatible
                      ? "Compatibility passed. Launch to queue the experiment and follow its results."
                      : "Validate compatibility first. This checks your systems and settings without launching a job."}
                  </p>
                  <div className="form-actions">
                    <Button
                      variant="outline"
                      type="submit"
                      disabled={validate.isPending || launch.isPending}
                    >
                      <ShieldCheck size={14} />
                      {validate.isPending
                        ? "Validating…"
                        : "Validate compatibility"}
                    </Button>
                    <Button
                      type="button"
                      disabled={!validation?.compatible || launch.isPending}
                      onClick={() => act(true)}
                    >
                      <Play size={14} />
                      {launch.isPending
                        ? "Queueing experiment…"
                        : "Launch experiment"}
                    </Button>
                  </div>
                </div>
              </form>
            </Panel>
          </div>
          <div className="stack">
            <Panel title="Execution plan">
              <dl className="summary-list">
                <dt>Systems</dt>
                <dd>{config.systems.length}</dd>
                <dt>Trials / system</dt>
                <dd>{config.trials}</dd>
                <dt>Planned runs</dt>
                <dd>{config.systems.length * config.trials}</dd>
                <dt>Tasks / run</dt>
                <dd>
                  {config.task_ids.length || "Suite defaults (8 text tasks)"}
                </dd>
                <dt>Budget</dt>
                <dd>{config.budget_seconds} s</dd>
                <dt>Verifier</dt>
                <dd>Independent / strict</dd>
                <dt>Resource estimate</dt>
                <dd>Unavailable</dd>
              </dl>
            </Panel>
            <Panel title="Validation before execution">
              <div className="panel-body muted text-xs leading-6">
                <FlaskConical size={22} className="mb-3" />
                Compatibility checks confirm capabilities, environment
                availability and budget observability. No job is launched until
                the configuration passes validation. Actual speed and cost
                depend on the configured provider.
              </div>
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}
