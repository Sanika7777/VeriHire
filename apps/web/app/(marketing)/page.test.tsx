import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MarketingHomePage from "./page";

describe("MarketingHomePage", () => {
  it("renders the primary headline", () => {
    render(<MarketingHomePage />);
    expect(
      screen.getByRole("heading", {
        name: /know who's hiring you before you send a single reply/i,
      }),
    ).toBeInTheDocument();
  });
});
