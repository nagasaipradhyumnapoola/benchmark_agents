"use client";
import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { useApi, percent, format } from "@/lib/api";
import type {
  Comparison as ComparisonData,
  Metrics,
  Result,
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
  RunPicker,
  Status,
} from "./common";
type Summary = Metrics & { run_id: string; system_name: string; demo: boolean };
export function Comparison() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = params.get("runs")?.split(",") ?? [];
  const runs = useApi<Run[]>("/runs");
  const [left, setLeft] = useState(ids[0] ?? "");
  const [right, setRight] = useState(ids[1] ?? "");
  const query = useApi<ComparisonData>(
    `/compare?run_ids=${ids.join(",")}`,
    false,
    ids.length >= 2,
  );
  const summaries = (query.data?.summary ?? []) as Summary[];
  const tasks = (query.data?.task_rows ?? []) as (Result & {
    system_name: string;
  })[];
  return (
    <>
      <PageTitle
        title="Comparison studio"
        description="Compare verified outcomes under matched conditions. Uncertainty and failed tasks remain visible."
      />
      <div className="comparison-picker">
        <RunPicker
          runs={runs.data ?? []}
          value={left}
          onChange={setLeft}
          label="Baseline run"
        />
        <RunPicker
          runs={runs.data ?? []}
          value={right}
          onChange={setRight}
          label="Candidate run"
        />
        <Button
          disabled={!left || !right || left === right}
          onClick={() => router.push(`/compare?runs=${left},${right}`)}
        >
          Compare runs
        </Button>
      </div>
      <ErrorState
        error={runs.error || query.error}
        retry={() => query.refetch()}
      />
      {query.isFetching ? (
        <Loading />
      ) : query.data ? (
        <>
          {query.data.runs.some((r) => r.manifest.demo) ? <Demo /> : null}
          <div className={`notice ${query.data.comparable ? "info" : "error"}`}>
            <div>
              <strong>
                {query.data.comparable
                  ? "Matched experimental conditions"
                  : "Comparison conditions differ"}
              </strong>
              <p>
                {query.data.comparable
                  ? "These runs share a condition fingerprint. Paired task analysis is available below."
                  : query.data.reasons.join(" · ")}
              </p>
            </div>
          </div>
          <div className="two-col mb-5">
            <Panel
              title="Verified task success"
              detail="Observed outcomes · 0–100% scale"
            >
              <div className="chart-wrap">
                <ChartContainer
                  config={{
                    success: { label: "Verified success", color: "#a8bacf" },
                  }}
                  className="h-[220px] w-full"
                >
                  <BarChart
                    accessibilityLayer
                    data={summaries.map((s) => ({
                      name: s.system_name,
                      success:
                        s.success_rate == null
                          ? null
                          : Math.round(s.success_rate * 1000) / 10,
                    }))}
                    layout="vertical"
                    margin={{ left: 8, right: 24 }}
                  >
                    <CartesianGrid horizontal={false} stroke="#2b2e33" />
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      tickLine={false}
                      axisLine={false}
                      unit="%"
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={120}
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 11 }}
                    />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar
                      dataKey="success"
                      fill="var(--color-success)"
                      radius={[0, 3, 3, 0]}
                      barSize={24}
                    />
                  </BarChart>
                </ChartContainer>
              </div>
            </Panel>
            <Panel
              title="95% Wilson intervals"
              detail="Task sample uncertainty · no model-population claim"
            >
              <div className="panel-body stack">
                {summaries.map((s) => (
                  <div key={s.run_id}>
                    <div className="flex justify-between gap-3 text-xs mb-3">
                      <span>{s.system_name}</span>
                      <span className="mono muted">
                        {percent(s.confidence_low)} –{" "}
                        {percent(s.confidence_high)}
                      </span>
                    </div>
                    <div
                      className="relative h-6 border-x border-border bg-muted/30 rounded-sm"
                      role="img"
                      aria-label={`${s.system_name} Wilson interval ${percent(s.confidence_low)} to ${percent(s.confidence_high)}`}
                    >
                      {s.confidence_low != null && s.confidence_high != null ? (
                        <>
                          <div
                            className="absolute top-3 h-px bg-[#9bb2ce]"
                            style={{
                              left: `${s.confidence_low * 100}%`,
                              width: `${(s.confidence_high - s.confidence_low) * 100}%`,
                            }}
                          />
                          <div
                            className="absolute top-2 size-2 rounded-full bg-[#c9d6e7]"
                            style={{
                              left: `calc(${(s.success_rate ?? 0) * 100}% - 4px)`,
                            }}
                          />
                        </>
                      ) : null}
                    </div>
                  </div>
                ))}
                <p className="muted text-xs leading-6">
                  Wilson intervals assume independent Bernoulli tasks. A small
                  public fixture suite is exploratory evidence. Repeated trials
                  and correlated tasks limit inference.
                </p>
              </div>
            </Panel>
          </div>
          <Panel
            title="Side-by-side measurements"
            detail="Unavailable values are never imputed"
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    {summaries.map((s) => (
                      <th key={s.run_id}>{s.system_name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      ["Success rate", "success_rate", "percent"],
                      ["Passed tasks", "passed", "number"],
                      ["Failed tasks", "failed", "number"],
                      [
                        "Median latency (s)",
                        "median_latency_seconds",
                        "number",
                      ],
                      [
                        "P95 latency (s; ≥20 tasks)",
                        "p95_latency_seconds",
                        "number",
                      ],
                      ["Observed tokens", "tokens", "number"],
                      ["Calculated cost (USD)", "cost_usd", "cost"],
                      ["Cost / success (USD)", "cost_per_success_usd", "cost"],
                    ] as const
                  ).map(([label, key, type]) => (
                    <tr key={key}>
                      <td>{label}</td>
                      {summaries.map((s) => (
                        <td key={s.run_id} className="mono">
                          {type === "percent"
                            ? percent(s[key])
                            : format(s[key], type === "cost" ? 6 : 3)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          <div className="section-gap">
            <Panel
              title="Verified success by category"
              detail="Public task groups · sample sizes remain explicit"
            >
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Category</th>
                      {summaries.map((s) => (
                        <th key={s.run_id}>{s.system_name}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from(
                      new Set(
                        summaries.flatMap((s) =>
                          Object.keys(s.by_category ?? {}),
                        ),
                      ),
                    )
                      .sort()
                      .map((category) => (
                        <tr key={category}>
                          <td>{category}</td>
                          {summaries.map((s) => {
                            const metric = s.by_category?.[category];
                            return (
                              <td key={s.run_id} className="mono">
                                {metric
                                  ? `${percent(metric.success_rate)} · ${metric.passed}/${metric.total} tasks`
                                  : "Unavailable"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>
          <div className="section-gap">
            <Panel
              title="Per-task evidence"
              detail="All observed tasks, including failures"
            >
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Task</th>
                      <th>System</th>
                      <th>Verified</th>
                      <th>Latency</th>
                      <th>Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((t, i) => (
                      <tr key={`${t.task_id}-${i}`}>
                        <td>
                          {t.task_name || t.task_id}
                          <small>{t.category}</small>
                        </td>
                        <td>{t.system_name}</td>
                        <td>
                          <Status value={t.passed ? "completed" : "failed"} />
                        </td>
                        <td>{format(t.duration_seconds)} s</td>
                        <td>
                          {t.verification.reason ||
                            t.error ||
                            t.verification.verifier}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>
          <details className="details-disclosure">
            <summary>
              Advanced comparison evidence: paired analysis, conditions and
              ablations
            </summary>
            <div className="two-col section-gap">
              <Panel
                title="Paired improvement / regression"
                detail="Exploratory task analysis; no multiple-comparison correction"
              >
                <JsonView value={query.data.paired_differences} />
              </Panel>
              <Panel
                title="Conditions and Pareto analysis"
                detail="Pareto set requires known calculated cost and observed latency"
              >
                <JsonView
                  value={{
                    changes: query.data.changes,
                    pareto: query.data.pareto,
                  }}
                />
              </Panel>
            </div>
            <div className="section-gap">
              <Panel
                title="Baseline-linked ablation evidence"
                detail="Observed intervention effects; treatment differences remain explicit"
              >
                <JsonView value={query.data.ablation_analysis ?? []} />
              </Panel>
            </div>
          </details>
          <div className="mt-5 flex gap-5">
            {query.data.runs.map((r) => (
              <Link
                className="subtle-link"
                href={`/replay?run=${r.id}`}
                key={r.id}
              >
                Replay {r.system_name} →
              </Link>
            ))}
          </div>
        </>
      ) : (
        <Panel title="Select two runs">
          <Empty
            title="A comparison begins with shared conditions"
            description="Select baseline and candidate runs above. Completed experiments appear automatically."
            demo={!runs.data?.length}
          />
        </Panel>
      )}
    </>
  );
}
