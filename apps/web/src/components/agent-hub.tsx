"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowUpRight,
  Boxes,
  Code2,
  Download,
  Search,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Empty, ErrorState, Loading, PageTitle, Panel } from "./common";

type User = { username: string };
type Manifest = {
  slug: string;
  name: string;
  summary: string;
  readme: string;
  version: string;
  license: string;
  runtime: "python" | "node";
  entrypoint: string;
  args: string[];
  model_flag: string | null;
  model_base_url_env: string | null;
  model_api_key_env: string | null;
  capabilities: string[];
  recommended_models: string[];
  benchmark_ids: string[];
  source_url: string | null;
  dependencies: string[];
  tags: string[];
};
type Release = {
  slug: string;
  owner: string;
  manifest: Manifest;
  files: Record<string, string>;
  digest: string;
  created_at: string;
};
type Agent = {
  slug: string;
  name: string;
  summary: string;
  owner: string;
  latest_version: string;
  license: string;
  recommended_models: string[];
  tags: string[];
  downloads: number;
};
type AgentDetail = {
  slug: string;
  owner: string;
  manifest: Manifest;
  latest_version: string;
  versions: { version: string; digest: string; created_at: string }[];
};
type Comment = { id: string; author: string; body: string; created_at: string };
type Report = {
  id: string;
  author: string;
  model: string;
  benchmark_id: string;
  passed: number;
  total: number;
  evidence_url?: string | null;
};
type RunShare = {
  slug: string;
  version: string;
  model: string;
  benchmark_id: string;
  passed: number;
  total: number;
  run_id: string;
};
const route = (value: string) => encodeURIComponent(value);
const releaseUrl = (slug: string, version: string) =>
  `/agents/${route(slug)}/versions/${route(version)}`;
const detailHref = (slug: string, version: string) =>
  `/hub?agent=${route(slug)}&version=${route(version)}`;
const lines = (value: string) =>
  value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
const asError = (error: unknown) =>
  error instanceof Error ? error : new Error("Request failed. Try again.");

async function request<T>(
  path: string,
  body?: unknown,
  publication = false,
): Promise<T> {
  const response = await fetch(`/api/hub${path}`, {
    credentials: "same-origin",
    cache: "no-store",
    ...(body === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(publication ? { "X-Agent-Hub-Rules": "2026-10-23" } : {}),
          },
          body: JSON.stringify(body),
        }),
  });
  const data = await response.json();
  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : "Request failed. Check the fields and try again.";
    throw new Error(detail);
  }
  return data as T;
}

function useHub<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setData(null);
    setError(null);
    setLoading(Boolean(path));
    if (path)
      void request<T>(path)
        .then((result) => {
          if (active) setData(result);
        })
        .catch((failure) => {
          if (active) setError(asError(failure));
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    return () => {
      active = false;
    };
  }, [path, revision]);
  return {
    data,
    error,
    loading,
    reload: () => setRevision((value) => value + 1),
  };
}

function Account({
  user,
  onChange,
}: {
  user: User | null;
  onChange: (user: User | null) => void;
}) {
  const [mode, setMode] = useState<"login" | "register" | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const password = form.elements.namedItem("password") as HTMLInputElement;
    setBusy(true);
    setError(null);
    try {
      const pending = request<{ user: User }>(`/auth/${mode}`, {
        username: String(fields.get("username") ?? "").trim(),
        password: String(fields.get("password") ?? ""),
      });
      password.value = "";
      fields.delete("password");
      const result = await pending;
      onChange(result.user);
      setMode(null);
    } catch {
      setError(
        new Error(
          "Account request failed. Check your credentials and that the hub is available, then try again.",
        ),
      );
    } finally {
      password.value = "";
      fields.delete("password");
      setBusy(false);
    }
  }
  async function logout() {
    setBusy(true);
    setError(null);
    try {
      await request("/auth/logout", {});
      onChange(null);
    } catch (failure) {
      setError(asError(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="stack hub-account" aria-label="Hub account">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="muted">
          {user
            ? `Signed in as ${user.username}`
            : "Browse and import freely. Sign in to publish, comment or share results."}
        </p>
        <div className="flex flex-wrap gap-3">
          {user ? (
            <Button
              variant="outline"
              onClick={() => void logout()}
              disabled={busy}
            >
              Sign out
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => {
                  setMode("login");
                  setError(null);
                }}
              >
                Sign in
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setMode("register");
                  setError(null);
                }}
              >
                Create account
              </Button>
            </>
          )}
        </div>
      </div>
      {!user && mode && (
        <form
          className="stack max-w-xl"
          onSubmit={(event) => void submit(event)}
        >
          <h2>
            {mode === "register"
              ? "Create a hub account"
              : "Sign in to the hub"}
          </h2>
          <div className="form-grid">
            <label className="field">
              <span>Username</span>
              <input
                name="username"
                autoComplete="username"
                required
                maxLength={40}
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                name="password"
                type="password"
                autoComplete={
                  mode === "register" ? "new-password" : "current-password"
                }
                required
                minLength={mode === "register" ? 12 : undefined}
                maxLength={256}
              />
            </label>
          </div>
          {mode === "register" && (
            <p className="muted text-xs">
              Use at least 12 characters. Your username appears on published
              releases and contributions.
            </p>
          )}
          <div className="flex gap-3">
            <Button type="submit" disabled={busy}>
              {busy
                ? "Submitting…"
                : mode === "register"
                  ? "Register account"
                  : "Sign in to account"}
            </Button>
            <Button variant="ghost" type="button" onClick={() => setMode(null)}>
              Cancel
            </Button>
          </div>
        </form>
      )}
      <ErrorState error={error} />
    </section>
  );
}

