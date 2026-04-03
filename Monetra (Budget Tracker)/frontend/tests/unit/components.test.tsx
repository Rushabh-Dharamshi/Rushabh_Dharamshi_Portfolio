import { fireEvent, render, screen } from "@testing-library/react";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { AutomationCenter } from "@/components/automation-center";
import { DashboardSummaryCards } from "@/components/dashboard-summary";
import { ExpenseForm } from "@/components/expense-form";
import { ExpenseTable } from "@/components/expense-table";
import { FinancialPulse } from "@/components/financial-pulse";
import { InsightsPanel } from "@/components/insights-panel";
import { KpiVisuals } from "@/components/kpi-visuals";
import { OperationsPanel } from "@/components/operations-panel";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";
import { SpendingComparisonPanel } from "@/components/spending-comparison-panel";

const dashboard = {
  monthly_budget: 1050,
  current_month_total: 420,
  monthly_expenses: 420,
  monthly_income: 1500,
  net_cash_flow: 1080,
  remaining_budget: 630,
  weekly_spending: 84.5,
  percent_spent: 40,
  status: "within" as const,
  month_label: "March 2026",
  month_key: "2026-03",
  income_month: "2026-03",
};

describe("presentational components", () => {
  it("renders dashboard summary cards", () => {
    render(<DashboardSummaryCards summary={dashboard} />);

    expect(screen.getByText("March 2026")).toBeInTheDocument();
    expect(screen.getByText("Monthly income")).toBeInTheDocument();
    expect(screen.getByText("Net cash flow")).toBeInTheDocument();
  });

  it("renders the transaction form and forwards actions", () => {
    const onChange = jest.fn();
    const onCreate = jest.fn();
    const onUpdate = jest.fn();
    const onDelete = jest.fn();
    const onClear = jest.fn();

    render(
      <ExpenseForm
        form={{
          date: "2026-03-01",
          category: "Food",
          description: "Groceries",
          amount: "12.50",
          entry_type: "expense",
        }}
        selectedExpenseId={1}
        onChange={onChange}
        onCreate={onCreate}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onClear={onClear}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("Food"), { target: { value: "Travel" } });
    fireEvent.click(screen.getByText("Add expense"));
    fireEvent.click(screen.getByText("Update expense"));
    fireEvent.click(screen.getByText("Delete expense"));
    fireEvent.click(screen.getByText("Clear inputs"));

    expect(onChange).toHaveBeenCalled();
    expect(onCreate).toHaveBeenCalled();
    expect(onUpdate).toHaveBeenCalled();
    expect(onDelete).toHaveBeenCalled();
    expect(onClear).toHaveBeenCalled();
  });

  it("renders the expense table and selection/search controls", () => {
    const onSearchIdChange = jest.fn();
    const onSearch = jest.fn();
    const onShowAll = jest.fn();
    const onSelect = jest.fn();

    render(
      <ExpenseTable
        expenses={[
          {
            id: 1,
            date: "2026-03-01",
            category: "Food",
            description: "Groceries",
            amount: 20.5,
            entry_type: "expense",
          },
        ]}
        selectedExpenseId={1}
        searchId="1"
        onSearchIdChange={onSearchIdChange}
        onSearch={onSearch}
        onShowAll={onShowAll}
        onSelect={onSelect}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("1"), { target: { value: "2" } });
    fireEvent.click(screen.getByText("Search"));
    fireEvent.click(screen.getByText("Show all"));
    fireEvent.click(screen.getByText("Groceries"));

    expect(onSearchIdChange).toHaveBeenCalled();
    expect(onSearch).toHaveBeenCalled();
    expect(onShowAll).toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalled();
  });

  it("renders insights and word cloud data", () => {
    render(
      <InsightsPanel
        categories={{
          top_categories: [{ category: "Food", amount: 220 }],
          bottom_categories: [{ category: "Travel", amount: 80 }],
          total_spending: 300,
        }}
        wordCloud={{
          top_category: "Food",
          frequencies: [{ label: "Groceries", value: 220 }],
        }}
      />,
    );

    expect(screen.getByText("Top categories")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
  });

  it("renders operations, budget, and prediction controls", () => {
    const onImport = jest.fn();
    const onPredict = jest.fn();
    const onCheckBudget = jest.fn();
    const onBudgetDraftChange = jest.fn();
    const onIncomeDraftChange = jest.fn();
    const onIncomeMonthChange = jest.fn();
    const onSaveBudget = jest.fn();
    const onSaveIncome = jest.fn();

    render(
      <OperationsPanel
        summary={dashboard}
        prediction={{
          next_month: "April 2026",
          predicted_spending: 880,
          is_budget_exceeded: false,
          monthly_budget: 1050,
        }}
        exportUrl="/export"
        reportUrl="/report"
        budgetDraft="1050.00"
        incomeDraft="1500.00"
        incomeMonthDraft="2026-03"
        onImport={onImport}
        onPredict={onPredict}
        onCheckBudget={onCheckBudget}
        onBudgetDraftChange={onBudgetDraftChange}
        onIncomeDraftChange={onIncomeDraftChange}
        onIncomeMonthChange={onIncomeMonthChange}
        onSaveBudget={onSaveBudget}
        onSaveIncome={onSaveIncome}
      />,
    );

    const file = new File(["csv"], "import.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("Import CSV"), {
      target: { files: [file] },
    });
    fireEvent.change(screen.getByDisplayValue("1050.00"), { target: { value: "1200" } });
    fireEvent.change(screen.getByDisplayValue("2026-03"), { target: { value: "2026-04" } });
    fireEvent.change(screen.getByDisplayValue("1500.00"), { target: { value: "2400" } });
    fireEvent.click(screen.getByText("Save budget"));
    fireEvent.click(screen.getByText("Save income for month"));
    fireEvent.click(screen.getByText("Predict next month"));
    fireEvent.click(screen.getByText("Check budget status"));

    expect(onImport).toHaveBeenCalledWith(file);
    expect(onBudgetDraftChange).toHaveBeenCalled();
    expect(onIncomeDraftChange).toHaveBeenCalled();
    expect(onIncomeMonthChange).toHaveBeenCalled();
    expect(onSaveBudget).toHaveBeenCalled();
    expect(onSaveIncome).toHaveBeenCalled();
    expect(onPredict).toHaveBeenCalled();
    expect(onCheckBudget).toHaveBeenCalled();
  });

  it("renders financial pulse insights and recent activity", () => {
    render(
      <FinancialPulse
        pulse={{
          health_score: 81,
          average_transaction: 32.25,
          transaction_count: 12,
          spend_velocity: 18.1,
          top_category_share: 44.5,
          runway_days: 16.5,
          narrative: "Steady spending rhythm.",
          cash_in: 1500,
          cash_out: 420,
          net_cash_flow: 1080,
          income_coverage: 357.14,
          recent_transactions: [
            {
              id: 1,
              date: "2026-03-01",
              category: "Food",
              description: "Groceries",
              amount: 20.5,
              entry_type: "expense",
            },
          ],
          recent_expenses: [],
        }}
      />,
    );

    expect(screen.getByText("Financial pulse")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("16.5 days")).toBeInTheDocument();
  });

  it("renders KPI charts, comparison panel, and recurring calendar", () => {
    const expenses = [
      { id: 1, date: "2026-03-01", category: "Food", description: "Groceries", amount: 20.5, entry_type: "expense" as const },
      { id: 2, date: "2026-03-05", category: "Travel", description: "Train", amount: 35.0, entry_type: "expense" as const },
      { id: 3, date: "2026-02-05", category: "Bills", description: "Utilities", amount: 65.0, entry_type: "expense" as const },
      { id: 4, date: "2026-03-08", category: "Salary", description: "Payroll", amount: 1200, entry_type: "income" as const },
    ];

    const onCreate = jest.fn();
    const onUpdate = jest.fn();
    const onDelete = jest.fn();

    render(
      <>
        <KpiVisuals expenses={expenses} summary={dashboard} />
        <SpendingComparisonPanel expenses={expenses} referenceDate={new Date(2026, 2, 20)} />
        <RecurringCalendarPanel
          items={[
            {
              id: 1,
              category: "Housing",
              description: "Rent",
              amount: 700,
              entry_type: "expense",
              frequency: "monthly",
              start_date: "2026-03-01",
              active: true,
            },
          ]}
          calendar={{
            window_start: "2026-03-01",
            window_end: "2026-04-04",
            occurrences: [
              {
                recurring_item_id: 1,
                date: "2026-03-01",
                category: "Housing",
                description: "Rent",
                amount: 700,
                entry_type: "expense",
                frequency: "monthly",
                days_until_due: 0,
              },
            ],
            completed_occurrences: [],
          }}
          onCreate={onCreate}
          onUpdate={onUpdate}
          onDelete={onDelete}
          onMarkPaid={jest.fn()}
          onMarkUnpaid={jest.fn()}
        />
      </>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Category" }));
    fireEvent.click(screen.getByText("Add reminder"));

    expect(screen.getByText("Charts and performance signals")).toBeInTheDocument();
    expect(screen.getByText("Overlay spending comparison")).toBeInTheDocument();
    expect(screen.getByText("Upcoming bills and frequent purchases")).toBeInTheDocument();
    expect(onCreate).toHaveBeenCalled();
  });

  it("renders the local Ollama agent panel and forwards actions", () => {
    const onTaskDraftChange = jest.fn();
    const onRun = jest.fn();

    render(
      <AiAgentPanel
        taskDraft="Prepare a finance briefing"
        result={{
          headline: "Local finance briefing",
          summary: "Cash flow remains positive.",
          risk_level: "low",
          recommended_actions: ["Keep monitoring recurring bills."],
          email_subject: "Finance briefing",
          email_draft: "Monthly briefing attached.",
          task: "Prepare a finance briefing",
          model: "qwen3:4b",
          tools_used: ["get_dashboard_summary"],
          report_download_url: "/api/reports/monthly",
          generated_at: "2026-03-21T10:00:00Z",
        }}
        isRunning={false}
        onTaskDraftChange={onTaskDraftChange}
        onRun={onRun}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("Prepare a finance briefing"), {
      target: { value: "Update the briefing" },
    });
    fireEvent.click(screen.getByText("Run local agent"));

    expect(screen.getByText("Local Ollama analysis agent")).toBeInTheDocument();
    expect(screen.getByText("Email draft")).toBeInTheDocument();
    expect(onTaskDraftChange).toHaveBeenCalled();
    expect(onRun).toHaveBeenCalled();
  });

  it("renders the automation center and forwards workflow actions", () => {
    const onRunWorkflow = jest.fn();

    render(
      <AutomationCenter
        workflows={[
          {
            id: "month_end_close",
            label: "Month-end close",
            description: "Generate the monthly report and review KPIs.",
            automation_focus: "Automates month-end reporting.",
            default_task: "Run the workflow.",
          },
        ]}
        runs={[
          {
            id: 1,
            workflow_name: "month_end_close",
            workflow_label: "Month-end close",
            status: "completed",
            headline: "Month-end pack ready",
            summary: "The KPI pack has been refreshed.",
            risk_level: "low",
            recommended_actions: ["Share the pack with stakeholders."],
            automated_actions: ["Generated a fresh monthly PDF report for distribution."],
            email_subject: "Month-end pack ready",
            email_draft: "The report and summary are ready.",
            task: "Run the workflow.",
            model: "mistral:latest",
            tools_used: ["generate_monthly_report"],
            report_download_url: "/api/reports/monthly",
            generated_at: "2026-03-21T10:00:00Z",
          },
        ]}
        activeWorkflowName={null}
        onRunWorkflow={onRunWorkflow}
      />,
    );

    fireEvent.click(screen.getByText("Run workflow"));

    expect(screen.getByText("Agent workflows for repetitive finance tasks")).toBeInTheDocument();
    expect(screen.getByText("Recent workflow runs")).toBeInTheDocument();
    expect(onRunWorkflow).toHaveBeenCalledWith("month_end_close");
  });
});


