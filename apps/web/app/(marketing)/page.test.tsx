import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MarketingHomePage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// HomeStats is a genuine async Server Component (real DB-backed data
// fetching via server-only) — @testing-library/react's client renderer
// can't execute that RSC boundary, so this unit test isolates the static
// page shell and leaves HomeStats to the Playwright/manual e2e coverage.
vi.mock("./home-stats", () => ({
  HomeStats: () => null,
}));

describe("MarketingHomePage", () => {
  it("renders the primary headline", () => {
    render(<MarketingHomePage />);
    expect(
      screen.getByRole("heading", {
        name: /know who's hiring you before you send a single reply/i,
      }),
    ).toBeInTheDocument();
  });

  it("renders the link-verification input", () => {
    render(<MarketingHomePage />);
    expect(
      screen.getByPlaceholderText(/paste a job link, recruiter profile, or company url/i),
    ).toBeInTheDocument();
  });
});
