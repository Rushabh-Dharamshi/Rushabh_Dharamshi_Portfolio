import { render, screen } from "@testing-library/react";

import { BudgetTrackerShell } from "@/components/budget-tracker-shell";

jest.mock("@/hooks/use-budget-tracker", () => ({
  useBudgetTracker: () => ({
    allExpenses: [
      {
        id: 1,
        date: "2026-03-01",
        category: "Food",
        description: "Groceries",
        amount: 20.5,
        entry_type: "expense",
      },
    ],
    expenses: [
      {
        id: 1,
        date: "2026-03-01",
        category: "Food",
        description: "Groceries",
        amount: 20.5,
        entry_type: "expense",
      },
    ],
    selectedExpense: null,
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
    },
    categoryInsights: {
      top_categories: [{ category: "Food", amount: 220 }],
      bottom_categories: [{ category: "Travel", amount: 80 }],
      total_spending: 300,
    },
    wordCloud: {
      top_category: "Food",
      frequencies: [{ label: "Groceries", value: 220 }],
    },
    financialPulse: {
      health_score: 81,
      average_transaction: 30.5,
      transaction_count: 8,
      spend_velocity: 15,
      top_category_share: 43,
      runway_days: 18,
      narrative: "Steady spending rhythm.",
      cash_in: 1500,
      cash_out: 420,
      net_cash_flow: 1080,
      income_coverage: 357.14,
      recent_transactions: [],
      recent_expenses: [],
    },
    recurringItems: [],
    recurringCalendar: { window_start: "2026-03-01", window_end: "2026-04-04", occurrences: [], completed_occurrences: [] },
    prediction: null,
    agentTaskDraft: "Prepare a finance briefing",
    agentWorkflows: [
      {
        id: "month_end_close",
        label: "Month-end close",
        description: "Generate the monthly report and review KPIs.",
        automation_focus: "Automates month-end reporting.",
        default_task: "Run the workflow.",
      },
    ],
    agentRuns: [],
    agentBriefing: {
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
    },
    isAgentRunning: false,
    activeWorkflowName: null,
    searchId: "",
    budgetDraft: "1050.00",
    incomeDraft: "1500.00",
    statusMessage: "Showing all records.",
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
  }),
}));

describe("BudgetTrackerShell", () => {
  it("renders the composed experience", () => {
    render(<BudgetTrackerShell />);

    expect(screen.getByText("Budget Tracker")).toBeInTheDocument();
    expect(screen.getByText("Financial pulse")).toBeInTheDocument();
    expect(screen.getByText("Charts and performance signals")).toBeInTheDocument();
    expect(screen.getByText("Overlay spending comparison")).toBeInTheDocument();
    expect(screen.getByText("Agent workflows for repetitive finance tasks")).toBeInTheDocument();
    expect(screen.getByText("Local Ollama analysis agent")).toBeInTheDocument();
    expect(screen.getByText("Transaction records")).toBeInTheDocument();
  });
});
