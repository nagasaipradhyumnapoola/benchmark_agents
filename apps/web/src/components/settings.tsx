"use client";
import { useState } from "react";
import Link from "next/link";
import { RefreshCw, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAction, useApi } from "@/lib/api";
import type { ExperimentConfig, Json } from "@/lib/types";
import { ErrorState, JsonView, Loading, PageTitle, Panel } from "./common";
export function Settings() {
  const settings = useApi<Json>("/settings");
  const diagnostics = useApi<Json>("/diagnostics");
  const models = useApi<Json[]>("/models");
  const agents = useApi<Json[]>("/agents");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const imported = useAction<ExperimentConfig>("/import");
  function validate() {
    try {
      const config = JSON.parse(text);
      setError(null);
      imported.mutate(config);
    } catch {
      setError("Paste a valid experiment configuration JSON object.");
    }
  }
  function download() {
    if (!imported.data) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(imported.data, null, 2)], {
        type: "application/json",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "bench-agents-imported-config.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      <PageTitle
        title="Integrations & settings"
        description="Inspect the local runtime, storage, endpoint inventory and execution policy."
        action={
          <Button
            variant="outline"
            disabled={diagnostics.isFetching}
            onClick={() => diagnostics.refetch()}
          >
            <RefreshCw size={14} />
            Run diagnostics
          </Button>
        }
      />
      <ErrorState
        error={settings.error || diagnostics.error}
        retry={() => {
          settings.refetch();
          diagnostics.refetch();
        }}
      />
      {settings.isPending ? (
        <Loading />
      ) : (
        <div className="two-col">
          <div className="stack">
            <Panel
              title="Local workspace settings"
              detail="Read-only server configuration · change environment and restart"
            >
              <JsonView value={settings.data} />
            </Panel>
            <Panel
              title="Runtime diagnostics"
              detail="Actual detection; installed does not imply exercised"
            >
              <JsonView
                value={
                  diagnostics.data ?? { status: "Checking local runtime…" }
                }
              />
            </Panel>
            <Panel title="Credential and execution policy">
              <div className="prose">
                <p>
                  Set provider secrets in the backend environment and reference
                  their names when registering a model. Inline credential values
                  are rejected. Existing configuration identities are immutable
                  once used by a run.
                </p>
                <p>
                  CLI agents require{" "}
                  <code>BENCH_AGENTS_ALLOW_HOST_PROCESS=1</code> on the server
                  and explicit experiment consent. Code verification requires
                  the hardened Linux Docker sandbox. A missing daemon produces a
                  clear validation failure.
                </p>
                <Link href="/docs#troubleshooting">
                  Troubleshooting and environment configuration →
                </Link>
              </div>
            </Panel>
          </div>
          <div className="stack">
            <Panel title="Registered endpoints and executables">
              <div className="panel-body">
                <div className="status-line justify-between mb-4">
                  <Link className="subtle-link" href="/models">
                    {models.data?.length ?? "…"} model configurations →
                  </Link>
                  <Link className="subtle-link" href="/agents">
                    {agents.data?.length ?? "…"} agent configurations →
                  </Link>
                </div>
                <p className="muted text-xs leading-6">
                  Probe each registration from its explorer. Provider
                  availability and credentials are verified by the adapter, not
                  inferred from a configuration record.
                </p>
              </div>
            </Panel>
            <Panel
              title="Import experiment configuration"
              detail="Schema validation only · importing never launches a job"
            >
              <div className="panel-body stack">
                <label className="field">
                  <span>Experiment JSON</span>
                  <textarea
                    rows={12}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder='{"name":"Imported baseline","systems":[{"model_id":"registered-id"}]}'
                  />
                </label>
                {error ? (
                  <p role="alert" className="notice error">
                    {error}
                  </p>
                ) : null}
                <ErrorState error={imported.error} />
                <Button
                  onClick={validate}
                  disabled={!text || imported.isPending}
                >
                  {imported.isPending ? "Validating…" : "Validate import"}
                </Button>
                {imported.data ? (
                  <>
                    <p className="notice info">
                      Configuration is schema-valid. Validate adapter
                      compatibility in the builder before launching.
                    </p>
                    <JsonView value={imported.data} />
                    <Button variant="outline" onClick={download}>
                      <Download size={14} />
                      Download validated configuration
                    </Button>
                  </>
                ) : null}
              </div>
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}
