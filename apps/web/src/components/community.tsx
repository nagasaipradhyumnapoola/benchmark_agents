"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAction, useApi } from "@/lib/api";
import { Empty, ErrorState, Loading, PageTitle, Panel } from "./common";

type Proposal = {
  kind: "agent" | "pairing" | "benchmark";
  title: string;
  description: string;
  author_name: string | null;
  source_url: string | null;
  license: string | null;
  recommended_models: string[];
  benchmark_ids: string[];
  evidence_url: string | null;
};
type Entry = Proposal & {
  id: string;
  publication_status: "published" | "local_draft";
  verification_status: "unverified";
  created_at?: string;
  share_url?: string;
  share_body?: string;
  share_requires_paste?: boolean;
};
type CommunityData = {
  published: Entry[];
  drafts: Entry[];
  repository_url: string;
  public_issues_url: string;
  contribution_docs_url: string;
  publication_note: string;
};

const lines = (value: string) =>
  value
    .split(/\r?\n/)
    .map((v) => v.trim())
    .filter(Boolean);

function Suggestion({ entry }: { entry: Entry }) {
  const [review, setReview] = useState(false);
  return (
    <article className="panel">
      <div className="panel-heading">
        <h3>{entry.title}</h3>
        <Badge variant="outline">
          {entry.publication_status === "local_draft"
            ? "Local draft · unverified"
            : "Unverified recommendation"}
        </Badge>
      </div>
      <p>{entry.description}</p>
      <p className="muted">
        {entry.kind}
        {entry.author_name ? ` · Suggested by ${entry.author_name}` : ""}
        {entry.license ? ` · License: ${entry.license}` : ""}
      </p>
      <p>
        <strong>Suggested models:</strong>{" "}
        {entry.recommended_models.join(", ") || "None specified"}
      </p>
      {entry.benchmark_ids.length > 0 && (
        <p>
          <strong>Benchmarks:</strong> {entry.benchmark_ids.join(", ")}
        </p>
      )}
      <div className="form-actions">
        {entry.source_url && (
          <a
            className="subtle-link"
            href={entry.source_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            View public source
          </a>
        )}
        {entry.evidence_url && (
          <a
            className="subtle-link"
            href={entry.evidence_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            View submitted evidence
          </a>
        )}
        {entry.publication_status === "local_draft" && (
          <>
            <a
              className="subtle-link"
              href={`/api/community/${encodeURIComponent(entry.id)}/export`}
              download
            >
              Download contribution JSON
            </a>
            <Button variant="outline" onClick={() => setReview(!review)}>
              {review ? "Close submission review" : "Review GitHub submission"}
            </Button>
          </>
        )}
      </div>
      {review && (
        <div className="stack">
          <p>
            Review everything below before opening GitHub. Your draft is still
            local; GitHub requires you to sign in and submit it yourself.
          </p>
          {entry.share_requires_paste ? (
            <p>
              Copy and paste the full review body below into the blank GitHub
              issue, or download the contribution JSON and attach it. Only the
              title travels in this link because the full body exceeds the link
              size limit.
            </p>
          ) : (
            <p>The title and body travel in the link.</p>
          )}
          <p>
            <strong>Issue title:</strong> [Community] {entry.title}
          </p>
          <pre
            className="json-view"
            tabIndex={0}
            role="region"
            aria-label="GitHub issue preview"
          >
            {entry.share_body}
          </pre>
          <a
            className="subtle-link"
            href={entry.share_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open GitHub to submit yourself
          </a>
        </div>
      )}
    </article>
  );
}

export function Community() {
  const query = useApi<CommunityData>("/community");
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState<Proposal["kind"]>("agent");
  const action = useAction<Entry>("/community", () => setSaved(true));
  const [saved, setSaved] = useState(false);
  const [formError, setFormError] = useState<Error | null>(null);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSaved(false);
    const form = new FormData(event.currentTarget);
    const text = (name: string) => String(form.get(name) ?? "").trim();
    const payload: Proposal = {
      kind,
      title: text("title"),
      description: text("description"),
      author_name: text("author_name") || null,
      source_url: text("source_url") || null,
      license: text("license") || null,
      recommended_models: lines(text("recommended_models")),
      benchmark_ids: lines(text("benchmark_ids")),
      evidence_url: text("evidence_url") || null,
    };
    if (
      !payload.title ||
      !payload.description ||
      (kind === "agent" && (!payload.source_url || !payload.license))
    ) {
      setFormError(
        new Error(
          "Enter a title and description. Agent suggestions also need a public source and license.",
        ),
      );
      return;
    }
    action.mutate(payload);
  }

  const matches = (entry: Entry) =>
    [
      entry.title,
      entry.description,
      entry.kind,
      entry.license ?? "",
      ...entry.recommended_models,
      ...entry.benchmark_ids,
    ]
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase());
  return (
    <div className="stack">
      <PageTitle
        title="Community"
        description="Share open-source agents, suggest model pairings and propose benchmarks."
      />
      <ErrorState error={query.error} retry={() => void query.refetch()} />
      {query.isLoading && <Loading />}
      {query.data && (
        <>
          <div className="notice">
            <p>{query.data.publication_note}</p>
          </div>
          <div className="form-actions">
            <a
              className="subtle-link"
              href={query.data.public_issues_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Browse public suggestions on GitHub
            </a>
            <a
              className="subtle-link"
              href={query.data.contribution_docs_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              How to contribute a catalog entry
            </a>
          </div>
          <label className="field">
            <span>Search community suggestions</span>
            <Input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <Panel
            title="Published recommendations"
            detail="Repository-backed suggestions updated with this installation. Recommendations are unverified; linked evidence is supplied by contributors."
          >
            {query.data.published.filter(matches).length ? (
              query.data.published
                .filter(matches)
                .map((entry) => <Suggestion key={entry.id} entry={entry} />)
            ) : (
              <Empty
                title={
                  search
                    ? "No matching published recommendations"
                    : "No published recommendations yet"
                }
                description="Accepted contributions appear after a maintainer reviews a catalog pull request and you receive the update."
              />
            )}
          </Panel>
          <Panel
            title="Local drafts"
            detail="Saved on this machine. Saving a draft does not publish it or register an agent."
          >
            {query.data.drafts.filter(matches).length ? (
              query.data.drafts
                .filter(matches)
                .map((entry) => <Suggestion key={entry.id} entry={entry} />)
            ) : (
              <Empty
                title={
                  search ? "No matching local drafts" : "No local drafts yet"
                }
                description="Save a suggestion below, then review its GitHub submission or download its JSON."
              />
            )}
          </Panel>
          <Panel
            title="Suggest something"
            detail="Share public metadata only. Never include API keys, provider endpoints, private credential references or local machine paths."
          >
            <form
              onSubmit={submit}
              className="stack"
              onChange={() => {
                setSaved(false);
                setFormError(null);
              }}
            >
              <div className="form-grid">
                <label className="field">
                  <span>Suggestion type</span>
                  <select
                    value={kind}
                    onChange={(event) =>
                      setKind(event.target.value as Proposal["kind"])
                    }
                  >
                    <option value="agent">Open-source agent</option>
                    <option value="pairing">Agent and model pairing</option>
                    <option value="benchmark">Benchmark</option>
                  </select>
                </label>
                <label className="field">
                  <span>Title</span>
                  <Input name="title" required maxLength={120} />
                </label>
                <label className="field">
                  <span>Your name (optional, public when shared)</span>
                  <Input name="author_name" maxLength={80} />
                </label>
                <label className="field">
                  <span>Public source URL</span>
                  <Input
                    name="source_url"
                    type="url"
                    placeholder="https://github.com/owner/project"
                    required={kind === "agent"}
                    maxLength={500}
                  />
                </label>
                <label className="field">
                  <span>License</span>
                  <Input
                    name="license"
                    placeholder="Apache-2.0, MIT, …"
                    required={kind === "agent"}
                    maxLength={100}
                  />
                </label>
                <label className="field">
                  <span>Public evidence URL (optional)</span>
                  <Input name="evidence_url" type="url" maxLength={500} />
                </label>
              </div>
              <label className="field">
                <span>Description</span>
                <textarea
                  name="description"
                  required
                  maxLength={1500}
                  rows={4}
                />
              </label>
              <label className="field">
                <span>Suggested models (one exact model name per line)</span>
                <textarea
                  name="recommended_models"
                  rows={3}
                  placeholder="provider/exact-model-name"
                />
              </label>
              <label className="field">
                <span>Benchmark IDs (optional, one per line)</span>
                <textarea name="benchmark_ids" rows={2} />
              </label>
              <p className="muted">
                Source and evidence links must use public HTTPS with no
                credentials, query or fragment. Source code is never fetched or
                executed here. Model suggestions do not establish compatibility
                or performance.
              </p>
              <ErrorState error={formError ?? action.error} />
              {saved && (
                <p role="status">
                  Saved locally. Review the draft before sharing it on GitHub.
                </p>
              )}
              <Button type="submit" disabled={action.isPending}>
                {action.isPending ? "Saving local draft…" : "Save local draft"}
              </Button>
            </form>
          </Panel>
        </>
      )}
    </div>
  );
}
