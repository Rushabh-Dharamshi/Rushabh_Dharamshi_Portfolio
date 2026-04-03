import { render, screen, waitFor } from "@testing-library/react";
import React from "react";

import RootLayout from "@/app/layout";
import HomePage from "@/app/page";
import { apiClient } from "@/lib/api-client";

jest.mock("@/components/budget-tracker-shell", () => ({
  BudgetTrackerShell: () => <div>Mock Budget Tracker Shell</div>,
}));

describe("app entrypoints", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("renders the home page", async () => {
    jest.spyOn(apiClient, "getAuthSession").mockResolvedValue({
      authenticated: true,
      username: "Rushabh",
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Mock Budget Tracker Shell")).toBeInTheDocument();
    });
  });

  it("renders the root layout", () => {
    const layout = RootLayout({ children: <div>Child content</div> });
    expect(React.isValidElement(layout)).toBe(true);
  });
});
