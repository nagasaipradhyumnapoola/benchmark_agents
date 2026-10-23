import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import {
  Builder,
  defaultExperiment,
  validateExperiment,
} from "@/components/builder";
import { Registry, agentDefaults, modelDefaults } from "@/components/registry";
import { request } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

function mount(element: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(<QueryClientProvider client={client}>{element}</QueryClientProvider>);
  return client;
}

function fixture(modelCount = 2) {
  const posts: { path: string; body: any }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options?: RequestInit) => {
      if (options?.method === "POST") {
        posts.push({ path, body: JSON.parse(options.body as string) });
        return {
          ok: true,
          json: async () => ({
            compatible: true,
            reasons: [],
            warnings: [],
            capabilities: {},
            requirements: [],
          }),
        };
      }
      return {
        ok: true,
        json: async () =>
          path.endsWith("/models")
            ? Array.from({ length: modelCount }, (_, i) => ({
                id: `m${i + 1}`,
                config: {
                  ...modelDefaults,
                  name: `Model ${i + 1}`,
                  model: `provider-${i + 1}`,
                },
              }))
            : path.endsWith("/agents")
              ? [
                  ...[1, 2].map((i) => ({
                    id: `a${i}`,
                    config: { ...agentDefaults, name: `Harness ${i}` },
                  })),
                  {
                    id: "native",
                    config: {
                      ...agentDefaults,
                      name: "Native product",
                      native: true,
                    },
                  },
                  {
                    id: "cli",
                    config: {
                      ...agentDefaults,
                      name: "Uncontrolled CLI",
                      adapter: "codex-cli",
                    },
                  },
                ]
              : path.endsWith("/benchmarks")
                ? [{ id: "starter-v1", name: "Starter", version: "1" }]
                : {
                    tasks: [
                      {
                        id: "quick",
                        name: "Quick task",
                        category: "text",
                        verifier: "exact",
                        requires_execution: false,
                      },
                    ],
                  },
      };
    }),
  );
  return posts;
}

it("previews and validates four exact pairs, counts checks and invalidates on selection changes", async () => {
  const posts = fixture();
  mount(<Builder />);
  await screen.findByLabelText(/Model 1/);
  fireEvent.change(screen.getByLabelText("Evaluation mode"), {
    target: { value: "matrix" },
  });
  expect(
    screen.queryByLabelText("Shared model for agent evaluation"),
  ).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/Native product/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/Uncontrolled CLI/)).not.toBeInTheDocument();
  for (const label of ["Model 1", "Model 2", "Harness 1", "Harness 2"])
    fireEvent.click(screen.getByLabelText(new RegExp(label)));
  for (const harness of [1, 2])
    for (const model of [1, 2])
      expect(
        screen.getByText(`Harness ${harness} × Model ${model}`),
      ).toBeVisible();
  expect(screen.getByText("32 task checks")).toBeVisible();
  fireEvent.click(
    screen.getByRole("button", { name: "Use one quick text task" }),
  );
  fireEvent.change(screen.getByLabelText(/^Trials/), {
    target: { value: "2" },
  });
  expect(screen.getByText("8 task checks")).toBeVisible();
  fireEvent.change(screen.getByLabelText("Experiment name"), {
    target: { value: "Matrix" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Validate compatibility" }),
  );
  await screen.findByText("Ready to launch");
  expect(posts[0].body.systems).toEqual([
    { model_id: "m1", agent_id: "a1" },
    { model_id: "m1", agent_id: "a2" },
    { model_id: "m2", agent_id: "a1" },
    { model_id: "m2", agent_id: "a2" },
  ]);
  expect(
    screen.getByRole("button", { name: "Launch experiment" }),
  ).toBeEnabled();
  fireEvent.click(screen.getByLabelText(/Model 2/));
  expect(
    screen.getByRole("button", { name: "Launch experiment" }),
  ).toBeDisabled();
});

