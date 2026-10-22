"use client";
import { useState } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/lib/api";
import type { Benchmark } from "@/lib/types";
import { Empty, ErrorState, Loading, PageTitle, Panel } from "./common";
export function Benchmarks() {
  const query = useApi<Benchmark[]>("/benchmarks");
  const [search, setSearch] = useState("");
  const [id, setId] = useState("starter-v1");
  const detail = useApi<Benchmark>(`/benchmarks/${id}`, false, !!id);
  const rows =
    query.data?.filter((b) =>
      `${b.name} ${b.description} ${b.categories?.join(" ")}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) ?? [];
  return (
    <>
      <PageTitle
        title="Benchmark library"
        description="Public tasks, versioned conditions and independent verification methods."
      />
      <div className="toolbar">
        <Input
          aria-label="Search benchmarks"
          placeholder="Search suites or categories…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <ErrorState error={query.error} retry={() => query.refetch()} />
      {query.isPending ? (
        <Loading />
      ) : (
        <div className="stack">
          <Panel
            title="Available suites"
            detail="Only installed and validated catalogs are runnable"
          >
            {rows.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Suite</th>
                      <th>Version</th>
                      <th>Tasks</th>
                      <th>Requirements</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((b) => (
                      <tr key={b.id}>
                        <td>
                          <button
                            className="table-primary"
                            onClick={() => setId(b.id)}
                          >
                            {b.name}
                          </button>
                          <small>{b.description}</small>
                        </td>
                        <td className="mono">{b.version}</td>
                        <td>
                          {b.task_count ?? b.tasks?.length ?? "See catalog"}
                        </td>
                        <td>
                          {b.requirements?.join(", ") ||
                            "See task requirements"}
                        </td>
                        <td>
                          <Button asChild variant="outline" size="sm">
                            <Link href={`/experiments/new?benchmark=${b.id}`}>
                              Build experiment
                            </Link>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty
                title="No matching suites"
                description="Clear the search to view installed benchmarks."
                demo={false}
              />
            )}
          </Panel>
          <ErrorState error={detail.error} />
          {detail.data ? (
            <Panel
              title={detail.data.name}
              detail="Task-level verification · expected answers stay outside provider prompts"
            >
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Task</th>
                      <th>Category</th>
                      <th>Verifier</th>
                      <th>Environment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.data.tasks?.map((t) => (
                      <tr key={t.id}>
                        <td>
                          {t.name}
                          <small>{t.description || t.prompt || t.id}</small>
                        </td>
                        <td>
                          <Badge variant="outline">{t.category}</Badge>
                        </td>
                        <td className="mono">{t.verifier}</td>
                        <td>
                          {t.requires_execution
                            ? "Docker required"
                            : "Workspace"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          ) : null}
          <Panel title="External benchmark setup">
            <div className="prose">
              <p>
                External evaluation packages keep their upstream scorers and
                their own versioned results. They are never silently mixed with
                the native starter suite. Check the integrations diagnostics
                before installing optional packages.
              </p>
              <p>
                <Link href="/settings">Inspect runtime availability</Link> or{" "}
                <Link href="/docs#external">read the integration workflow</Link>
                . Uninstalled integrations are unavailable until their package,
                dataset and scorer are explicitly configured.
              </p>
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}
