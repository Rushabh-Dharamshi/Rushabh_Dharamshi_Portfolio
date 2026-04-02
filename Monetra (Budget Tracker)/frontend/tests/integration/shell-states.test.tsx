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
    expect(screen.getByText("Local Ollama analysis agent")).toBeInTheDocument();
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
