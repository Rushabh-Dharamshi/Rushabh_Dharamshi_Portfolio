import { fireEvent, render, screen } from "@testing-library/react";

import { AutomationCenter } from "@/components/automation-center";
import { BudgetTrackerShell } from "@/components/budget-tracker-shell";
import { FinancialPulse } from "@/components/financial-pulse";
import { InsightsPanel } from "@/components/insights-panel";
import { OperationsPanel } from "@/components/operations-panel";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";
import { SpendingComparisonPanel } from "@/components/spending-comparison-panel";

const mockUseBudgetTracker = jest.fn();

jest.mock("@/hooks/use-budget-tracker", () => ({
  useBudgetTracker: () => mockUseBudgetTracker(),
}));

describe("frontend strict branch fill", () => {
  beforeEach(() => {
    mockUseBudgetTracker.mockReset();
  });

  it("covers active shell selection branches", () => {
    mockUseBudgetTracker.mockReturnValue({
      allExpenses: [],
      expenses: [],
      selectedExpense: { id: 42 },
      form: { date: "", category: "", description: "", amount: "", entry_type: "expense" },
      dashboard: {
        monthly_budget: 1050,
        current_month_total: 420,
        monthly_expenses: 420,
        monthly_income: 1500,
        net_cash_flow: 1080,
        remaining_budget: 630,
        weekly_spending: 84.5,
        percent_spent: 40,
        status: "within",
        month_label: "March 2026",
        month_key: "2026-03",
        income_month: "2026-03",
      },
      categoryInsights: null,
      wordCloud: null,
      financialPulse: null,
      recurringItems: [],
      recurringCalendar: { window_start: "2026-03-01", window_end: "2026-04-04", occurrences: [], completed_occurrences: [] },
      prediction: null,
      agentTaskDraft: "task",
      agentBriefing: null,
      agentWorkflows: [],
      agentRuns: [],
      isAgentRunning: false,
      isBootstrappingAutomation: false,
      activeWorkflowName: null,
      activeEmailDispatchId: null,
      searchId: "42",
      budgetDraft: "1050.00",
      incomeDraft: "1500.00",
      incomeMonthDraft: "2026-03",
      statusMessage: null,
      errorMessage: null,
      isLoading: false,
      exportUrl: "/export",
      reportUrl: "/report",
      setForm: jest.fn(),
      setSearchId: jest.fn(),
      setBudgetDraft: jest.fn(),
      setIncomeDraft: jest.fn(),
      setIncomeMonthDraft: jest.fn(),
      setAgentTaskDraft: jest.fn(),
      selectExpense: jest.fn(),
      resetForm: jest.fn(),
      createExpense: jest.fn(),
      updateExpense: jest.fn(),
      deleteExpense: jest.fn(),
      searchExpenseById: jest.fn(),
      showAllRecords: jest.fn(),
      importExpenses: jest.fn(),
      predictNextMonth: jest.fn(),
      checkBudgetStatus: jest.fn(),
      saveMonthlyBudget: jest.fn(),
      saveMonthlyIncome: jest.fn(),
      createRecurringItem: jest.fn(),
      updateRecurringItem: jest.fn(),
      deleteRecurringItem: jest.fn(),
      markRecurringOccurrencePaid: jest.fn(),
      markRecurringOccurrenceUnpaid: jest.fn(),
      runFinanceBriefingAgent: jest.fn(),
      runAutomationWorkflow: jest.fn(),
      sendUpcomingBillsEmailNow: jest.fn(),
      sendMonthEndEmailNow: jest.fn(),
      refresh: jest.fn(),
    });

    render(<BudgetTrackerShell />);

    expect(screen.getByText("Expense records")).toBeInTheDocument();
  });

  it("covers automation high-risk, pulse income rows, and rich insights branches", () => {
    render(
      <>
        <AutomationCenter
          workflows={[{ id: "month_end_close", label: "Month-end close", description: "desc", automation_focus: "focus", default_task: "run" }]}
          runs={[{
            id: 1,
            workflow_name: "month_end_close",
            workflow_label: "Month-end close",
            status: "completed",
            headline: "done",
            summary: "sent",
            risk_level: "high",
            recommended_actions: [],
            automated_actions: ["Generated PDF"],
            email_subject: "subject",
            email_draft: "draft",
            task: "run",
            model: "qwen",
            tools_used: ["generate_monthly_report"],
            report_download_url: null,
            generated_at: "2026-04-03T12:00:00Z",
          }]}
          activeWorkflowName={null}
          liveStatusMessage={null}
          onRunWorkflow={jest.fn()}
        />
        <FinancialPulse
          pulse={{
            health_score: 90,
            average_transaction: 25,
            transaction_count: 1,
            spend_velocity: 12,
            top_category_share: 44,
            runway_days: 9,
            narrative: "Steady",
            cash_in: 1000,
            cash_out: 400,
            net_cash_flow: 600,
            income_coverage: 250,
            recent_transactions: [{ id: 9, description: "Salary", category: "Income", date: "2026-04-01", amount: 1200, entry_type: "income" }],
            recent_expenses: [],
          }}
        />
        <InsightsPanel
          categories={{ top_categories: [], bottom_categories: [], total_spending: 0 }}
          wordCloud={{
            top_category: null,
            top_category_total: 0,
            dominant_label: "Groceries",
            dominant_value: undefined,
            frequencies: [{ label: "Groceries", value: 220 }],
          }}
        />
      </>,
    );

    expect(screen.queryByText("high risk")).not.toBeInTheDocument();
    expect(screen.getByText((value) => value.includes("1,200.00"))).toBeInTheDocument();
    expect(screen.getByText("9 days")).toBeInTheDocument();
    expect(screen.getAllByText((value) => value.includes("0.00")).length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Description word cloud for top category")).toBeInTheDocument();
  });

  it("covers operations no-file branch and over-budget prediction branch", () => {
    const onImport = jest.fn();
    render(
      <OperationsPanel
        summary={null}
        prediction={{ next_month: "May 2026", predicted_spending: 1200, is_budget_exceeded: true, monthly_budget: 1000 }}
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
      />,
    );

    fireEvent.change(screen.getByLabelText(/Import CSV/i), { target: { files: [] } });
    expect(onImport).not.toHaveBeenCalled();
    expect(screen.getByText("Forecast exceeds the budget threshold.")).toBeInTheDocument();
  });

  it("covers category comparison empty-state branch", () => {
    render(<SpendingComparisonPanel expenses={[]} referenceDate={new Date(2026, 3, 3)} />);
    fireEvent.click(screen.getByRole("button", { name: "Category" }));
    expect(screen.getByText("Add expense transactions before switching to category comparisons.")).toBeInTheDocument();
  });

  it("covers recurring planner validation and completed-occurrence text branches", () => {
    const onMarkPaid = jest.fn();
    render(
      <RecurringCalendarPanel
        items={[
          { id: 1, category: "Bills", description: "Alpha", amount: 10, entry_type: "expense", frequency: "monthly", start_date: "2026-04-02", end_date: null, active: false },
          { id: 2, category: "Bills", description: "Beta", amount: 10, entry_type: "expense", frequency: "monthly", start_date: "2026-04-02", end_date: "2026-06-02", active: true },
        ]}
        calendar={{
          window_start: "2026-03-31",
          window_end: "2026-05-04",
          occurrences: [
            { recurring_item_id: 2, date: "2026-04-02", category: "Bills", description: "Beta", amount: 10, entry_type: "expense", frequency: "monthly", days_until_due: 1 },
            { recurring_item_id: 1, date: "2026-04-02", category: "Bills", description: "Alpha", amount: 10, entry_type: "expense", frequency: "monthly", days_until_due: 2 },
          ],
          completed_occurrences: [
            { recurring_item_id: 1, date: "2026-04-01", category: "Bills", description: "Alpha", amount: 10, entry_type: "expense", frequency: "monthly", days_until_due: 0, transaction_id: null },
          ],
        }}
        onCreate={jest.fn()}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
        onMarkPaid={onMarkPaid}
        onMarkUnpaid={jest.fn()}
      />,
    );

    fireEvent.click(screen.getAllByText("Verify and mark paid")[0]);
    expect(onMarkPaid).not.toHaveBeenCalled();
    expect(screen.getByText("Bills | monthly | due in 1 day")).toBeInTheDocument();
    expect(screen.getByText("Bills | cleared for 2026-04-01")).toBeInTheDocument();
  });
});

