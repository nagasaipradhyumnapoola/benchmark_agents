import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { Overview } from "@/components/overview";
import type { Overview as OverviewData } from "@/lib/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function renderOverview(data: OverviewData) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => data })),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <Overview />
    </QueryClientProvider>,
  );
}

it("guides an empty workspace through real setup without synthetic results or a demo action", async () => {
  renderOverview({
    models: [],
    agents: [],
    experiments: [],
    runs: [],
    metrics: { total: 0, passed: 0, success_rate: null },
    recent_failures: [],
  });
  expect(
    await screen.findByRole("heading", {
      name: "Set up your first experiment",
    }),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: "Register model" })).toHaveAttribute(
    "href",
    "/models",
  );
  expect(screen.getByRole("link", { name: "Register agent" })).toHaveAttribute(
    "href",
    "/agents",
  );
  expect(
    screen.getByRole("link", { name: "Build experiment" }),
  ).toHaveAttribute("href", "/experiments/new");
  expect(screen.getByText("uv run bench-agents terminal")).toBeVisible();
  expect(screen.getByRole("link", { name: "Terminal setup" })).toHaveAttribute(
    "href",
    "/docs#terminal",
  );
  expect(
    screen.getByRole("heading", { name: "Experiment activity" }),
  ).toBeVisible();
  expect(screen.getByText("No active jobs")).toBeVisible();
  expect(screen.queryByText("Verified success")).not.toBeInTheDocument();
  expect(screen.queryByText("Median latency")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /demonstration/i }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

it("keeps persisted experiment outcomes visible after setup", async () => {
  renderOverview({
    models: [],
    agents: [],
    experiments: [
      {
        id: "experiment-1",
        name: "Measured endpoint",
        mode: "model",
        status: "completed",
        demo: false,
        created_at: "2026-10-23T00:00:00Z",
        config: {} as never,
      },
    ],
    runs: [],
    metrics: {
      total: 2,
      passed: 1,
      success_rate: 0.5,
      median_latency_seconds: 1.2,
    },
    recent_failures: [],
  });
  expect(
    await screen.findByRole("link", { name: "Measured endpoint" }),
  ).toHaveAttribute("href", "/experiments?id=experiment-1");
  expect(screen.getByText("50.0%")).toBeVisible();
  expect(screen.getByText("1 / 2")).toBeVisible();
  expect(
    screen.queryByRole("heading", { name: "Set up your first experiment" }),
  ).not.toBeInTheDocument();
});
