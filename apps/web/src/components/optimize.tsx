"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAction, useApi } from "@/lib/api";
import type { Experiment, ExperimentConfig, Compatibility } from "@/lib/types";
import {
  Demo,
  Empty,
  ErrorState,
  JsonView,
  PageTitle,
  Panel,
  Status,
} from "./common";
export function Optimize() {
  const router = useRouter();
  const params = useSearchParams();
  const experiments = useApi<Experiment[]>("/experiments");
  const [baseline, setBaseline] = useState(params.get("baseline") ?? "");
  const [name, setName] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [overrides, setOverrides] = useState('{"max_tokens": 1024}');
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState<Compatibility | null>(null);
  const source = experiments.data?.find((e) => e.id === baseline);
  const validate = useAction<Compatibility>(
    "/experiments/validate",
    setChecked,
  );
  const clone = useAction<Experiment>(`/experiments/${baseline}/clone`, (e) =>
    router.push(`/experiments?id=${e.id}`),
  );
  function config() {
    const changes = JSON.parse(overrides);
    if (!changes || Array.isArray(changes) || typeof changes !== "object")
      throw new Error("Overrides must be a JSON object.");
    return {
      ...changes,
      name: name || `${source?.name} · ablation`,
      description: hypothesis,
      mode: "ablation",
      baseline_id: baseline,
    };
  }
  function act(launch: boolean) {
    try {
      if (!source) throw new Error("Select a baseline experiment.");
      const changes = config();
      setError(null);
      if (launch) clone.mutate(changes);
      else
        validate.mutate({ ...source.config, ...changes } as ExperimentConfig);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid configuration");
    }
  }
  return (
    <>
      <PageTitle
        title="Optimization laboratory"
        description="Change one condition, retain the baseline, and inspect evidence for improvement or regression."
      />
      <ErrorState error={experiments.error} />
      <div className="split">
        <Panel
          title="Controlled ablation"
          detail="Cloning creates a new immutable experiment"
        >
          <div className="form-section stack">
            <label className="field">
              <span>Baseline experiment</span>
              <select
                value={baseline}
                onChange={(e) => {
                  setBaseline(e.target.value);
                  setChecked(null);
                }}
              >
                <option value="">Select a persisted baseline</option>
                {experiments.data?.map((e) => (
                  <option value={e.id} key={e.id}>
                    {e.name} · {e.status}
                  </option>
                ))}
              </select>
            </label>
            {source?.demo ? <Demo /> : null}
            <label className="field">
              <span>Candidate name</span>
              <Input
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setChecked(null);
                }}
                placeholder="Baseline · lower token budget"
              />
            </label>
            <label className="field">
              <span>Hypothesis</span>
              <textarea
                rows={3}
                value={hypothesis}
                onChange={(e) => {
                  setHypothesis(e.target.value);
                  setChecked(null);
                }}
                placeholder="Reducing the token limit will preserve verified success while reducing calculated cost."
              />
            </label>
            <label className="field">
              <span>Configuration changes (JSON)</span>
              <textarea
                rows={7}
                value={overrides}
                onChange={(e) => {
                  setOverrides(e.target.value);
                  setChecked(null);
                }}
              />
              <small>
                Overrides merge at the experiment level. To change system
                parameters, provide the complete systems array. Conditions
                changes remain visible in comparison.
              </small>
            </label>
            {error ? (
              <p role="alert" className="notice error">
                {error}
              </p>
            ) : null}
            <ErrorState error={validate.error || clone.error} />
            {checked ? (
              <>
                <Status value={checked.compatible ? "completed" : "failed"} />
                <JsonView value={checked} />
              </>
            ) : null}
            <div className="form-actions">
              <Button
                variant="outline"
                disabled={!baseline || validate.isPending}
                onClick={() => act(false)}
              >
                Validate changes
              </Button>
              <Button
                disabled={!checked?.compatible || clone.isPending}
                onClick={() => act(true)}
              >
                {clone.isPending ? "Launching…" : "Clone and launch ablation"}
              </Button>
            </div>
          </div>
        </Panel>
        <div className="stack">
          <Panel title="Baseline configuration">
            {source ? (
              <JsonView value={source.config} />
            ) : (
              <Empty
                title="Choose a baseline"
                description="Select an experiment to inspect its fixed conditions."
                demo={false}
              />
            )}
          </Panel>
          <Panel title="Draw conclusions from evidence">
            <div className="panel-body muted text-xs leading-6">
              An ablation changes the condition fingerprint. Comparison
              explicitly marks the mismatch; it does not pretend a
              changed-budget experiment is a controlled head-to-head. Inspect
              task successes, failures, latency and available usage before
              concluding.
              <Link className="subtle-link block mt-4" href="/compare">
                Open comparison studio →
              </Link>
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}
