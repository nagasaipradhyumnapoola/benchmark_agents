import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { Community } from "@/components/community";

const proposal = {
  id: "draft-one",
  kind: "agent",
  title: "Open agent",
  description: "Try repository editing tasks.",
  author_name: null,
  source_url: "https://github.com/example/agent",
  license: "MIT",
  recommended_models: ["provider/exact-model"],
  benchmark_ids: [],
  evidence_url: null,
  created_at: "2026-10-23T00:00:00Z",
  publication_status: "local_draft",
  verification_status: "unverified",
  share_body: "Community proposal (unverified recommendation). Open agent",
  share_url:
    "https://github.com/nagasaipradhyumnapoola/benchmark_agents/issues/new?title=Open+agent",
  share_requires_paste: false,
};

function mount(drafts: (typeof proposal)[] = []) {
  const bodies: unknown[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_path: string, options?: RequestInit) => {
      if (options?.method === "POST") {
        const body = JSON.parse(String(options.body));
        bodies.push(body);
        drafts = [{ ...proposal, ...body }];
        return { ok: true, json: async () => drafts[0] };
      }
      return {
        ok: true,
        json: async () => ({
          published: [],
          drafts,
          repository_url:
            "https://github.com/nagasaipradhyumnapoola/benchmark_agents",
          public_issues_url:
            "https://github.com/nagasaipradhyumnapoola/benchmark_agents/issues",
          contribution_docs_url:
            "https://github.com/nagasaipradhyumnapoola/benchmark_agents/blob/main/docs/community.md",
          publication_note:
            "Drafts stay on this machine until you review and submit a GitHub issue yourself.",
        }),
      };
    }),
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <Community />
    </QueryClientProvider>,
  );
  return bodies;
}

it("saves exact model recommendations as local metadata and requires review before GitHub sharing", async () => {
  const bodies = mount();
  expect(
    await screen.findByText("No published recommendations yet"),
  ).toBeVisible();
  fireEvent.change(screen.getByLabelText("Title"), {
    target: { value: "Open agent" },
  });
  fireEvent.change(screen.getByLabelText("Description"), {
    target: { value: "Try repository editing tasks." },
  });
  fireEvent.change(screen.getByLabelText("Public source URL"), {
    target: { value: "https://github.com/example/agent" },
  });
  fireEvent.change(screen.getByLabelText("License"), {
    target: { value: "MIT" },
  });
  fireEvent.change(
    screen.getByLabelText("Suggested models (one exact model name per line)"),
    { target: { value: "provider/exact-model\nprovider/other-model" } },
  );
  expect(
    screen.queryByRole("link", { name: /Open GitHub/ }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save local draft" }));
  await waitFor(() =>
    expect(bodies).toEqual([
      {
        kind: "agent",
        title: "Open agent",
        description: "Try repository editing tasks.",
        author_name: null,
        source_url: "https://github.com/example/agent",
        license: "MIT",
        recommended_models: ["provider/exact-model", "provider/other-model"],
        benchmark_ids: [],
        evidence_url: null,
      },
    ]),
  );
  expect(
    await screen.findByText("Open agent", { selector: "h3" }),
  ).toBeVisible();
  expect(screen.getByText("Local draft · unverified")).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Download contribution JSON" }),
  ).toHaveAttribute("href", "/api/community/draft-one/export");
  fireEvent.click(
    screen.getByRole("button", { name: "Review GitHub submission" }),
  );
  expect(
    screen.getByRole("region", { name: "GitHub issue preview" }),
  ).toHaveTextContent("unverified recommendation");
  const open = screen.getByRole("link", {
    name: "Open GitHub to submit yourself",
  });
  expect(open).toHaveAttribute("href", proposal.share_url);
  expect(open).toHaveAttribute("rel", "noopener noreferrer");
});

it("filters drafts and makes source and license optional for benchmark suggestions", async () => {
  mount([proposal]);
  expect(
    await screen.findByText("Open agent", { selector: "h3" }),
  ).toBeVisible();
  fireEvent.change(screen.getByLabelText("Search community suggestions"), {
    target: { value: "no matching agent" },
  });
  expect(
    screen.queryByText("Open agent", { selector: "h3" }),
  ).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Suggestion type"), {
    target: { value: "benchmark" },
  });
  expect(screen.getByLabelText("Public source URL")).not.toBeRequired();
  expect(screen.getByLabelText("License")).not.toBeRequired();
});

it("explains how to submit an oversized draft without truncating its review", async () => {
  const fullBody = "界".repeat(6500);
  mount([{ ...proposal, share_requires_paste: true, share_body: fullBody }]);
  await screen.findByText("Open agent", { selector: "h3" });
  fireEvent.click(
    screen.getByRole("button", { name: "Review GitHub submission" }),
  );
  expect(
    screen.getByText(/Copy and paste the full review body below/),
  ).toBeVisible();
  expect(screen.getByText(/download the contribution JSON/)).toBeVisible();
  expect(
    screen.getByRole("region", { name: "GitHub issue preview" }),
  ).toHaveTextContent(fullBody);
  expect(
    screen.getByRole("link", { name: "Open GitHub to submit yourself" }),
  ).toHaveAttribute("href", proposal.share_url);
});
