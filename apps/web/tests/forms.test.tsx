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