function Publisher({
  initial,
  onDone,
  onCancel,
}: {
  initial?: Release;
  onDone: (release: Release) => void;
  onCancel: () => void;
}) {
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploads, setUploads] = useState<Record<string, string>>({});
  const [uploading, setUploading] = useState(false);
  const [acceptedRules, setAcceptedRules] = useState(false);
  const manifest = initial?.manifest;
  const firstPath = Object.keys(initial?.files ?? {})[0] ?? "";
  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    setError(null);
    setUploading(true);
    try {
      if (files.length > 40)
        throw new Error("Choose at most 40 UTF-8 text files.");
      const result: Record<string, string> = {};
      let total = 0;
      for (const file of files) {
        total += file.size;
        if (file.size > 128 * 1024 || total > 1024 * 1024)
          throw new Error(
            "Source files must be at most 128 KiB each and 1 MiB in total.",
          );
        if (Object.hasOwn(result, file.name))
          throw new Error("Choose files with unique names.");
        result[file.name] = await file.text();
      }
      setUploads(result);
    } catch (failure) {
      setUploads({});
      event.target.value = "";
      setError(asError(failure));
    } finally {
      setUploading(false);
    }
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!acceptedRules) {
      setError(
        new Error(
          "Review and acknowledge the publication rules before publishing.",
        ),
      );
      return;
    }
    const fields = new FormData(event.currentTarget);
    const text = (name: string) => String(fields.get(name) ?? "").trim();
    try {
      const entrypoint = text("entrypoint");
      const path = text("file_path") || entrypoint;
      const code = String(fields.get("code") ?? "");
      const files = {
        ...initial?.files,
        ...uploads,
        ...(code ? { [path]: code } : {}),
      };
      if (!Object.hasOwn(files, entrypoint))
        throw new Error(
          "Add source code or upload a text file matching the entrypoint.",
        );
      const sizes = Object.values(files).map(
        (source) => new TextEncoder().encode(source).length,
      );
      if (
        sizes.length > 40 ||
        sizes.some((size) => size > 128 * 1024) ||
        sizes.reduce((a, b) => a + b, 0) > 1024 * 1024
      )
        throw new Error(
          "Use at most 40 files, 128 KiB per file and 1 MiB total.",
        );
      const args: unknown = text("args") ? JSON.parse(text("args")) : [];
      if (!Array.isArray(args) || args.some((arg) => typeof arg !== "string"))
        throw new Error(
          "Entrypoint arguments must be a JSON array of strings.",
        );
      const release = {
        manifest: {
          slug: text("slug"),
          name: text("name"),
          summary: text("summary"),
          readme: text("readme"),
          version: text("version"),
          license: text("license"),
          runtime: text("runtime"),
          entrypoint,
          args,
          model_flag: text("model_flag") || null,
          model_base_url_env: text("model_base_url_env") || null,
          model_api_key_env: text("model_api_key_env") || null,
          capabilities: ["text"],
          recommended_models: lines(text("recommended_models")),
          benchmark_ids: lines(text("benchmark_ids")),
          source_url: text("source_url") || null,
          dependencies: lines(text("dependencies")),
          tags: text("tags")
            .split(",")
            .map((tag) => tag.trim())
            .filter(Boolean),
        },
        files,
      };
      setBusy(true);
      onDone(
        await request<Release>(
          initial ? `/agents/${route(initial.slug)}/versions` : "/agents",
          release,
          true,
        ),
      );
    } catch (failure) {
      setError(asError(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel
      title={initial ? "Publish a new version" : "Publish an agent"}
      detail="Publish immutable UTF-8 source and usage instructions to the connected hub. Include only source you have permission to share."
    >
      <form className="stack pt-6" onSubmit={(event) => void submit(event)}>
        <div className="publish-section-heading">
          <h3>Agent details</h3>
          <p>
            Give developers a clear reason to use your agent and explain how it
            works.
          </p>
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Agent name</span>
            <input
              name="name"
              required
              maxLength={120}
              defaultValue={manifest?.name}
            />
          </label>
          <label className="field">
            <span>Slug</span>
            <input
              name="slug"
              aria-label="Slug"
              required
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
              defaultValue={manifest?.slug}
              readOnly={Boolean(initial)}
            />
            <small>
              Lowercase letters, numbers and hyphens. The first publisher owns
              this slug.
            </small>
          </label>
          <label className="field">
            <span>Version</span>
            <input
              name="version"
              aria-label="Version"
              required
              placeholder="1.0.0"
            />
            <small>
              Use a new semantic version. Published versions cannot be replaced.
            </small>
          </label>
          <label className="field">
            <span>License</span>
            <input
              name="license"
              required
              defaultValue={manifest?.license}
              placeholder="MIT or Apache-2.0"
            />
          </label>
        </div>
        <label className="field">
          <span>Summary</span>
          <input
            name="summary"
            required
            maxLength={500}
            defaultValue={manifest?.summary}
          />
        </label>
        <label className="field">
          <span>README</span>
          <textarea
            name="readme"
            aria-label="README"
            required
            rows={5}
            defaultValue={manifest?.readme}
          />
          <small>
            Describe inputs, outputs, usage, limitations and model requirements.
          </small>
        </label>
        <div className="publish-section-heading">
          <h3>Source & runtime</h3>
          <p>
            Publish the code behind this version. Imports use this exact source.
          </p>
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Runtime</span>
            <select name="runtime" defaultValue={manifest?.runtime ?? "python"}>
              <option value="python">Python</option>
              <option value="node">Node.js</option>
            </select>
          </label>
          <label className="field">
            <span>Entrypoint</span>
            <input
              name="entrypoint"
              aria-label="Entrypoint"
              required
              placeholder="agent.py"
              defaultValue={manifest?.entrypoint}
            />
            <small>
              Relative path to the script the local harness will use.
            </small>
          </label>
        </div>
        <label className="field">
          <span>Source file path</span>
          <input
            name="file_path"
            placeholder="Same as entrypoint when blank"
            defaultValue={firstPath}
          />
        </label>
        <label className="field">
          <span>Source code</span>
          <textarea
            name="code"
            aria-label="Source code"
            rows={10}
            spellCheck={false}
            defaultValue={initial?.files[firstPath] ?? ""}
          />
          <small>
            Paste one source file, or upload files below. Never include
            credentials or private configuration.
          </small>
        </label>
        <label className="field">
          <span>Upload text source files (optional)</span>
          <input
            type="file"
            multiple
            onChange={(event) => void upload(event)}
          />
          <small>
            Up to 40 files; 128 KiB each, 1 MiB total. Uploaded files use their
            file names; use the source path field for a nested path.
          </small>
        </label>
        {Object.keys(uploads).length > 0 && (
          <p className="mono text-xs break-all">
            Files ready: {Object.keys(uploads).join(", ")}
          </p>
        )}
        <div className="publish-section-heading">
          <h3>Models & discoverability</h3>
          <p>Help people find your agent and choose a model to test it with.</p>
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Recommended models (one per line)</span>
            <textarea
              name="recommended_models"
              aria-label="Recommended models (one per line)"
              rows={3}
              defaultValue={manifest?.recommended_models.join("\n")}
            />
            <small>
              Exact provider/model IDs. Recommendations do not establish
              compatibility.
            </small>
          </label>
          <label className="field">
            <span>Benchmark IDs (one per line, optional)</span>
            <textarea
              name="benchmark_ids"
              rows={3}
              defaultValue={manifest?.benchmark_ids.join("\n")}
            />
          </label>
          <label className="field">
            <span>Tags (comma separated, optional)</span>
            <input name="tags" defaultValue={manifest?.tags.join(", ")} />
          </label>
          <label className="field">
            <span>Public source URL (optional)</span>
            <input
              name="source_url"
              type="url"
              defaultValue={manifest?.source_url ?? ""}
              placeholder="https://github.com/owner/project"
            />
          </label>
        </div>
        <details>
          <summary className="cursor-pointer py-3">
            Model bindings, arguments and dependencies
          </summary>
          <div className="stack py-4">
            <p className="muted text-xs">
              Specify variable names only. Endpoint values and API keys belong
              in your private local model registration.
            </p>
            <label className="field">
              <span>Entrypoint arguments (JSON array, optional)</span>
              <input
                name="args"
                defaultValue={manifest ? JSON.stringify(manifest.args) : ""}
                placeholder={'["--format", "json"]'}
              />
            </label>
            <div className="form-grid">
              <label className="field">
                <span>Model flag (optional)</span>
                <input
                  name="model_flag"
                  defaultValue={manifest?.model_flag ?? ""}
                  placeholder="--model"
                />
              </label>
              <label className="field">
                <span>Model base URL environment variable (optional)</span>
                <input
                  name="model_base_url_env"
                  defaultValue={manifest?.model_base_url_env ?? ""}
                  placeholder="OPENAI_BASE_URL"
                />
              </label>
              <label className="field">
                <span>Model API key environment variable (optional)</span>
                <input
                  name="model_api_key_env"
                  defaultValue={manifest?.model_api_key_env ?? ""}
                  placeholder="OPENAI_API_KEY"
                />
              </label>
            </div>
            <label className="field">
              <span>Dependencies (one per line, informational)</span>
              <textarea
                name="dependencies"
                rows={3}
                defaultValue={manifest?.dependencies.join("\n")}
              />
              <small>
                Import does not install dependencies. Review and install them
                separately if you trust the source.
              </small>
            </label>
          </div>
        </details>
        <div className="publish-rules-summary">
          <p>
            Publish only source you have permission to distribute. Keep
            credentials and private data out of every file and description.
          </p>
          <Link href="/rules" className="subtle-link">
            Read the publication rules <ArrowUpRight size={14} />
          </Link>
          <label className="policy-ack">
            <input
              type="checkbox"
              required
              checked={acceptedRules}
              onChange={(event) => setAcceptedRules(event.target.checked)}
            />
            <span>
              I have reviewed the publication rules and have permission to share
              this source.
            </span>
          </label>
        </div>
        <ErrorState error={error} />
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy || uploading || !acceptedRules}>
            <Upload size={15} />
            {busy ? "Publishing…" : "Publish release"}
          </Button>
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel publishing
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function Contributions({
  release,
  user,
  run,
}: {
  release: Release;
  user: User | null;
  run: RunShare | null;
}) {
  const base = releaseUrl(release.slug, release.manifest.version);
  const comments = useHub<{ items: Comment[] }>(`${base}/comments`);
  const reports = useHub<{ items: Report[] }>(`${base}/reports`);
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);
  const [shared, setShared] = useState(false);
  async function submit(
    event: React.FormEvent<HTMLFormElement>,
    kind: "comments" | "reports",
  ) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const text = (name: string) => String(fields.get(name) ?? "").trim();
    setError(null);
    setBusy(true);
    try {
      await request(
        `${base}/${kind}`,
        kind === "comments"
          ? { body: text("body") }
          : {
              model: text("model"),
              benchmark_id: text("benchmark_id"),
              passed: Number(text("passed")),
              total: Number(text("total")),
              evidence_url: text("evidence_url") || null,
            },
      );
      form.reset();
      if (kind === "comments") comments.reload();
      else reports.reload();
    } catch (failure) {
      setError(asError(failure));
    } finally {
      setBusy(false);
    }
  }
  async function shareRun() {
    if (!run) return;
    setError(null);
    setBusy(true);
    try {
      await request("/share-run", {
        run_id: run.run_id,
        slug: release.slug,
        version: release.manifest.version,
      });
      setShared(true);
      reports.reload();
    } catch (failure) {
      setError(asError(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div id="agent-results" />
      <Panel
        title="Benchmark results"
        detail="Contributor summaries are self-reported and not verified by the hub. Compare model, benchmark and source version before drawing conclusions."
      >
        <div className="stack py-6">
          <ErrorState error={reports.error} retry={reports.reload} />
          {run && (
            <div className="stack">
              <h3>Your completed local run</h3>
              <p>
                {run.model} · {run.benchmark_id} · {run.passed} / {run.total}{" "}
                tasks passed local verification
              </p>
              <p className="muted text-xs">
                Sharing sends this summary to the connected hub. It appears as
                self-reported; the hub does not independently verify your local
                run.
              </p>
              <Button
                disabled={!user || busy || shared}
                onClick={() => void shareRun()}
              >
                {shared
                  ? "Benchmark result shared"
                  : "Share this benchmark result"}
              </Button>
              {!user && (
                <p className="muted">Sign in above to share this result.</p>
              )}
            </div>
          )}
          {reports.loading ? (
            <p role="status">Loading results…</p>
          ) : reports.data?.items.length ? (
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Self-reported benchmark results"
            >
              <table>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Benchmark</th>
                    <th>Passed / total</th>
                    <th>Contributor</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.data.items.map((report) => (
                    <tr key={report.id}>
                      <td className="whitespace-normal break-all">
                        {report.model}
                        <div>
                          <Badge variant="outline">Self-reported</Badge>
                        </div>
                      </td>
                      <td>{report.benchmark_id}</td>
                      <td>
                        {report.passed} / {report.total}
                      </td>
                      <td>{report.author}</td>
                      <td>
                        {report.evidence_url ? (
                          <a
                            className="subtle-link"
                            href={report.evidence_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            View evidence
                          </a>
                        ) : (
                          "Not provided"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">No results shared for this version.</p>
          )}
          {user ? (
            <details>
              <summary className="cursor-pointer py-3">
                Share a benchmark result manually
              </summary>
              <form
                className="stack pt-4"
                onSubmit={(event) => void submit(event, "reports")}
              >
                <div className="form-grid">
                  <label className="field">
                    <span>Result model</span>
                    <input name="model" required />
                  </label>
                  <label className="field">
                    <span>Result benchmark ID</span>
                    <input name="benchmark_id" required />
                  </label>
                  <label className="field">
                    <span>Tasks passed</span>
                    <input name="passed" type="number" min={0} required />
                  </label>
                  <label className="field">
                    <span>Total tasks</span>
                    <input name="total" type="number" min={1} required />
                  </label>
                  <label className="field full">
                    <span>Public evidence URL (optional)</span>
                    <input name="evidence_url" type="url" />
                  </label>
                </div>
                <Button disabled={busy} type="submit">
                  Share benchmark result
                </Button>
              </form>
            </details>
          ) : (
            <p className="muted text-xs">
              Sign in to share a self-reported benchmark summary.
            </p>
          )}
        </div>
      </Panel>
      <div id="agent-discussion" />
      <Panel
        title="Discussion"
        detail="Comments belong to this specific source version."
      >
        <div className="stack py-6">
          <ErrorState error={comments.error} retry={comments.reload} />
          {comments.loading ? (
            <p role="status">Loading comments…</p>
          ) : comments.data?.items.length ? (
            comments.data.items.map((comment) => (
              <article className="border-b pb-5" key={comment.id}>
                <p className="text-xs muted mb-2">
                  {comment.author} ·{" "}
                  {new Date(comment.created_at).toLocaleDateString()}
                </p>
                <p className="whitespace-pre-wrap break-words">
                  {comment.body}
                </p>
              </article>
            ))
          ) : (
            <p className="muted">No comments on this version.</p>
          )}
          {user ? (
            <form
              className="stack"
              onSubmit={(event) => void submit(event, "comments")}
            >
              <label className="field">
                <span>Add a comment</span>
                <textarea name="body" required rows={3} maxLength={4000} />
              </label>
              <Button disabled={busy} type="submit">
                Post comment
              </Button>
            </form>
          ) : (
            <p className="muted text-xs">Sign in to join the discussion.</p>
          )}
        </div>
      </Panel>
      <ErrorState error={error} />
    </>
  );
}

function Detail({
  slug,
  version,
  user,
  run,
  onPublish,
}: {
  slug: string;
  version: string;
  user: User | null;
  run: RunShare | null;
  onPublish: (release: Release) => void;
}) {
  const router = useRouter();
  const agent = useHub<AgentDetail>(`/agents/${route(slug)}`);
  const selectedVersion = version || agent.data?.latest_version || "";
  const query = useHub<Release>(
    selectedVersion ? releaseUrl(slug, selectedVersion) : null,
  );
  const [sourcePath, setSourcePath] = useState("");
  const [busy, setBusy] = useState(false);
  const [imported, setImported] = useState<{
    id: string;
    dependencies: string[];
  } | null>(null);
  const [error, setError] = useState<Error | null>(null);
  useEffect(() => {
    setImported(null);
    setError(null);
    setSourcePath("");
  }, [slug, selectedVersion]);
  async function importAgent() {
    if (!query.data) return;
    setBusy(true);
    setError(null);
    try {
      const result = await request<{
        agent: { id: string };
        dependencies: string[];
      }>("/import", {
        slug,
        version: selectedVersion,
        expected_digest: query.data.digest,
      });
      setImported({ id: result.agent.id, dependencies: result.dependencies });
    } catch (failure) {
      setError(asError(failure));
    } finally {
      setBusy(false);
    }
  }
  const release = query.data;
  if (agent.loading || query.loading) return <Loading />;
  return (
    <div className="stack">
      <Link href="/hub" className="subtle-link">
        <ArrowLeft size={15} />
        All agents
      </Link>
      <ErrorState
        error={agent.error ?? query.error}
        retry={() => {
          agent.reload();
          query.reload();
        }}
      />
      {release && (
        <>
          <div className="hub-release-heading">
            <div className="min-w-0">
              <p className="hub-owner">
                {release.owner} / {release.slug}
              </p>
              <h2 className="text-2xl break-words">{release.manifest.name}</h2>
              <p className="muted mt-2 break-words">
                {release.manifest.summary}
              </p>
              <p className="muted text-xs mt-3 break-all">
                {release.owner} / {release.slug} · {release.manifest.license} ·{" "}
                {release.manifest.runtime}
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                disabled={busy || Boolean(imported)}
                onClick={() => void importAgent()}
              >
                <Download size={15} />
                {busy
                  ? "Importing…"
                  : imported
                    ? "Agent imported"
                    : "Import agent"}
              </Button>
              {user?.username === release.owner && (
                <Button variant="outline" onClick={() => onPublish(release)}>
                  Publish new version
                </Button>
              )}
            </div>
          </div>
          <nav
            className="release-navigation"
            aria-label="Agent release sections"
          >
            <a href="#agent-usage">Usage & license</a>
            <a href="#agent-source">
              Source code <span>{Object.keys(release.files).length}</span>
            </a>
            <a href="#agent-results">Benchmark results</a>
            <a href="#agent-discussion">Discussion</a>
          </nav>
          <div className="notice">
            <p>
              Import downloads and stages source code and configuration only. It
              does not execute code or install dependencies. Review source
              before trusting it. Host execution requires a separate explicit
              trusted-agent opt-in in the experiment builder.
            </p>
          </div>
          <ErrorState error={error} />
          {imported && (
            <div className="stack">
              <p role="status">
                Agent registered in your local workspace.
                {imported.dependencies.length
                  ? ` Dependencies to review separately: ${imported.dependencies.join(", ")}.`
                  : ""}
              </p>
              <Link
                className="subtle-link"
                href={`/experiments/new?agent=${route(imported.id)}`}
              >
                Benchmark imported agent <ArrowUpRight size={15} />
              </Link>
              <p className="muted text-xs">
                Pair it with a configured model and validate compatibility
                before running.
              </p>
            </div>
          )}
          <div className="form-grid">
            <label className="field">
              <span>Release version</span>
              <select
                value={selectedVersion}
                onChange={(event) =>
                  router.push(detailHref(slug, event.target.value))
                }
              >
                {(agent.data?.versions ?? []).map((item) => (
                  <option key={item.version} value={item.version}>
                    {item.version}
                  </option>
                ))}
              </select>
            </label>
            <div className="field">
              <span>Recommended models</span>
              <p className="break-all">
                {release.manifest.recommended_models.join(", ") ||
                  "No model recommendations supplied"}
              </p>
              <small>
                Publisher suggestions; validate your model pairing locally.
              </small>
            </div>
          </div>
          <div id="agent-usage" />
          <Panel title="Usage and license">
            <div className="stack py-6">
              <p className="whitespace-pre-wrap break-words max-w-prose leading-7">
                {release.manifest.readme}
              </p>
              <p>
                <strong>License:</strong> {release.manifest.license}
              </p>
              {release.manifest.source_url && (
                <a
                  className="subtle-link break-all"
                  href={release.manifest.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Public source <ArrowUpRight size={14} />
                </a>
              )}
              {release.manifest.tags.length > 0 && (
                <p className="muted break-words">
                  Tags: {release.manifest.tags.join(", ")}
                </p>
              )}
              <p className="muted break-words text-xs">
                Suggested benchmarks:{" "}
                {release.manifest.benchmark_ids.join(", ") || "None supplied"}
              </p>
              <p className="muted break-words text-xs">
                Dependencies (not installed by import):{" "}
                {release.manifest.dependencies.join(", ") || "None declared"}
              </p>
            </div>
          </Panel>
          <div id="agent-source" />
          <Panel
            title="Review source"
            detail="Source is shown as text. Review every file before enabling trusted host execution."
          >
            <div className="stack py-6">
              <label className="field">
                <span>Source file</span>
                <select
                  value={sourcePath || Object.keys(release.files)[0] || ""}
                  onChange={(event) => setSourcePath(event.target.value)}
                >
                  {Object.keys(release.files).map((path) => (
                    <option key={path}>{path}</option>
                  ))}
                </select>
              </label>
              <pre
                className="json-view"
                tabIndex={0}
                role="region"
                aria-label="Source preview"
              >
                {release.files[sourcePath || Object.keys(release.files)[0]]}
              </pre>
              <details>
                <summary className="cursor-pointer py-3">
                  Release digest and runtime configuration
                </summary>
                <dl className="stack text-xs py-4">
                  <div>
                    <dt className="muted">SHA-256 digest</dt>
                    <dd className="mono break-all mt-1 ml-0">
                      {release.digest}
                    </dd>
                  </div>
                  <div>
                    <dt className="muted">Entrypoint and arguments</dt>
                    <dd className="mono break-all mt-1 ml-0">
                      {release.manifest.entrypoint}{" "}
                      {JSON.stringify(release.manifest.args)}
                    </dd>
                  </div>
                  <div>
                    <dt className="muted">Model bindings</dt>
                    <dd className="mono break-all mt-1 ml-0">
                      {JSON.stringify({
                        model_flag: release.manifest.model_flag,
                        model_base_url_env: release.manifest.model_base_url_env,
                        model_api_key_env: release.manifest.model_api_key_env,
                      })}
                    </dd>
                  </div>
                </dl>
              </details>
            </div>
          </Panel>
          <Contributions
            key={`${slug}/${selectedVersion}`}
            release={release}
            user={user}
            run={
              run?.slug === release.slug &&
              run.version === release.manifest.version
                ? run
                : null
            }
          />
        </>
      )}
    </div>
  );
}

export function AgentHub() {
  const router = useRouter();
  const params = useSearchParams();
  const status = useHub<{ available: boolean; url: string; message: string }>(
    "/status",
  );
  const account = useHub<{ user: User | null }>("/auth/me");
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    if (account.data) setUser(account.data.user);
  }, [account.data]);
  const runId = params.get("run");
  const run = useHub<RunShare>(runId ? `/runs/${route(runId)}/share` : null);
  const slug = params.get("agent") || run.data?.slug || "";
  const version = params.get("version") || run.data?.version || "";
  const [publishing, setPublishing] = useState(false);
  const [initial, setInitial] = useState<Release | undefined>();
  const filterParams = new URLSearchParams();
  for (const key of ["search", "model", "license"]) {
    const value = params.get(key)?.trim();
    if (value) filterParams.set(key, value);
  }
  const filters = filterParams.toString();
  const requestedPage = Number(params.get("page") || "1");
  const page =
    Number.isSafeInteger(requestedPage) && requestedPage > 0
      ? requestedPage
      : 1;
  const catalogQuery = new URLSearchParams(filters);
  if (page > 1) catalogQuery.set("page", String(page));
  const catalog = useHub<{
    items: Agent[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
  }>(
    status.data?.available && !slug
      ? `/agents${catalogQuery.size ? `?${catalogQuery}` : ""}`
      : null,
  );
  function pageHref(value: number) {
    const query = new URLSearchParams(filters);
    if (value > 1) query.set("page", String(value));
    return `/hub${query.size ? `?${query}` : ""}`;
  }
  function publish(release: Release) {
    setPublishing(false);
    setInitial(undefined);
    catalog.reload();
    router.push(detailHref(release.slug, release.manifest.version));
  }
  return (
    <div className="stack agent-hub">
      <PageTitle
        title="Agent Hub"
        description="Browse source, choose a model, and test an agent in your own workspace."
        action={
          <Button
            disabled={!status.data?.available || !user}
            onClick={() => {
              setInitial(undefined);
              setPublishing(true);
            }}
          >
            <Upload size={15} />
            Publish an agent
          </Button>
        }
      />
      <Account
        user={user}
        onChange={(value) => {
          setUser(value);
          if (!value) setPublishing(false);
        }}
      />
      <ErrorState error={status.error} retry={status.reload} />
      <ErrorState error={account.error} retry={account.reload} />
      <ErrorState error={run.error} retry={run.reload} />
      {status.loading && <Loading />}
      {status.data && (
        <div className="hub-registry-line">
          <span className="min-w-0 break-all">
            {status.data.available
              ? "Connected registry"
              : "Registry unavailable"}{" "}
            <span className="muted">{status.data.url}</span>
          </span>
          <Link className="subtle-link" href="/community">
            Repository community suggestions <ArrowUpRight size={13} />
          </Link>
        </div>
      )}
      {status.data && !status.data.available && (
        <div className="stack">
          <h2>Hub is unavailable</h2>
          <p className="muted">{status.data.message}</p>
          <p>Start your local registry, then try again:</p>
          <pre
            className="json-view"
            tabIndex={0}
            role="region"
            aria-label="Hub start command"
          >
            uv run agent-hub hub
          </pre>
          <Button variant="outline" onClick={status.reload}>
            Reconnect to hub
          </Button>
        </div>
      )}
      {status.data?.available && (
        <>
          {publishing && user ? (
            <Publisher
              key={
                initial ? `${initial.slug}/${initial.manifest.version}` : "new"
              }
              initial={initial}
              onDone={publish}
              onCancel={() => setPublishing(false)}
            />
          ) : slug ? (
            <Detail
              key={slug}
              slug={slug}
              version={version}
              user={user}
              run={run.data}
              onPublish={(release) => {
                setInitial(release);
                setPublishing(true);
              }}
            />
          ) : (
            <div className="hub-directory">
              <form
                key={filters}
                className="hub-filters stack"
                onSubmit={(event) => {
                  event.preventDefault();
                  const form = new FormData(event.currentTarget);
                  const query = new URLSearchParams();
                  for (const key of ["search", "model", "license"]) {
                    const value = String(form.get(key) ?? "").trim();
                    if (value) query.set(key, value);
                  }
                  router.push(`/hub${query.size ? `?${query}` : ""}`);
                }}
              >
                <h2>Find your agent</h2>
                <div className="stack">
                  <label className="field">
                    <span>Search agents</span>
                    <input
                      name="search"
                      type="search"
                      placeholder="Name, description or tag"
                      defaultValue={params.get("search") ?? ""}
                      maxLength={200}
                    />
                  </label>
                  <label className="field">
                    <span>Filter by model</span>
                    <input
                      name="model"
                      placeholder="provider/exact-model"
                      defaultValue={params.get("model") ?? ""}
                      maxLength={200}
                    />
                  </label>
                  <label className="field">
                    <span>Filter by license</span>
                    <input
                      name="license"
                      placeholder="MIT, Apache-2.0…"
                      defaultValue={params.get("license") ?? ""}
                      maxLength={100}
                    />
                  </label>
                </div>
                <div>
                  <Button type="submit" variant="outline">
                    <Search size={15} />
                    Search registry
                  </Button>
                  {filters && (
                    <Button
                      variant="ghost"
                      type="button"
                      onClick={() => router.push("/hub")}
                    >
                      Clear filters
                    </Button>
                  )}
                </div>
                <div className="hub-import-guide">
                  <h3>From source to a result</h3>
                  <ol>
                    <li>Review the agent’s source and license.</li>
                    <li>Import a version into your workspace.</li>
                    <li>Connect your model and run a benchmark.</li>
                  </ol>
                  <Link className="subtle-link" href="/docs">
                    Integration guide <ArrowUpRight size={14} />
                  </Link>
                </div>
              </form>
              <section className="hub-results" aria-label="Agent directory">
                <div className="hub-results-heading">
                  <h2>Browse agents</h2>
                  <span className="muted" role="status" aria-live="polite">
                    {catalog.data
                      ? `${catalog.data.total} ${catalog.data.total === 1 ? "agent" : "agents"}`
                      : "Loading registry…"}
                  </span>
                </div>
                <ErrorState error={catalog.error} retry={catalog.reload} />
                {catalog.loading ? (
                  <Loading />
                ) : catalog.data?.items.length ? (
                  <div className="hub-agent-list">
                    {catalog.data.items.map((agent) => (
                      <article className="hub-agent-row" key={agent.slug}>
                        <div className="hub-agent-mark" aria-hidden="true">
                          <Code2 size={21} strokeWidth={1.5} />
                        </div>
                        <div className="min-w-0">
                          <p className="hub-agent-owner">
                            {agent.owner} / {agent.slug}
                          </p>
                          <div className="flex flex-wrap items-baseline justify-between gap-3">
                            <h3>
                              <Link
                                className="subtle-link hub-agent-name break-words"
                                href={detailHref(
                                  agent.slug,
                                  agent.latest_version,
                                )}
                              >
                                {agent.name} <ArrowUpRight size={15} />
                              </Link>
                            </h3>
                          </div>
                          <p className="mt-2 max-w-prose break-words">
                            {agent.summary}
                          </p>
                          <div className="hub-agent-meta">
                            <span>{agent.license}</span>
                            <span>v{agent.latest_version}</span>
                            <span>
                              <Download size={13} /> {agent.downloads}{" "}
                              {agent.downloads === 1 ? "download" : "downloads"}
                            </span>
                          </div>
                          <p className="muted text-xs mt-3 break-all">
                            Suggested models:{" "}
                            {agent.recommended_models.slice(0, 3).join(", ") ||
                              "None suggested"}
                            {agent.recommended_models.length > 3 &&
                              ` · +${agent.recommended_models.length - 3} more on release`}
                          </p>
                          {agent.tags.length > 0 && (
                            <p className="muted text-xs mt-2 break-words">
                              {agent.tags.join(" · ")}
                            </p>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  catalog.data && (
                    <div className="hub-directory-empty">
                      <Boxes size={34} strokeWidth={1.2} aria-hidden="true" />
                      <Empty
                        title={
                          filters || page > 1
                            ? "No agents match these filters"
                            : "No agents published yet"
                        }
                        description={
                          page > 1
                            ? "This page is empty. Return to the first page to browse available agents."
                            : filters
                              ? "Try another model, license or search term."
                              : "The registry starts empty. Publish your source to make a versioned agent available here."
                        }
                      />
                      {!filters && page === 1 && (
                        <>
                          <p>
                            Publish a Python or Node.js agent with its code,
                            usage instructions and recommended models.
                          </p>
                          <Button
                            variant="outline"
                            disabled={!user}
                            onClick={() => {
                              setInitial(undefined);
                              setPublishing(true);
                            }}
                          >
                            {user
                              ? "Publish your first agent"
                              : "Create an account above to publish"}{" "}
                            <Upload size={14} />
                          </Button>
                          <Link className="subtle-link" href="/agents">
                            Already have an agent? Register it locally{" "}
                            <ArrowUpRight size={14} />
                          </Link>
                        </>
                      )}
                    </div>
                  )
                )}
                {catalog.data && (catalog.data.pages > 1 || page > 1) && (
                  <nav
                    className="hub-pagination"
                    aria-label="Agent results pages"
                  >
                    <div className="flex flex-wrap gap-2">
                      {page > 1 && (
                        <Button variant="outline" asChild>
                          <Link href={pageHref(1)}>First page</Link>
                        </Button>
                      )}
                      {page > 1 && page <= catalog.data.pages && (
                        <Button variant="outline" asChild>
                          <Link href={pageHref(page - 1)}>Previous</Link>
                        </Button>
                      )}
                      {page < catalog.data.pages && (
                        <Button variant="outline" asChild>
                          <Link href={pageHref(page + 1)}>Next page</Link>
                        </Button>
                      )}
                    </div>
                    <p className="muted">
                      {page <= catalog.data.pages
                        ? `Page ${page} of ${catalog.data.pages} · ${catalog.data.total} agents`
                        : "Page unavailable"}
                    </p>
                  </nav>
                )}
              </section>
            </div>
          )}
        </>
      )}
    </div>
  );
}
