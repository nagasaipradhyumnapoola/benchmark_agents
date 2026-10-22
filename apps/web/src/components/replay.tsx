"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Download, FileText } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { useApi, active, format } from "@/lib/api";
import type { Run } from "@/lib/types";
import type { Artifact } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
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
function ArtifactPreview({
  run,
  artifact,
}: {
  run: string;
  artifact: Artifact;
}) {
  const [open, setOpen] = useState(false);
  const readable =
    artifact.media_type.startsWith("text/") ||
    /json|javascript|xml/.test(artifact.media_type);
  const query = useQuery({
    queryKey: ["artifact", run, artifact.id],
    enabled: open && readable && artifact.size_bytes <= 262144,
    queryFn: async () => {
      const response = await fetch(`/api/runs/${run}/artifacts/${artifact.id}`);
      if (!response.ok)
        throw new Error("Artifact preview failed. Download the file or retry.");
      return response.text();
    },
  });
  return (
    <div className="border-b border-border py-3">
      <div className="inventory-item !px-0 !border-0">
        <div className="min-w-0">
          <strong>
            <FileText size={15} className="inline mr-2" />
            {artifact.name}
          </strong>
          <small>
            {artifact.media_type} · {artifact.size_bytes.toLocaleString()} bytes
          </small>
          <small className="mono break-all">SHA256 {artifact.sha256}</small>
        </div>
        <Button variant="outline" size="icon" asChild>
          <a
            aria-label={`Download ${artifact.name}`}
            href={`/api/runs/${run}/artifacts/${artifact.id}`}
          >
            <Download size={14} />
          </a>
        </Button>
      </div>
      {readable && artifact.size_bytes <= 262144 ? (
        <Button variant="ghost" size="sm" onClick={() => setOpen(!open)}>
          {open ? "Hide preview" : "Preview text / diff"}
        </Button>
      ) : (
        <p className="muted text-xs">
          Preview unavailable for binary files or artifacts over 256 KiB.
          Download to inspect.
        </p>
      )}
      <ErrorState error={query.error} />
      {open && query.isPending ? (
        <p role="status" className="muted text-xs">
          Loading artifact…
        </p>
      ) : null}
      {open && query.data ? (
        <pre
          className="json-view"
          tabIndex={0}
          role="region"
          aria-label={`Text preview of ${artifact.name}`}
        >
          {query.data}
        </pre>
      ) : null}
    </div>
  );
}
export function Replay() {
  const params = useSearchParams();
  const router = useRouter();
  const id = params.get("run") ?? "";
  const runs = useApi<Run[]>("/runs");
  const selected = runs.data?.find((r) => r.id === id);
  const query = useApi<Run>(
    `/runs/${id}`,
    !!selected && active(selected.status),
    !!id,
  );
  const [sequence, setSequence] = useState<number | null>(null);
  const [eventFilter, setEventFilter] = useState("all");
  const [task, setTask] = useState("");
  const [other, setOther] = useState("");
  const events =
    query.data?.events?.filter(
      (e) =>
        (eventFilter === "all" || e.type === eventFilter) &&
        (!task || e.task_id === task),
    ) ?? [];
  const event = events.find((e) => e.sequence === sequence) ?? events.at(-1);
  return (
    <>
      <PageTitle
        title="Execution replay"
        description="Follow the recorded timeline from system input to independent verification and persisted artifacts."
      />
      <div className="two-col mb-5">
        <RunPicker
          runs={runs.data ?? []}
          value={id}
          onChange={(value) => {
            setSequence(null);
            router.push(`/replay?run=${value}`);
          }}
        />
        <div className="comparison-picker !mb-0 !grid-cols-[1fr_auto]">
          <RunPicker
            label="Compare alongside"
            runs={runs.data ?? []}
            value={other}
            onChange={setOther}
          />
          <Button
            variant="outline"
            disabled={!id || !other || id === other}
            onClick={() => router.push(`/compare?runs=${id},${other}`)}
          >
            Compare
          </Button>
        </div>
      </div>
      <ErrorState
        error={runs.error || query.error}
        retry={() => query.refetch()}
      />
      {query.isFetching && !query.data ? (
        <Loading />
      ) : query.data ? (
        <>
          {query.data.manifest.demo ? <Demo /> : null}
          <div className="status-line mb-5">
            <h2 className="!text-lg">{query.data.system_name}</h2>
            <Status value={query.data.status} />
            <span className="mono muted text-xs">
              Trial {query.data.trial} · {query.data.id}
            </span>
          </div>
          <div className="toolbar filters">
            <select
              aria-label="Filter event type"
              value={eventFilter}
              onChange={(e) => setEventFilter(e.target.value)}
            >
              <option value="all">All event types</option>
              {Array.from(new Set(query.data.events?.map((e) => e.type))).map(
                (type) => (
                  <option value={type} key={type}>
                    {type}
                  </option>
                ),
              )}
            </select>
            <select
              aria-label="Filter task"
              value={task}
              onChange={(e) => setTask(e.target.value)}
            >
              <option value="">All tasks</option>
              {query.data.results?.map((r) => (
                <option value={r.task_id} key={r.task_id}>
                  {r.task_name || r.task_id}
                </option>
              ))}
            </select>
          </div>
          <div className="inspector">
            <Panel
              title="Event timeline"
              detail={`${events.length} recorded events`}
            >
              <div className="timeline">
                {events.length ? (
                  events.map((e) => (
                    <button
                      className={`event-button ${event?.sequence === e.sequence ? "active" : ""}`}
                      key={e.sequence}
                      onClick={() => setSequence(e.sequence)}
                    >
                      <span className="sequence mono">{e.sequence}</span>
                      <span>
                        {e.type}
                        <small>
                          {new Date(e.timestamp).toLocaleTimeString()} ·{" "}
                          {e.task_id ?? "run"}
                        </small>
                        <small>{e.message}</small>
                      </span>
                    </button>
                  ))
                ) : (
                  <Empty
                    title="No matching events"
                    description="Change the event filter or wait for execution."
                    demo={false}
                  />
                )}
              </div>
            </Panel>
            <Panel
              title="Evidence inspector"
              detail={
                event
                  ? `Event ${event.sequence} · ${event.provenance} provenance`
                  : "Select an event"
              }
            >
              <div className="panel-body">
                <Tabs defaultValue="event">
                  <TabsList className="flex flex-wrap h-auto gap-1">
                    <TabsTrigger value="event">Event</TabsTrigger>
                    <TabsTrigger value="results">Verification</TabsTrigger>
                    <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
                    <TabsTrigger value="manifest">Manifest</TabsTrigger>
                  </TabsList>
                  <TabsContent value="event" className="tab-panel">
                    {event ? (
                      <>
                        <div className="status-line mb-4">
                          <Status
                            value={
                              event.severity === "error"
                                ? "failed"
                                : event.severity
                            }
                          />
                          <span className="mono muted text-xs">
                            {event.timestamp}
                          </span>
                        </div>
                        <p className="muted text-xs mb-4">{event.message}</p>
                        <JsonView value={event} />
                      </>
                    ) : (
                      <Empty
                        title="Awaiting trace"
                        description="The adapter records normalized events during execution."
                        demo={false}
                      />
                    )}
                  </TabsContent>
                  <TabsContent value="results" className="tab-panel">
                    {query.data.results?.length ? (
                      query.data.results
                        .filter((r) => !task || r.task_id === task)
                        .map((r) => (
                          <details
                            className="border-b border-border py-3"
                            key={r.task_id}
                          >
                            <summary className="cursor-pointer text-xs">
                              <Status
                                value={r.passed ? "completed" : "failed"}
                              />{" "}
                              <span className="ml-2">
                                {r.task_name || r.task_id}
                              </span>{" "}
                              <span className="muted">
                                · {format(r.duration_seconds)} s
                              </span>
                            </summary>
                            <JsonView
                              value={{
                                output: r.output,
                                verification: r.verification,
                                error: r.error,
                              }}
                            />
                          </details>
                        ))
                    ) : (
                      <Empty title="No task results recorded" demo={false} />
                    )}
                  </TabsContent>
                  <TabsContent value="artifacts" className="tab-panel">
                    {query.data.artifacts?.length ? (
                      query.data.artifacts.map((a) => (
                        <ArtifactPreview key={a.id} run={id} artifact={a} />
                      ))
                    ) : (
                      <Empty
                        title="No persisted artifacts"
                        description="Files and diffs appear only when an adapter produces them. Tool inputs and outputs remain in the event inspector."
                        demo={false}
                      />
                    )}
                  </TabsContent>
                  <TabsContent value="manifest" className="tab-panel">
                    <JsonView value={query.data.manifest} />
                  </TabsContent>
                </Tabs>
              </div>
            </Panel>
          </div>
        </>
      ) : (
        <Panel title="Replay a persisted run">
          <Empty
            title="Every outcome has a trace"
            description="Select a run above to inspect normalized events, verifier evidence and artifacts."
            demo={!runs.data?.length}
          />
        </Panel>
      )}
    </>
  );
}
