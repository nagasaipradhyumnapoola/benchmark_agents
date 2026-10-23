import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { defaultExperiment, validateExperiment } from "@/components/builder";
import {
  modelDefaults,
  agentDefaults,
  validateRegistration,
  Registry,
} from "@/components/registry";
import { request, useAction, useApi } from "@/lib/api";
import { Demo, MetricStrip } from "@/components/common";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
}));
function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      {children}
    </QueryClientProvider>
  );
}
describe("registration boundary validation", () => {
  it("requires provider identity and rejects secret values in environment references", () => {
    expect(validateRegistration({ ...modelDefaults, name: "Local" })).toMatch(
      /identifier/,
    );
    expect(
      validateRegistration({
        ...modelDefaults,
        name: "Local",
        model: "qwen",
        api_key_env: "sk-secret with spaces",
      }),
    ).toMatch(/environment variable/);
    expect(
      validateRegistration({
        ...modelDefaults,
        name: "Local",
        model: "qwen",
        api_key_env: "MODEL_KEY",
      }),
    ).toBeNull();
  });
  it("requires environment allowlist entries to be names", () => {
    expect(
      validateRegistration({
        ...agentDefaults,
        name: "Agent",
        env_allowlist: ["KEY=value"],
      }),
    ).toMatch(/names only/);
  });
  it("rejects secret values in controlled agent model mappings", () => {
    expect(
      validateRegistration({
        ...agentDefaults,
        name: "Harness",
        model_base_url_env: "https://provider.example",
      }),
    ).toMatch(/names only/);
    expect(
      validateRegistration({
        ...agentDefaults,
        name: "Harness",
        model_api_key_env: "secret value",
      }),
    ).toMatch(/names only/);
    expect(
      validateRegistration({
        ...agentDefaults,
        name: "Harness",
        model_base_url_env: "MODEL_BASE_URL",
        model_api_key_env: "MODEL_API_KEY",
      }),
    ).toBeNull();
  });
});
describe("experiment validation", () => {
  it("rejects no systems and incompatible task timeout budgets", () => {
    expect(
      validateExperiment({ ...defaultExperiment, name: "Baseline" }),
    ).toMatch(/Select at least/);
    expect(
      validateExperiment({
        ...defaultExperiment,
        name: "Baseline",
        systems: [{ model_id: "m" }],
        budget_seconds: 10,
        task_timeout_seconds: 20,
      }),
    ).toMatch(/cannot exceed/);
  });
  it("accepts an identifiable budgeted experiment", () => {
    expect(
      validateExperiment({
        ...defaultExperiment,
        name: "Baseline",
        systems: [{ model_id: "m" }],
      }),
    ).toBeNull();
  });
});
describe("truthful evidence states", () => {
  it("keeps unavailable measurements distinct from zero", () => {
    render(
      <MetricStrip
        metrics={{ total: 0, passed: 0, success_rate: null, cost_usd: null }}
      />,
    );
    expect(screen.getAllByText("Unavailable").length).toBe(3);
    expect(screen.getByText("0 / 0")).toBeVisible();
  });
  it("marks demonstration evidence and its scientific limitation", () => {
    render(<Demo />);
    expect(screen.getByText(/do not measure model intelligence/)).toBeVisible();
  });
});
describe("API-backed registration form", () => {
  it("registers a script harness with model mappings, selects it and offers a checked next step", async () => {
    let saved: Record<string, unknown> | null = null;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string, options?: RequestInit) => {
        if (input.endsWith("/probe"))
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
        if (options?.method === "POST") {
          saved = JSON.parse(options.body as string);
          return {
            ok: true,
            json: async () => ({ id: "agent-1", config: saved }),
          };
        }
        return {
          ok: true,
          json: async () =>
            input.endsWith("/runs")
              ? []
              : saved
                ? [{ id: "agent-1", config: saved }]
                : [],
        };
      }),
    );
    render(<Registry kind="agents" />, { wrapper });
    await screen.findByText("No agents registered");
    fireEvent.click(screen.getByRole("button", { name: "Register agent" }));
    fireEvent.change(screen.getByLabelText("Display name"), {
      target: { value: "Script harness" },
    });
    fireEvent.change(screen.getByLabelText(/^Executable/), {
      target: { value: "python" },
    });
    fireEvent.change(screen.getByLabelText(/^Script path/), {
      target: { value: "C:/agents/harness.py" },
    });
    fireEvent.change(screen.getByLabelText(/^Model flag/), {
      target: { value: "--model" },
    });
    fireEvent.change(
      screen.getByLabelText(/^Model endpoint environment variable/),
      { target: { value: "MODEL_BASE_URL" } },
    );
    fireEvent.change(
      screen.getByLabelText(/^Model API key environment variable/),
      { target: { value: "MODEL_API_KEY" } },
    );
    fireEvent.click(
      screen.getByText("Advanced configuration", { selector: "summary" }),
    );
    fireEvent.change(screen.getByLabelText(/^Additional arguments/), {
      target: { value: '["--json"]' },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Register configuration" }),
    );
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(saved).toMatchObject({
      executable: "python",
      args: ["C:/agents/harness.py", "--json"],
      model_flag: "--model",
      model_base_url_env: "MODEL_BASE_URL",
      model_api_key_env: "MODEL_API_KEY",
    });
    expect(
      await screen.findByText(/Configuration saved. Check compatibility/),
    ).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: "Probe compatibility" }),
    );
    expect(
      await screen.findByRole("heading", { name: "Compatibility confirmed" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: /Build an experiment with this agent/ }),
    ).toHaveAttribute("href", "/experiments/new?agent=agent-1");
  });
  it("searches persisted configurations and exposes a labelled registration dialog", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string) => ({
        ok: true,
        json: async () =>
          input.endsWith("/runs")
            ? []
            : [
                {
                  id: "model-1",
                  config: {
                    ...modelDefaults,
                    name: "Local research model",
                    model: "qwen",
                  },
                },
              ],
      })),
    );
    render(<Registry kind="models" />, { wrapper });
    expect(await screen.findByText("Local research model")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Search models"), {
      target: { value: "absent" },
    });
    expect(await screen.findByText("No matching configurations")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Register model" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName(
      "Register model configuration",
    );
    expect(screen.getByLabelText(/API key environment variable/)).toBeVisible();
    expect(screen.getByLabelText(/^Endpoint base URL/)).toHaveValue(
      "http://127.0.0.1:1234/v1",
    );
    fireEvent.change(screen.getByLabelText("Adapter"), {
      target: { value: "ollama" },
    });
    expect(screen.getByLabelText(/^Endpoint base URL/)).toHaveValue(
      "http://127.0.0.1:11434",
    );
  });
  it("shows server validation errors instead of treating rejected input as success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 422,
        statusText: "Unprocessable Entity",
        json: async () => ({ detail: "Unknown adapter" }),
      })),
    );
    await expect(request("/models", {})).rejects.toThrow("Unknown adapter");
  });
});
function MutationFixture() {
  const query = useApi<{ value: number }>("/fixture");
  const action = useAction("/fixture");
  return (
    <>
      <span>Value: {query.data?.value ?? "loading"}</span>
      <button onClick={() => action.mutate({ value: 2 })}>Update record</button>
    </>
  );
}
describe("server state synchronization", () => {
  it("invalidates a displayed record after successful mutation", async () => {
    let value = 1;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, options?: RequestInit) => {
        if (options?.method === "POST") value = 2;
        return { ok: true, json: async () => ({ value }) };
      }),
    );
    render(<MutationFixture />, { wrapper });
    expect(await screen.findByText("Value: 1")).toBeVisible();
    fireEvent.click(screen.getByText("Update record"));
    await waitFor(() => expect(screen.getByText("Value: 2")).toBeVisible());
  });
});
