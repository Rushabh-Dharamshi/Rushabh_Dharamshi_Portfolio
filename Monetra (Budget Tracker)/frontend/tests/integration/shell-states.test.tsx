import { render, screen } from "@testing-library/react";

import { BudgetTrackerShell } from "@/components/budget-tracker-shell";

const baseTrackerState: any = {
  allExpenses: [],
  expenses: [],
  selectedExpense: null,
  form: { date: "", category: "", description: "", amount: "", entry_type: "expense" as const },
  dashboard: null,
  categoryInsights: null,
  wordCloud: null,
  financialPulse: null,
  recurringItems: [],
  recurringCalendar: null,
  prediction: null,
  latencyReport: {
    scope: "current_user",
    record_count: 0,
    failed_count: 0,
    summary: { average_ms: 0, minimum_ms: 0, maximum_ms: 0, p95_ms: 0 },
    by_endpoint: [],
    latest: [],
  },
  agentTaskDraft: "Prepare a finance briefing",
  agentWorkflows: [],
  agentRuns: [],
  agentBriefing: null,
  isAgentRunning: false,
  activeWorkflowName: null,
  searchId: "",
  budgetDraft: "",
  incomeDraft: "",
  statusMessage: null,
  errorMessage: null,
  isLoading: false,
  exportUrl: "/export",
  reportUrl: "/report",
  setForm: jest.fn(),
  setSearchId: jest.fn(),
  setBudgetDraft: jest.fn(),
  setIncomeDraft: jest.fn(),
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
  refresh: jest.fn(),
  refreshLatencyReport: jest.fn(),
};

const mockUseBudgetTracker = jest.fn(() => baseTrackerState);

jest.mock("@/hooks/use-budget-tracker", () => ({
  useBudgetTracker: () => mockUseBudgetTracker(),
}));

describe("BudgetTrackerShell state coverage", () => {
  afterEach(() => {
    mockUseBudgetTracker.mockReset();
    mockUseBudgetTracker.mockImplementation(() => baseTrackerState);
  });

  it("shows the loading state during initial fetch", () => {
    mockUseBudgetTracker.mockReturnValue({
      ...baseTrackerState,
      isLoading: true,
    });

    render(<BudgetTrackerShell />);

    expect(screen.getByText("Loading budget data...")).toBeInTheDocument();
  });

  it("shows backend errors without hiding the dashboard shell", () => {
    mockUseBudgetTracker.mockReturnValue({
      ...baseTrackerState,
      errorMessage: "Backend unavailable.",
    });

    render(<BudgetTrackerShell />);

    expect(screen.getByText("Backend unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Ollama analysis agent")).toBeInTheDocument();
  });

  it("shows success feedback messages for sanity checks", () => {
    mockUseBudgetTracker.mockReturnValue({
      ...baseTrackerState,
      statusMessage: "Smoke check passed.",
    });

    render(<BudgetTrackerShell />);

    expect(screen.getByText("Smoke check passed.")).toBeInTheDocument();
  });
});
