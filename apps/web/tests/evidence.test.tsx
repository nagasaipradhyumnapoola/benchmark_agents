import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { JsonView } from "@/components/common";

describe("evidence inspector keyboard access", () => {
  it("makes scrollable evidence focusable and leaves hostile text inert", () => {
    render(
      <JsonView
        value={{ output: '<script>throw new Error("unsafe")</script>' }}
      />,
    );
    const region = screen.getByRole("region", { name: "JSON evidence" });
    region.focus();
    expect(region).toHaveFocus();
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region.querySelector("script")).toBeNull();
    expect(region).toHaveTextContent("<script>");
  });
});
