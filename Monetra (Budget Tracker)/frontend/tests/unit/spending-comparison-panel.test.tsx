import { fireEvent, render, screen } from "@testing-library/react";

import { SpendingComparisonPanel } from "@/components/spending-comparison-panel";

const sampleExpenses = [
  {
    id: 1,
    date: "2026-03-01",
    category: "Food",
    description: "Groceries",
    amount: 80,
    entry_type: "expense" as const,
  },
  {
    id: 2,
    date: "2026-02-15",
    category: "Food",
    description: "Dining",
    amount: 45,
    entry_type: "expense" as const,
  },
  {
    id: 3,
    date: "2026-01-10",
    category: "Travel",
    description: "Train",
    amount: 60,
    entry_type: "expense" as const,
  },
];

describe("SpendingComparisonPanel", () => {
  it("shows the category empty-state guidance when there are no expense rows", () => {
    render(<SpendingComparisonPanel expenses={[]} referenceDate={new Date(2026, 2, 21)} />);

    fireEvent.click(screen.getByRole("button", { name: "Category" }));

    expect(screen.getByText("Add expense transactions before switching to category comparisons.")).toBeInTheDocument();
  });

  it("supports switching between weekly and category comparison modes", () => {
    render(
      <SpendingComparisonPanel
        expenses={sampleExpenses}
        referenceDate={new Date(2026, 2, 21)}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Weekly" }));
    fireEvent.click(screen.getByRole("button", { name: "Category" }));

    expect(screen.getByLabelText("Category")).toBeInTheDocument();
    expect(screen.getByLabelText("Overlay spending comparison chart")).toBeInTheDocument();
  });

  it("lets the user drag the comparison window", () => {
    render(
      <SpendingComparisonPanel
        expenses={sampleExpenses}
        referenceDate={new Date(2026, 2, 21)}
      />,
    );

    fireEvent.change(screen.getByRole("slider"), { target: { value: "6" } });

    expect(screen.getByText("Drag to compare 6 months")).toBeInTheDocument();
  });
});
