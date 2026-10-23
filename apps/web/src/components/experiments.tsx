"use client";
import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Square, ArrowUpRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApi, useAction, active, percent, format } from "@/lib/api";
import type { Experiment, Run } from "@/lib/types";
import {
  Demo,
  Empty,
  ErrorState,
  ExperimentTable,
  JsonView,
  Loading,
  PageTitle,
  Panel,
  Status,
} from "./common";
function LiveRun({ run }: { run: Run }) {
  const detail = useApi<Run>(`/runs/${run.id}`, active(run.status));
  return (
    <div className="panel-body border-b border-border">
      <div className="status-line justify-between">
        <div>
          <Link href={`/replay?run=${run.id}`} className="table-primary">
            {run.system_name}
          </Link>
          <p className="muted text-xs mt-1">
            Trial {run.trial} · {run.id.slice(0, 8)}
          </p>
        </div>
        <Status value={run.status} />
      </div>
      {run.metrics?.total != null ? (
        <p className="registration-note mt-3">
          <strong>
            {run.metrics.passed ?? 0} / {run.metrics.total} tasks passed
            verification.
          </strong>{" "}
          {run.status === "completed"
            ? "Run finished; completion alone does not mean every task passed."
            : "Outcomes update as tasks finish."}
        </p>
      ) : null}
      <div className="metric-strip !my-4 !py-3">
        <div>
          <span>Tasks recorded</span>
          <strong className="!text-lg">
            {detail.data?.results?.length ?? run.metrics?.total ?? 0}
          </strong>
        </div>
        <div>
          <span>Verified success</span>
          <strong className="!text-lg">
            {percent(run.metrics?.success_rate)}
          </strong>
        </div>
        <div>
          <span>Elapsed task time</span>
          <strong className="!text-lg">
            {format(run.metrics?.duration_seconds)} s
          </strong>
        </div>
        <div>
          <span>Resource usage</span>
          <strong className="!text-sm">Unavailable</strong>
        </div>
      </div>
      {run.error ? <p className="notice error">{run.error}</p> : null}
      <ErrorState error={detail.error} />
      {detail.data?.events?.length ? (
        <div className="muted text-xs mono">
          Latest: {detail.data.events.at(-1)?.type} ·{" "}
          {detail.data.events.at(-1)?.message}
        </div>
      ) : (
        <p className="muted text-xs">Waiting for the next persisted event.</p>
      )}
      <Link href={`/replay?run=${run.id}`} className="subtle-link mt-3">
        Inspect execution trace <ArrowUpRight size={12} />
      </Link>
    </div>
  );
}
function ExperimentDetail({ id }: { id: string }) {
  const query = useApi<Experiment>(`/experiments/${id}`, true);
  const cancel = useAction(`/experiments/${id}/cancel`);
  const data = query.data;
  return (
    <>
      <ErrorState error={query.error} retry={() => query.refetch()} />
      {query.isPending ? (
        <Loading />
      ) : data ? (
        <>
          <div className="status-line mb-5">
            <h2 className="!text-xl">{data.name}</h2>
            <Status value={data.status} />
            {active(data.status) ? (
              <Button
                variant="destructive"
                size="sm"
                disabled={cancel.isPending}
                onClick={() => cancel.mutate({})}
              >
                <Square size={12} />
                Cancel experiment
              </Button>
            ) : null}
            <Link
              className="subtle-link"
              href={`/optimize?baseline=${data.id}`}
            >
              Clone as ablation <ArrowUpRight size={12} />
            </Link>
          </div>
          <ErrorState error={cancel.error} />
          {data.demo ? <Demo /> : null}
          <div className="split">
            <Panel
              title="Live run monitor"
              detail={
                active(data.status)
                  ? "Polling durable execution records every 2 seconds"
                  : "Execution stopped · recorded outcomes below"
              }
            >
              {data.runs?.length ? (
                data.runs.map((r) => <LiveRun key={r.id} run={r} />)
              ) : (
                <Empty
                  title={
                    active(data.status)
                      ? "Queued for execution"
                      : "No runs recorded"
                  }
                  description={
                    active(data.status)
                      ? "The worker will create runs when it claims this experiment."
                      : "Execution stopped before any run was recorded. Review the configuration and service diagnostics before trying again."
                  }
                  demo={false}
                />
              )}
            </Panel>
            <div className="stack">
              <Panel title="Reproducibility configuration">
                <details className="details-disclosure">
                  <summary>View immutable configuration</summary>
                  <JsonView value={data.config} />
                </details>
              </Panel>
              <Panel title="Export evidence">
                <div className="panel-body flex gap-3 flex-wrap">
                  {["json", "csv", "html", "zip"].map((f) => (
                    <Button asChild variant="outline" size="sm" key={f}>
                      <a
                        href={`/api/experiments/${data.id}/report?format=${f}`}
                      >
                        {f.toUpperCase()}
                      </a>
                    </Button>
                  ))}
                </div>
              </Panel>
            </div>
          </div>
        </>
      ) : null}
    </>
  );
}
export function Experiments() {
  const params = useSearchParams();
  const id = params.get("id");
  const query = useApi<Experiment[]>("/experiments", true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const rows =
    query.data?.filter(
      (e) =>
        e.name.toLowerCase().includes(search.toLowerCase()) &&
        (status === "all" || e.status === status),
    ) ?? [];
  return (
    <>
      <PageTitle
        title="Live experiments"
        description="Follow queued and running jobs, inspect failures, and revisit durable experiment records."
        action={
          <Button variant="outline" onClick={() => query.refetch()}>
            <RefreshCw size={14} />
            Refresh records
          </Button>
        }
      />
      {id ? (
        <>
          <div className="mb-5">
            <Link href="/experiments" className="subtle-link">
              ← All experiments
            </Link>
          </div>
          <ExperimentDetail key={id} id={id} />
        </>
      ) : (
        <>
          <div className="toolbar filters">
            <Input
              aria-label="Search experiments"
              placeholder="Search experiments…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              aria-label="Filter experiment status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {[
                "all",
                "queued",
                "running",
                "completed",
                "failed",
                "cancelled",
                "interrupted",
              ].map((s) => (
                <option value={s} key={s}>
                  {s === "all" ? "All statuses" : s}
                </option>
              ))}
            </select>
          </div>
          <ErrorState error={query.error} retry={() => query.refetch()} />
          {query.isPending ? (
            <Loading />
          ) : (
            <Panel
              title="Experiment records"
              detail={`${rows.length} matching records · refresh survives browser restart`}
            >
              <ExperimentTable experiments={rows} />
            </Panel>
          )}
        </>
      )}
    </>
  );
}
