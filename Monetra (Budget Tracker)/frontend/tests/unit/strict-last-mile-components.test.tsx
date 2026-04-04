import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { ExpenseTable } from "@/components/expense-table";
import { InsightsPanel } from "@/components/insights-panel";
import { KpiVisuals } from "@/components/kpi-visuals";
import { OperationsPanel } from "@/components/operations-panel";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";

describe("frontend strict last-mile component coverage", () => {
  afterEach(() => {
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  it("covers empty expense-table state, import optional chaining, and AI string fallbacks", () => {
    const originalFilter = Array.prototype.filter;
    const filterSpy = jest
      .spyOn(Array.prototype, "filter")
      .mockImplementation(function mockFilter<T>(
        this: T[],
        predicate: (value: T, index: number, array: T[]) => unknown,
        thisArg?: unknown,
      ) {
        if (
          predicate === Boolean &&
          this.length === 1 &&
          this[0] === "Fallback summary"
        ) {
          return [] as T[];
        }
        return originalFilter.call(this, predicate, thisArg);
      });

    const onImport = jest.fn();

    render(
      <>
        <ExpenseTable
          expenses={[]}
          selectedExpenseId={null}
          searchId=""
          onSearchIdChange={jest.fn()}
          onSearch={jest.fn()}
          onShowAll={jest.fn()}
          onSelect={jest.fn()}
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
        <AiAgentPanel
          taskDraft="close the month"
          isRunning={false}
          onTaskDraftChange={jest.fn()}
          onRun={jest.fn()}
          result={{
            headline: "month end",
            summary: "Fallback summary",
            risk_level: "low",
            recommended_actions: ["   "],
            email_subject: "month end close",
            email_draft: "",
            task: "close the month",
            model: "qwen",
            tools_used: [],
            report_download_url: null,
            generated_at: "2026-04-03T22:00:00Z",
            trace: {
              memory: [],
              plan: {
                intent: "",
                success_criteria: ["  keep runway healthy  "],
                steps: [],
              },
              execution_results: [],
              repair_attempts: 0,
              verification: {
                headline: "verified",
                summary: "verified summary",
                risk_level: "low",
              },
            },
          }}
        />
      </>,
    );

    fireEvent.change(screen.getByLabelText(/Import CSV/i), {
      target: { files: undefined },
    });

    expect(screen.getByText("No expense records found.")).toBeInTheDocument();
    expect(onImport).not.toHaveBeenCalled();
    expect(screen.getByText("Fallback summary.")).toBeInTheDocument();
    expect(screen.getByText("Keep runway healthy.")).toBeInTheDocument();

    filterSpy.mockRestore();
  });

  it("covers word-cloud fallbacks, zero-share KPI output, and recurring month tie ordering", () => {
    jest.useFakeTimers().setSystemTime(new Date("2026-04-18T12:00:00Z"));
    const originalMap = Array.prototype.map;
    const mapSpy = jest
      .spyOn(Array.prototype, "map")
      .mockImplementation(function mockMap<T, U>(
        this: T[],
        callback: (value: T, index: number, array: T[]) => U,
        thisArg?: unknown,
      ) {
        if (
          this.length === 4 &&
          typeof this[0] === "object" &&
          this[0] !== null &&
          "label" in (this[0] as object) &&
          (this[0] as { label?: string }).label === "Week 1" &&
          (this[3] as { label?: string } | undefined)?.label === "Week 4+"
        ) {
          return [] as U[];
        }
        return originalMap.call(this, callback, thisArg);
      });

    const { container } = render(
      <>
        <InsightsPanel
          categories={{
            top_categories: [],
            bottom_categories: [],
            total_spending: 0,
          }}
          wordCloud={{
            top_category: undefined as unknown as string,
            top_category_total: undefined as unknown as number,
            dominant_label: "Groceries",
            dominant_value: 0,
            frequencies: [{ label: "Groceries", value: 220 }],
          }}
        />
        <KpiVisuals
          summary={{
            monthly_budget: 1000,
            current_month_total: 0,
            monthly_expenses: 0,
            monthly_income: 1500,
            net_cash_flow: 1500,
            remaining_budget: 1000,
            weekly_spending: 0,
            percent_spent: 0,
            status: "within",
            month_label: "April 2026",
            month_key: "2026-04",
            income_month: "2026-04",
          }}
          expenses={[
            {
              id: 1,
              date: "2026-04-02",
              category: "Zero",
              description: "Zero amount",
              amount: 0,
              entry_type: "expense",
            },
          ]}
        />
        <RecurringCalendarPanel
          items={[
            {
              id: 1,
              category: "Bills",
              description: "Open End",
              amount: 12,
              entry_type: "expense",
              frequency: "monthly",
              start_date: "2026-04-03",
              end_date: null,
              active: true,
            },
            {
              id: 2,
              category: "Bills",
              description: "Zulu",
              amount: 10,
              entry_type: "expense",
              frequency: "monthly",
              start_date: "2026-04-15",
              end_date: "2026-04-15",
              active: true,
            },
            {
              id: 3,
              category: "Bills",
              description: "Alpha",
              amount: 10,
              entry_type: "expense",
              frequency: "monthly",
              start_date: "2026-04-15",
              end_date: "2026-04-15",
              active: true,
            },
          ]}
          calendar={{
            window_start: "2026-04-01",
            window_end: "2026-05-06",
            occurrences: [],
            completed_occurrences: [],
          }}
          onCreate={jest.fn()}
          onUpdate={jest.fn()}
          onDelete={jest.fn()}
          onMarkPaid={jest.fn()}
          onMarkUnpaid={jest.fn()}
        />
      </>,
    );

    expect(
      screen.getByLabelText("Description word cloud for top category"),
    ).toBeInTheDocument();
    expect(screen.getAllByText((value) => value.includes("0.00")).length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        "Weekly comparisons will appear once current-month expenses are available.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText((value) => value.includes("0.0") && value.includes("%") && value.includes("0.00"))).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Open End/i }));
    expect(screen.getByLabelText("End date (optional)")).toHaveValue("");

    const monthBreakdownNames = Array.from(
      container.querySelectorAll(".month-breakdown-row strong"),
    ).map((node) => node.textContent);
    expect(monthBreakdownNames.indexOf("Alpha")).toBeLessThan(
      monthBreakdownNames.indexOf("Zulu"),
    );

    mapSpy.mockRestore();
  });
});



