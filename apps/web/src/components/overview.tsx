"use client";
import Link from "next/link";
import { ArrowUpRight, Boxes, Cpu, ShieldCheck } from "lucide-react";
import { useApi } from "@/lib/api";
import type { Overview as OverviewData } from "@/lib/types";
import {
  Demo,
  DemoButton,
  Empty,
  ErrorState,
  ExperimentTable,
  Loading,
  MetricStrip,
  PageTitle,
  Panel,
} from "./common";
export function Overview() {
  const query = useApi<OverviewData>("/overview", true);
  return (
    <>
      <PageTitle
        title="Overview"
        description="A shared workspace for reproducible experiments and verified execution evidence."
        action={<DemoButton />}
      />
      <ErrorState error={query.error} retry={() => query.refetch()} />
      {query.isPending ? (
        <Loading />
      ) : query.data ? (
        <>
          <MetricStrip metrics={query.data.metrics} />
          {query.data.experiments.some((e) => e.demo) ? <Demo /> : null}
          <div className="split">
            <div className="stack">
              <Panel
                title="Experiment activity"
                detail="Persisted jobs · orchestration status is separate from task success"
                action={
                  <Link href="/experiments">
                    View all <ArrowUpRight className="inline" size={12} />
                  </Link>
                }
              >
                <ExperimentTable
                  experiments={query.data.experiments.slice(0, 8)}
                />
              </Panel>
              <Panel
                title="Recent verification failures"
                detail="Unsuccessful outputs remain part of the evidence"
              >
                {query.data.recent_failures.length ? (
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
                        {query.data.recent_failures.slice(0, 5).map((f, i) => (
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
                    demo={false}
                  />
                )}
              </Panel>
            </div>
            <div className="stack">
              <Panel
                title="System inventory"
                action={<Link href="/models">Manage</Link>}
              >
                <Link className="inventory-item" href="/models">
                  <div>
                    <strong>
                      <Cpu size={15} className="inline mr-2" />
                      Models
                    </strong>
                    <small>Registered model configurations</small>
                  </div>
                  <span className="mono">{query.data.models.length}</span>
                </Link>
                <Link className="inventory-item" href="/agents">
                  <div>
                    <strong>
                      <Boxes size={15} className="inline mr-2" />
                      Agents
                    </strong>
                    <small>Versioned execution harnesses</small>
                  </div>
                  <span className="mono">{query.data.agents.length}</span>
                </Link>
                <Link className="inventory-item" href="/benchmarks">
                  <div>
                    <strong>
                      <ShieldCheck size={15} className="inline mr-2" />
                      Starter suite
                    </strong>
                    <small>Independent verifiers · public fixtures</small>
                  </div>
                  <ArrowUpRight size={14} />
                </Link>
              </Panel>
              <Panel title="Start with evidence">
                <div className="panel-body">
                  <p className="muted text-xs leading-6">
                    Register a real endpoint or launch the zero-credential
                    demonstration. Compare identical conditions, then inspect
                    the traces behind each outcome.
                  </p>
                  <Link href="/docs" className="subtle-link mt-4">
                    Read the first-run guide <ArrowUpRight size={12} />
                  </Link>
                </div>
              </Panel>
            </div>
          </div>
        </>
      ) : null}
    </>
  );
}
