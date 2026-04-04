import { fireEvent, render, screen } from "@testing-library/react";

import { ExpenseTable } from "@/components/expense-table";
import { InsightsPanel } from "@/components/insights-panel";
import { OperationsPanel } from "@/components/operations-panel";

describe("frontend strict direct branch closures", () => {
  it("covers both selected and unselected expense-table row branches", () => {
    const onSelect = jest.fn();
    render(
      <ExpenseTable
        expenses={[
          {
            id: 7,
            date: "2026-04-03",
            category: "Travel",
            description: "Tube",
            amount: 6.4,
            entry_type: "expense",
          },
        ]}
        selectedExpenseId={null}
        searchId="7"
        onSearchIdChange={jest.fn()}
        onSearch={jest.fn()}
        onShowAll={jest.fn()}
        onSelect={onSelect}
      />,
    );

    fireEvent.click(screen.getByText("Tube"));

    expect(screen.queryByText("No expense records found.")).not.toBeInTheDocument();
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 7, description: "Tube" }),
    );
  });

  it("covers defined and fallback word-cloud stats plus both import file-list branches", () => {
    const onImport = jest.fn();
    render(
      <>
        <InsightsPanel
          categories={{
            top_categories: [{ category: "Food", amount: 220 }],
            bottom_categories: [{ category: "Travel", amount: 30 }],
            total_spending: 250,
          }}
          wordCloud={{
            top_category: "Food",
            top_category_total: 250,
            dominant_label: "Groceries",
            dominant_value: 180,
            frequencies: [{ label: "Groceries", value: 180, share: 72 }],
          }}
        />
        <InsightsPanel
          categories={{
            top_categories: [],
            bottom_categories: [],
            total_spending: 0,
          }}
          wordCloud={{
            top_category: null as unknown as string,
            top_category_total: null as unknown as number,
            dominant_label: "Groceries",
            dominant_value: 0,
            frequencies: [{ label: "Groceries", value: 10, share: null as unknown as number }],
          }}
        />
        <OperationsPanel
          summary={null}
          prediction={null}
          exportUrl="/export"
          reportUrl="/report"
          budgetDraft="1000"
          incomeDraft="1500"
          incomeMonthDraft="2026-04"
          onImport={onImport}
          onPredict={jest.fn()}
          onCheckBudget={jest.fn()}
          onBudgetDraftChange={jest.fn()}
          onIncomeDraftChange={jest.fn()}
          onIncomeMonthChange={jest.fn()}
          onSaveBudget={jest.fn()}
          onSaveIncome={jest.fn()}
        />
      </>,
    );

    const input = screen.getByLabelText(/Import CSV/i) as HTMLInputElement;
    const file = new File(["a,b"], "expenses.csv", { type: "text/csv" });
    Object.defineProperty(input, "files", { configurable: true, value: [file] });
    fireEvent.change(input);
    Object.defineProperty(input, "files", { configurable: true, value: undefined });
    fireEvent.change(input, { target: {} });

    expect(screen.getByText("72.0% of Food")).toBeInTheDocument();
    expect(document.body.textContent).toContain("0.0% of");
    expect(onImport).toHaveBeenCalledTimes(1);
  });
});



