"use client";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Terminal } from "lucide-react";
import { useApi } from "@/lib/api";
import type { Overview as OverviewData } from "@/lib/types";
import {
  Demo,
  Empty,
  ErrorState,
  ExperimentTable,
  Loading,
  MetricStrip,
  PageTitle,
  Panel,
} from "./common";

function FirstExperiment({ data }: { data: OverviewData }) {
  const hasModels = data.models.length > 0;
  const hasAgents = data.agents.length > 0;
  return (
    <section className="first-experiment" aria-labelledby="setup-title">
      <div className="setup-workflow">
        <h2 id="setup-title">Set up your first experiment</h2>
        <p className="setup-intro">
          Start with a model endpoint. Add an agent to compare execution
          harnesses, then choose the tasks and conditions you want to test.
        </p>
        <ol className="setup-steps">
          <li>
            <span className="step-number" aria-hidden="true">
              1
            </span>
            <div>
              <h3>Connect a model</h3>
              <p>Register an endpoint and probe its compatibility.</p>
              {hasModels ? (
                <small>{data.models.length} registered</small>
              ) : null}
            </div>
            <Link href="/models" className="setup-link">
              {hasModels ? "Manage models" : "Register model"}{" "}
              <ArrowRight size={16} />
            </Link>
          </li>
          <li>
            <span className="step-number" aria-hidden="true">
              2
            </span>
            <div>
              <h3>
                Pair an agent <span className="optional">Optional</span>
              </h3>
              <p>Import an agent from the Hub, or register your own harness.</p>
              {hasAgents ? (
                <small>{data.agents.length} registered</small>
              ) : null}
            </div>
            <Link href={hasAgents ? "/agents" : "/hub"} className="setup-link">
              {hasAgents ? "Manage agents" : "Explore Agent Hub"}{" "}
              <ArrowRight size={16} />
            </Link>
          </li>
          <li>
            <span className="step-number" aria-hidden="true">
              3
            </span>
            <div>
              <h3>Run a benchmark</h3>
              <p>Set tasks, trials and budget. Validate before you launch.</p>
            </div>
            <Link href="/experiments/new" className="setup-link">
              Build experiment <ArrowRight size={16} />
            </Link>
          </li>
        </ol>
      </div>
      <aside className="terminal-handoff" aria-labelledby="terminal-title">
        <Terminal size={21} strokeWidth={1.5} aria-hidden="true" />
        <h2 id="terminal-title">Work from your terminal</h2>
        <p>
          Browse configurations, launch runs and inspect results in the same
          local workspace.
        </p>
        <pre tabIndex={0} aria-label="Launch the Bench Agents terminal">
          <code>uv run bench-agents terminal</code>
        </pre>
        <Link href="/docs#terminal" className="subtle-link">
          Terminal setup <ArrowUpRight size={14} />
        </Link>
      </aside>
    </section>
  );
}

export function Overview() {
  const query = useApi<OverviewData>("/overview", true);
  const data = query.data;
  const running =
    data?.experiments.filter((e) => ["running", "queued"].includes(e.status))
      .length ?? 0;
  return (
    <>
      <PageTitle
        title="Overview"
        description="Configure systems, run benchmarks, and inspect execution evidence."
        action={
          <Link href="/docs" className="subtle-link">
            First-run guide <ArrowUpRight size={14} />
          </Link>
        }
      />
      <ErrorState error={query.error} retry={() => query.refetch()} />
      {query.isPending ? (
        <Loading />
      ) : data ? (
        <>
          <div className="workspace-summary" aria-label="Workspace inventory">
            <div>
              <Link href="/models">
                <strong>{data.models.length}</strong> models
              </Link>
              <Link href="/agents">
                <strong>{data.agents.length}</strong> agents
              </Link>
              <Link href="/experiments">
                <strong>{data.experiments.length}</strong> experiments
              </Link>
            </div>
            <span
              className={
                running ? "activity-state is-active" : "activity-state"
              }
            >
              <span aria-hidden="true" />
              {running ? `${running} active jobs` : "No active jobs"}
            </span>
          </div>
          {data.experiments.length ? (
            <MetricStrip metrics={data.metrics} />
          ) : (
            <FirstExperiment data={data} />
          )}
          {data.experiments.some((e) => e.demo) ? <Demo /> : null}
          <Panel
            title="Experiment activity"
            detail="Job status and independently verified task outcomes are recorded separately."
            action={
              <Link href="/experiments">
                View experiments <ArrowUpRight className="inline" size={13} />
              </Link>
            }
            className="activity-panel"
          >
            {data.experiments.length ? (
              <ExperimentTable experiments={data.experiments.slice(0, 8)} />
            ) : (
              <Empty
                title="No experiments yet"
                description="Your experiments will appear here with their status, results and execution traces. Create one after registering your systems."
              />
            )}
          </Panel>
          {data.experiments.length ? (
            <Panel
              title="Recent verification failures"
              detail="Failed tasks remain part of the evidence."
              className="section-gap"
            >
              {data.recent_failures.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Task</th>
                        <th>Failure evidence</th>
                        <th>Inspect</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_failures.slice(0, 5).map((f, i) => (
                        <tr key={`${f.task_id}-${i}`}>
                          <td>{f.task_name || f.task_id}</td>
                          <td>
                            {f.verification?.reason ||
                              f.error ||
                              f.failure_category ||
                              "Verification failed"}
                          </td>
                          <td>
                            {f.run_id ? (
                              <Link
                                href={`/replay?run=${f.run_id}`}
                                className="subtle-link"
                              >
                                Trace <ArrowUpRight size={12} />
                              </Link>
                            ) : (
                              "See experiment trace"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty
                  title="No failures recorded"
                  description="Failed tasks appear here with their independent verification evidence."
                />
              )}
            </Panel>
          ) : null}
        </>
      ) : null}
    </>
  );
}
