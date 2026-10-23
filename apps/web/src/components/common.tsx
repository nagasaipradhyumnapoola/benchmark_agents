"use client";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Loader2,
  Play,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAction, format, percent } from "@/lib/api";
import type { Experiment, Metrics, Run } from "@/lib/types";
import { useRouter } from "next/navigation";
export function PageTitle({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Panel({
  title,
  detail,
  children,
  action,
  className = "",
}: {
  title: string;
  detail?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {detail ? <p>{detail}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Status({ value }: { value: string }) {
  return (
    <Badge variant="outline" className={`status status-${value}`}>
      <span className="status-dot" />
      {value}
    </Badge>
  );
}
export function Demo({ compact = false }: { compact?: boolean }) {
  return compact ? (
    <Badge className="demo-badge" variant="outline">
      DEMO
    </Badge>
  ) : (
    <div className="notice demo-notice">
      <AlertTriangle size={17} />
      <span>
        <strong>Demonstration evidence.</strong> Deterministic adapters test the
        pipeline. These results do not measure model intelligence.
      </span>
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error | null;
  retry?: () => void;
}) {
  return error ? (
    <div role="alert" className="notice error">
      <AlertTriangle size={18} />
      <div>
        <strong>Unable to complete this request</strong>
        <p>{error.message}</p>
        {retry ? (
          <Button variant="outline" onClick={retry}>
            <RefreshCw size={14} />
            Try again
          </Button>
        ) : null}
      </div>
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div
      role="status"
      aria-label="Loading workspace data"
      className="loading-block"
    >
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-48 w-full" />
      <span className="muted">
        <Loader2 className="inline animate-spin" size={14} /> Loading persisted
        evidence…
      </span>
    </div>
  );
}
export function DemoButton() {
  const router = useRouter();
  const action = useAction<Experiment>("/demo", (data) =>
    router.push(`/experiments?id=${data.id}`),
  );
  return (
    <>
      <Button disabled={action.isPending} onClick={() => action.mutate({})}>
        <Play size={14} />
        {action.isPending
          ? "Queueing demonstration…"
          : "Run offline demonstration"}
      </Button>
      <ErrorState error={action.error} />
    </>
  );
}
export function Empty({
  title = "No evidence yet",
  description = "Run an experiment to create durable, independently verified evidence.",
  demo = false,
  action,
}: {
  title?: string;
  description?: string;
  demo?: boolean;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
      {demo ? (
        <Link href="/docs" className="subtle-link">
          Read the setup guide <ArrowRight size={14} />
        </Link>
      ) : null}
    </div>
  );
}
export function JsonView({ value }: { value: unknown }) {
  return (
    <pre
      className="json-view"
      tabIndex={0}
      role="region"
      aria-label="JSON evidence"
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
export function MetricStrip({ metrics }: { metrics: Metrics }) {
  const items = [
    ["Verified success", percent(metrics.success_rate)],
    [
      "Tasks verified",
      metrics.total === undefined
        ? "Unavailable"
        : `${metrics.passed ?? 0} / ${metrics.total}`,
    ],
    [
      "Median latency",
      metrics.median_latency_seconds == null
        ? "Unavailable"
        : `${format(metrics.median_latency_seconds)} s`,
    ],
    [
      "Calculated cost",
      metrics.cost_usd == null
        ? "Unavailable"
        : `$${format(metrics.cost_usd, 4)}`,
    ],
  ];
  return (
    <div className="metric-strip">
      {items.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}
export function ExperimentTable({
  experiments,
}: {
  experiments: Experiment[];
}) {
  return experiments.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Experiment</th>
            <th>Mode</th>
            <th>Status</th>
            <th>Created</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {experiments.map((e) => (
            <tr key={e.id}>
              <td>
                <Link
                  href={`/experiments?id=${e.id}`}
                  className="table-primary"
                >
                  {e.name}
                </Link>
                <small className="mono">
                  {e.id.slice(0, 8)} {e.demo ? <Demo compact /> : null}
                </small>
              </td>
              <td>{e.mode}</td>
              <td>
                <Status value={e.status} />
              </td>
              <td>{new Date(e.created_at).toLocaleString()}</td>
              <td>
                <Link
                  aria-label={`Inspect ${e.name}`}
                  href={`/experiments?id=${e.id}`}
                >
                  <ArrowRight size={16} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty />
  );
}
export function RunPicker({
  runs,
  value,
  onChange,
  label = "Run",
}: {
  runs: Run[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Select a persisted run</option>
        {runs.map((r) => (
          <option value={r.id} key={r.id}>
            {r.system_name} · trial {r.trial} · {r.id.slice(0, 8)} · {r.status}
          </option>
        ))}
      </select>
    </label>
  );
}
