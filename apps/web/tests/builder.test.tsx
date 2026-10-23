import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { Builder } from "@/components/builder";
import { agentDefaults, modelDefaults } from "@/components/registry";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams("agent=native-agent&mode=native"),
}));

it("keeps native product settings separate from controlled model pairing", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) => ({
      ok: true,
      json: async () =>
        path.endsWith("/models")
          ? [
              {
                id: "model-1",
                config: {
                  ...modelDefaults,
                  name: "Registered model",
                  model: "model",
                },
              },
            ]
          : path.endsWith("/agents")
            ? [
                {
                  id: "native-agent",
                  config: {
                    ...agentDefaults,
                    name: "Native product",
                    native: true,
                  },
                },
                {
                  id: "controlled-agent",
                  config: {
                    ...agentDefaults,
                    name: "Controlled harness",
                    native: false,
                  },
                },
              ]
            : path.endsWith("/benchmarks")
              ? [{ id: "starter-v1", name: "Starter", version: "1" }]
              : { id: "starter-v1", name: "Starter", version: "1", tasks: [] },
    })),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <Builder />
    </QueryClientProvider>,
  );
  expect(await screen.findByLabelText(/Native product/)).toBeChecked();
  expect(screen.getByLabelText("Evaluation mode")).toHaveValue("native");
  expect(
    screen.queryByLabelText("Shared model for agent evaluation"),
  ).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/Controlled harness/)).not.toBeInTheDocument();
  expect(
    screen.getByText(
      /Native products use their own model and provider settings/,
    ),
  ).toBeVisible();
  fireEvent.change(screen.getByLabelText("Evaluation mode"), {
    target: { value: "agent" },
  });
  expect(
    screen.getByLabelText("Shared model for agent evaluation"),
  ).toBeVisible();
  expect(screen.getByLabelText(/Controlled harness/)).not.toBeChecked();
  expect(screen.queryByLabelText(/Native product/)).not.toBeInTheDocument();
});
