import { fireEvent, render, screen } from "@testing-library/react";

import { BudgetTrackerShell } from "@/components/budget-tracker-shell";

const mockUseBudgetTracker = jest.fn();

jest.mock("@/hooks/use-budget-tracker", () => ({
  useBudgetTracker: () => mockUseBudgetTracker(),
}));

jest.mock("@/components/automation-center", () => ({
  AutomationCenter: ({ liveStatusMessage }: { liveStatusMessage: string | null }) => (
    <div>Automation center mock{liveStatusMessage ? `: ${liveStatusMessage}` : ""}</div>
  ),
}));
jest.mock("@/components/dashboard-summary", () => ({ DashboardSummaryCards: () => <div>Summary cards mock</div> }));
jest.mock("@/components/expense-form", () => ({ ExpenseForm: () => <div>Expense form mock</div> }));
jest.mock("@/components/operations-panel", () => ({ OperationsPanel: () => <div>Operations panel mock</div> }));
jest.mock("@/components/recurring-calendar-panel", () => ({ RecurringCalendarPanel: () => <div>Recurring panel mock</div> }));
jest.mock("@/components/ai-agent-panel", () => ({ AiAgentPanel: () => <div>AI panel mock</div> }));
jest.mock("@/components/rag-qa-panel", () => ({ RagQaPanel: () => <div>RAG panel mock</div> }));
jest.mock("@/components/kpi-visuals", () => ({ KpiVisuals: () => <div>KPI visuals mock</div> }));
jest.mock("@/components/financial-pulse", () => ({ FinancialPulse: () => <div>Pulse mock</div> }));
jest.mock("@/components/expense-table", () => ({ ExpenseTable: () => <div>Expense table mock</div> }));
jest.mock("@/components/spending-comparison-panel", () => ({ SpendingComparisonPanel: () => <div>Comparison mock</div> }));
jest.mock("@/components/insights-panel", () => ({ InsightsPanel: () => <div>Insights mock</div> }));

const baseTracker = {
  allExpenses: [],
  expenses: [],
  selectedExpense: null,
  form: { date: "", category: "", description: "", amount: "", entry_type: "expense" as const },
  dashboard: {
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
  },
  categoryInsights: null,
  wordCloud: null,
  financialPulse: null,
  recurringItems: [],
  recurringCalendar: null,
  prediction: null,
  ragQuestionDraft: "question",
  ragAnswer: null,
  ragStatus: { available: true, collection_name: "monetra-finance-knowledge", indexed_at: "2026-04-15T09:00:00Z", document_count: 12, chunk_count: 36, signature: "sig" },
  agentTaskDraft: "task",
  agentBriefing: null,
  agentWorkflows: [],
  agentRuns: [],
  isAgentRunning: false,
  isRagQueryRunning: false,
  isRagReindexing: false,
  isBootstrappingAutomation: false,
  activeWorkflowName: null,
  activeEmailDispatchId: null,
  searchId: "",
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
  setRagQuestionDraft: jest.fn(),
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
  runRagQuery: jest.fn(),
  reindexRagKnowledge: jest.fn(),
  runFinanceBriefingAgent: jest.fn(),
  runAutomationWorkflow: jest.fn(),
  sendUpcomingBillsEmailNow: jest.fn(),
  sendMonthEndEmailNow: jest.fn(),
  refresh: jest.fn(),
};

describe("BudgetTrackerShell unit coverage", () => {
  beforeEach(() => {
    mockUseBudgetTracker.mockReset();
    mockUseBudgetTracker.mockReturnValue(baseTracker);
  });

  it("renders hero stats, messages, and logout", () => {
    const onLogout = jest.fn();
    mockUseBudgetTracker.mockReturnValue({
      ...baseTracker,
      errorMessage: "Backend unavailable.",
      statusMessage: "Refreshed successfully.",
    });

    render(<BudgetTrackerShell username="Owner" onLogout={onLogout} />);

    expect(screen.getByText("Signed in as Owner")).toBeInTheDocument();
    expect(screen.getByText("GBP-native finance tracking")).toBeInTheDocument();
    expect(screen.getByText("RAG panel mock")).toBeInTheDocument();
    expect(screen.getByText((value) => value.includes("1,050.00"))).toBeInTheDocument();
    expect(screen.getByText("Backend unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Refreshed successfully.")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Sign out"));
    expect(onLogout).toHaveBeenCalled();
  });

  it("renders fallback hero values and loading state without logout", () => {
    mockUseBudgetTracker.mockReturnValue({
      ...baseTracker,
      dashboard: null,
      isLoading: true,
    });

    render(<BudgetTrackerShell />);

    expect(screen.getAllByText("--")).toHaveLength(3);
    expect(screen.getByText("loading")).toBeInTheDocument();
    expect(screen.getByText("Loading budget data...")).toBeInTheDocument();
    expect(screen.queryByText("Sign out")).not.toBeInTheDocument();
  });

  it("passes the active workflow live status into the automation panel", () => {
    mockUseBudgetTracker.mockReturnValue({
      ...baseTracker,
      activeWorkflowName: "month_end_close",
      statusMessage: "month end close is running through the local agent pipeline. Elapsed: 4s.",
    });

    render(<BudgetTrackerShell />);

    expect(screen.getByText("Automation center mock: month end close is running through the local agent pipeline. Elapsed: 4s.")).toBeInTheDocument();
  });
});