it("blocks matrices with an empty selection or more than sixteen pairs", async () => {
  const posts = fixture(9);
  mount(<Builder />);
  await screen.findByLabelText(/Model 1/);
  fireEvent.change(screen.getByLabelText("Evaluation mode"), {
    target: { value: "matrix" },
  });
  expect(
    screen.getByRole("button", { name: "Validate compatibility" }),
  ).toBeDisabled();
  for (let i = 1; i <= 9; i++)
    fireEvent.click(screen.getByLabelText(new RegExp(`Model ${i} `)));
  for (const i of [1, 2])
    fireEvent.click(screen.getByLabelText(new RegExp(`Harness ${i}`)));
  expect(screen.getByText(/18 pairs exceeds the limit of 16/)).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Validate compatibility" }),
  ).toBeDisabled();
  expect(posts).toHaveLength(0);
  expect(
    validateExperiment({
      ...defaultExperiment,
      name: "Large",
      mode: "matrix",
      systems: Array.from({ length: 17 }, (_, i) => ({
        model_id: `m${i}`,
        agent_id: "a",
      })),
    }),
  ).toMatch(/16/);
  expect(
    validateExperiment({
      ...defaultExperiment,
      name: "Missing",
      mode: "matrix",
      systems: [{ agent_id: "a" }],
    }),
  ).toMatch(/model and.*agent/);
});

it("connects hosted models with a separate write-only session key and re-enters forgotten credentials", async () => {
  let saved: any = null;
  const posts: any[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options?: RequestInit) => {
      if (options?.method === "POST") {
        const body = JSON.parse(options.body as string);
        posts.push({ path, body });
        if (path.endsWith("/connect"))
          saved = {
            ...body.config,
            api_key_env: "BENCH_AGENTS_SESSION_example",
          };
        return {
          ok: true,
          json: async () =>
            path.endsWith("/credential")
              ? { configured: true, scope: "session" }
              : { id: "model-1", config: saved },
        };
      }
      return {
        ok: true,
        json: async () =>
          path.endsWith("/runs")
            ? []
            : saved
              ? [{ id: "model-1", config: saved }]
              : [],
      };
    }),
  );
  const client = mount(<Registry kind="models" />);
  await screen.findByText("No models registered");
  fireEvent.click(screen.getByRole("button", { name: "Register model" }));
  fireEvent.change(screen.getByLabelText("Connection type"), {
    target: { value: "hosted" },
  });
  expect(screen.getByLabelText("Authentication")).toHaveValue("session");
  expect(screen.getByLabelText(/^Session API key/)).toHaveAttribute(
    "type",
    "password",
  );
  fireEvent.change(screen.getByLabelText("Display name"), {
    target: { value: "Hosted test" },
  });
  fireEvent.change(screen.getByLabelText(/^Provider model identifier/), {
    target: { value: "hosted-model" },
  });
  fireEvent.change(screen.getByLabelText(/^Endpoint base URL/), {
    target: { value: "https://example.test/v1" },
  });
  fireEvent.change(screen.getByLabelText(/^Session API key/), {
    target: { value: "test-secret" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Register configuration" }),
  );
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  expect(posts[0]).toMatchObject({
    path: "/api/models/connect",
    body: {
      config: { connection_type: "hosted", api_key_env: null },
      api_key: "test-secret",
    },
  });
  expect(JSON.stringify(saved)).not.toContain("test-secret");
  expect(screen.getByText(/re-enter.*backend restarts/i)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Re-enter session API key"), {
    target: { value: "replacement-secret" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Update session key" }));
  await screen.findByText(/Session key updated/);
  expect(posts[1]).toEqual({
    path: "/api/models/model-1/credential",
    body: { api_key: "replacement-secret" },
  });
  expect(screen.getByLabelText("Re-enter session API key")).toHaveValue("");
  expect(
    JSON.stringify(
      client
        .getMutationCache()
        .getAll()
        .map((mutation) => mutation.state.variables),
    ),
  ).not.toContain("secret");
});

it("does not render rejected request inputs from structured API errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: async () => ({
        detail: [{ msg: "Invalid", input: "test-secret" }],
      }),
    })),
  );
  await expect(request("/models/connect", {})).rejects.toThrow(
    "422 Unprocessable Entity",
  );
});
