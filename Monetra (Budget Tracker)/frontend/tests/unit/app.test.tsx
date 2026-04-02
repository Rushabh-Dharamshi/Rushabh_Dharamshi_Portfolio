import { render, screen } from "@testing-library/react";
import React from "react";

import RootLayout from "@/app/layout";
import HomePage from "@/app/page";

jest.mock("@/components/budget-tracker-shell", () => ({
  BudgetTrackerShell: () => <div>Mock Budget Tracker Shell</div>,
}));

describe("app entrypoints", () => {
  it("renders the home page", () => {
    render(<HomePage />);
    expect(screen.getByText("Mock Budget Tracker Shell")).toBeInTheDocument();
  });

  it("renders the root layout", () => {
    const layout = RootLayout({ children: <div>Child content</div> });
    expect(React.isValidElement(layout)).toBe(true);
  });
});
