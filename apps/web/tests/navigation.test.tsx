import { it, expect, vi } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { Workspace } from "@/components/workspace";
vi.mock("next/navigation", () => ({ usePathname: () => "/compare" }));
it("exposes all twelve destinations and identifies the active screen", () => {
  render(
    <Workspace>
      <p>Evidence workspace</p>
    </Workspace>,
  );
  const nav = screen.getByRole("navigation", { name: "Main navigation" });
  const links = within(nav).getAllByRole("link");
  expect(links).toHaveLength(12);
  expect(
    within(nav).getByRole("link", { name: "Comparison studio" }),
  ).toHaveAttribute("aria-current", "page");
  expect(links.map((a) => a.getAttribute("href"))).toEqual([
    "/",
    "/models",
    "/agents",
    "/benchmarks",
    "/experiments/new",
    "/experiments",
    "/compare",
    "/replay",
    "/optimize",
    "/reports",
    "/settings",
    "/docs",
  ]);
});
it("opens an accessible mobile navigation sheet", () => {
  render(
    <Workspace>
      <p>Evidence workspace</p>
    </Workspace>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
  expect(screen.getByRole("dialog")).toHaveAccessibleName(
    "Workspace navigation",
  );
  const dialog = screen.getByRole("dialog");
  expect(
    within(dialog).getByRole("link", { name: "Execution replay" }),
  ).toHaveAttribute("href", "/replay");
  // jsdom has no document navigation; this test verifies the sheet close state.
  dialog.addEventListener("click", (event) => event.preventDefault(), {
    once: true,
  });
  fireEvent.click(
    within(dialog).getByRole("link", { name: "Execution replay" }),
  );
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
