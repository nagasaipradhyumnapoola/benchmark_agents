import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { AgentHub } from "@/components/agent-hub";

let params = "";
const push = vi.fn();
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(params),
  useRouter: () => ({ push }),
}));
const manifest = {
  slug: "test-agent",
  name: "Test agent",
  summary: "Text harness",
  readme: "Review this harness before execution.",
  version: "1.0.0",
  license: "MIT",
  runtime: "python",
  entrypoint: "agent.py",
  args: [],
  model_flag: null,
  model_base_url_env: null,
  model_api_key_env: null,
  capabilities: ["text"],
  recommended_models: ["provider/exact"],
  benchmark_ids: [],
  source_url: null,
  dependencies: [],
  tags: ["text"],
};
const release = {
  slug: manifest.slug,
  owner: "developer",
  manifest,
  files: { "agent.py": "print('source')" },
  digest: "a".repeat(64),
  created_at: "2026-10-23T00:00:00Z",
};
let user: { username: string } | null;
let calls: { path: string; body: Record<string, unknown> }[];
let rejectAuth = false;
let runVersion = "1.0.0";
let available = true;
beforeEach(() => {
  params = "";
  user = null;
  calls = [];
  rejectAuth = false;
  runVersion = "1.0.0";
  available = true;
  push.mockClear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options?: RequestInit) => {
      let data: unknown;
      if (options?.method === "POST") {
        const body = JSON.parse(String(options.body));
        calls.push({ path, body });
        if (/auth\/(register|login)$/.test(path)) {
          if (rejectAuth)
            return {
              ok: false,
              json: async () => ({ detail: "Invalid credentials" }),
            };
          user = { username: String(body.username) };
          data = { user };
        } else if (path.endsWith("/import"))
          data = {
            agent: { id: "saved-agent" },
            dependencies: [],
            source: {
              slug: manifest.slug,
              version: manifest.version,
              digest: release.digest,
            },
          };
        else data = release;
      } else if (path.endsWith("/status"))
        data = {
          available,
          url: "http://127.0.0.1:8100",
          message: "Ready",
        };
      else if (path.endsWith("/auth/me")) data = { user };
      else if (path.includes("/runs/"))
        data = {
          slug: "test-agent",
          version: runVersion,
          model: "local/model",
          benchmark_id: "starter-v1",
          passed: 2,
          total: 3,
          run_id: "completed-run",
        };
      else if (path.endsWith("/comments")) data = { items: [] };
      else if (path.endsWith("/reports"))
        data = {
          items: [
            {
              id: "r1",
              author: "developer",
              model: "provider/exact",
              benchmark_id: "starter-v1",
              passed: 1,
              total: 2,
              self_reported: true,
            },
          ],
        };
      else if (path.includes("/versions/"))
        data = {
          ...release,
          manifest: { ...manifest, version: path.split("/").at(-1) },
        };
      else if (path.endsWith("/agents/test-agent"))
        data = {
          ...release,
          latest_version: "1.0.0",
          versions: [
            { version: "1.0.0", digest: release.digest },
            { version: "0.9.0", digest: "b".repeat(64) },
          ],
        };
      else
        data = {
          items: [
            {
              ...manifest,
              owner: "developer",
              latest_version: "1.0.0",
              digest: release.digest,
              downloads: 0,
            },
          ],
          total: 1,
        };
      return { ok: true, json: async () => data };
    }),
  );
});

it("imports the inspected immutable release and links its saved registration to the experiment builder", async () => {
  params = "agent=test-agent&version=1.0.0";
  render(<AgentHub />);
  expect(
    await screen.findByRole("region", { name: "Source preview" }),
  ).toHaveTextContent("print('source')");
  fireEvent.click(screen.getByRole("button", { name: "Import agent" }));
  expect(
    await screen.findByRole("link", { name: "Benchmark imported agent" }),
  ).toHaveAttribute("href", "/experiments/new?agent=saved-agent");
  expect(calls).toContainEqual({
    path: "/api/hub/import",
    body: {
      slug: "test-agent",
      version: "1.0.0",
      expected_digest: release.digest,
    },
  });
  expect(
    screen.getByText(/does not execute.*install dependencies/i),
  ).toBeVisible();
});

it("keeps passwords out of persisted state and clears the password field after account submission", async () => {
  render(<AgentHub />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Create account" }),
  );
  fireEvent.change(screen.getByLabelText("Username"), {
    target: { value: "developer" },
  });
  const password = screen.getByLabelText("Password");
  fireEvent.change(password, { target: { value: "test-password-1234" } });
  fireEvent.click(screen.getByRole("button", { name: "Register account" }));
  expect(await screen.findByText("Signed in as developer")).toBeVisible();
  expect(password).toHaveValue("");
  expect(localStorage.length).toBe(0);
  expect(calls[0]).toEqual({
    path: "/api/hub/auth/register",
    body: { username: "developer", password: "test-password-1234" },
  });
});

