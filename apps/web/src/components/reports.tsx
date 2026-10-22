"use client";
import { useState } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useApi } from "@/lib/api";
import type { Experiment } from "@/lib/types";
import {
  Demo,
  Empty,
  ErrorState,
  Loading,
  PageTitle,
  Panel,
  Status,
} from "./common";
export function Reports() {
  const query = useApi<Experiment[]>("/experiments");
  const [search, setSearch] = useState("");
  const [provenance, setProvenance] = useState("all");
  const rows =
    query.data?.filter(
      (e) =>
        e.name.toLowerCase().includes(search.toLowerCase()) &&
        (provenance === "all" || (provenance === "demo") === e.demo),
    ) ?? [];
  return (
    <>
      <PageTitle
        title="Reports"
        description="Portable evidence packages with results, failures, traces and reproducibility manifests."
      />
      <div className="toolbar filters">
        <Input
          aria-label="Search reports"
          placeholder="Find an experiment report…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Filter report provenance"
          value={provenance}
          onChange={(e) => setProvenance(e.target.value)}
        >
          <option value="all">All provenance</option>
          <option value="real">Real configured systems</option>
          <option value="demo">Demonstration only</option>
        </select>
      </div>
      <ErrorState error={query.error} retry={() => query.refetch()} />
      {query.isPending ? (
        <Loading />
      ) : (
        <Panel
          title="Experiment reports"
          detail={`${rows.length} records · exports generated from persisted backend evidence`}
        >
          {rows.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Experiment</th>
                    <th>State</th>
                    <th>Created</th>
                    <th>Download report</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((e) => (
                    <tr key={e.id}>
                      <td>
                        <Link
                          className="table-primary"
                          href={`/experiments?id=${e.id}`}
                        >
                          {e.name}
                        </Link>
                        <small>
                          {e.mode} {e.demo ? <Demo compact /> : null}
                        </small>
                      </td>
                      <td>
                        <Status value={e.status} />
                      </td>
                      <td>{new Date(e.created_at).toLocaleDateString()}</td>
                      <td>
                        <div className="flex gap-2">
                          {["json", "csv", "html", "zip"].map((f) => (
                            <Button asChild key={f} size="sm" variant="outline">
                              <a
                                href={`/api/experiments/${e.id}/report?format=${f}`}
                                aria-label={`Download ${e.name} as ${f}`}
                              >
                                {f.toUpperCase()}
                              </a>
                            </Button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="No matching reports"
              description="Every persisted experiment can be exported, including failed and cancelled jobs."
              demo={!search}
            />
          )}
        </Panel>
      )}
      <div className="section-gap">
        <Panel title="Methodology and limitations">
          <div className="prose">
            <p>
              Reports distinguish orchestration completion from independently
              verified task success. They include all failures, immutable
              configuration, recorded events and demo provenance. Unobserved
              tokens, cost, hardware and energy remain unavailable.
            </p>
            <p>
              The starter fixture suite is a small public sample. Wilson
              intervals assume independent task outcomes; repeated trials and
              correlated tasks weaken that assumption. Comparisons check
              condition fingerprints and expose changes. Exports redact known
              credentials, escape HTML and neutralize spreadsheet formula
              injection.
            </p>
            <p>
              <Link href="/docs">
                Read the full workflow and interpretation guide
              </Link>
              .
            </p>
          </div>
        </Panel>
      </div>
    </>
  );
}