it("publishes source text with exact model suggestions and explicit runtime bindings", async () => {
  user = { username: "developer" };
  render(<AgentHub />);
  const publish = await screen.findByRole("button", {
    name: "Publish an agent",
  });
  await waitFor(() => expect(publish).toBeEnabled());
  fireEvent.click(publish);
  for (const [label, value] of Object.entries({
    "Agent name": "Test agent",
    Slug: "test-agent",
    Version: "1.0.0",
    Summary: "Text harness",
    README: "Review this harness before execution.",
    License: "MIT",
    Entrypoint: "agent.py",
    "Source file path": "agent.py",
    "Source code": "print('source')",
    "Recommended models (one per line)": "provider/exact",
  })) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole("button", { name: "Publish release" }));
  await waitFor(() =>
    expect(calls.some((call) => call.path === "/api/hub/agents")).toBe(true),
  );
  expect(calls.find((call) => call.path === "/api/hub/agents")?.body).toEqual({
    manifest: { ...manifest, tags: [] },
    files: { "agent.py": "print('source')" },
  });
  expect(push).toHaveBeenCalledWith("/hub?agent=test-agent&version=1.0.0");
});

it("labels contributor results as self-reported and navigates immutable versions", async () => {
  params = "agent=test-agent&version=1.0.0";
  render(<AgentHub />);
  expect(
    await screen.findByText("Self-reported", { exact: true }),
  ).toBeVisible();
  expect(screen.getByText(/not verified by the hub/i)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Release version"), {
    target: { value: "0.9.0" },
  });
  expect(push).toHaveBeenCalledWith("/hub?agent=test-agent&version=0.9.0");
});

it("resolves a completed local run to its source release and shares only its saved identity", async () => {
  params = "run=completed-run";
  user = { username: "developer" };
  render(<AgentHub />);
  const share = await screen.findByRole("button", {
    name: "Share this benchmark result",
  });
  expect(screen.getByText(/local\/model.*2 \/ 3 tasks passed/)).toBeVisible();
  fireEvent.click(share);
  expect(
    await screen.findByRole("button", { name: "Benchmark result shared" }),
  ).toBeDisabled();
  expect(calls).toContainEqual({
    path: "/api/hub/share-run",
    body: { run_id: "completed-run", slug: "test-agent", version: "1.0.0" },
  });
});

it("does not offer to attach a local run to a different source version", async () => {
  params = "agent=test-agent&version=1.0.0&run=completed-run";
  runVersion = "0.9.0";
  user = { username: "developer" };
  render(<AgentHub />);
  await screen.findByRole("region", { name: "Source preview" });
  expect(
    screen.queryByRole("button", { name: "Share this benchmark result" }),
  ).not.toBeInTheDocument();
});

it("clears a rejected password while keeping the account form usable", async () => {
  rejectAuth = true;
  render(<AgentHub />);
  fireEvent.click(await screen.findByRole("button", { name: "Sign in" }));
  fireEvent.change(screen.getByLabelText("Username"), {
    target: { value: "developer" },
  });
  const password = screen.getByLabelText("Password");
  fireEvent.change(password, { target: { value: "wrong-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in to account" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Account request failed",
  );
  expect(password).toHaveValue("");
  expect(
    screen.getByRole("button", { name: "Sign in to account" }),
  ).toBeEnabled();
});

it("guides an unavailable registry to its actual start command", async () => {
  available = false;
  render(<AgentHub />);
  expect(
    await screen.findByRole("region", { name: "Hub start command" }),
  ).toHaveTextContent("uv run bench-agents hub");
  expect(
    screen.getByRole("button", { name: "Publish an agent" }),
  ).toBeDisabled();
});

it("requires a new immutable version and uses the owner release endpoint", async () => {
  params = "agent=test-agent&version=1.0.0";
  user = { username: "developer" };
  render(<AgentHub />);
  const newVersion = await screen.findByRole("button", {
    name: "Publish new version",
  });
  fireEvent.click(newVersion);
  expect(screen.getByLabelText("Version")).toHaveValue("");
  expect(screen.getByLabelText("Slug")).toHaveAttribute("readonly");
  fireEvent.change(screen.getByLabelText("Version"), {
    target: { value: "1.1.0" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Publish release" }));
  await waitFor(() =>
    expect(calls).toContainEqual({
      path: "/api/hub/agents/test-agent/versions",
      body: {
        manifest: { ...manifest, version: "1.1.0" },
        files: release.files,
      },
    }),
  );
});
