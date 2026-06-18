import { act, renderHook, waitFor } from "@testing-library/react";

var mockApiClient = {
  listExpenses: jest.fn(),
  searchExpenseById: jest.fn(),
  createExpense: jest.fn(),
  updateExpense: jest.fn(),
  deleteExpense: jest.fn(),
  importExpenses: jest.fn(),
  exportExpenses: jest.fn(),
  downloadMonthlyReport: jest.fn(),
  getSettings: jest.fn(),
  getDashboard: jest.fn(),
  getCategoryInsights: jest.fn(),
  getWordCloud: jest.fn(),
  getFinancialPulse: jest.fn(),
  getPrediction: jest.fn(),
  getLatencyReport: jest.fn(),
  recordClientFailure: jest.fn(),
  startFinanceBriefingAgent: jest.fn(),
  getFinanceBriefingJob: jest.fn(),
  listAgentWorkflows: jest.fn(),
  listAgentRuns: jest.fn(),
  runAutomationBootstrap: jest.fn(),
  startAgentWorkflow: jest.fn(),
  getAgentWorkflowJob: jest.fn(),
  listRecurringItems: jest.fn(),
  getRecurringCalendar: jest.fn(),
  updateMonthlyBudget: jest.fn(),
  updateMonthlyIncome: jest.fn(),
  createRecurringItem: jest.fn(),
  updateRecurringItem: jest.fn(),
  deleteRecurringItem: jest.fn(),
  markRecurringOccurrencePaid: jest.fn(),
  markRecurringOccurrenceUnpaid: jest.fn(),
};

jest.mock("@/lib/api-client", () => ({
  apiClient: mockApiClient,
}));

import { useBudgetTracker } from "@/hooks/use-budget-tracker";

describe("useBudgetTracker error and recurring paths", () => {
  beforeEach(() => {
    jest.resetAllMocks();
    mockApiClient.listExpenses.mockResolvedValue([]);
    mockApiClient.searchExpenseById.mockRejectedValue(new Error("Expense not found."));
    mockApiClient.createExpense.mockResolvedValue({});
    mockApiClient.updateExpense.mockResolvedValue({});
    mockApiClient.deleteExpense.mockResolvedValue({});
    mockApiClient.importExpenses.mockResolvedValue({ imported_rows: 1, skipped_rows: 0 });
    mockApiClient.exportExpenses.mockReturnValue("/export");
    mockApiClient.downloadMonthlyReport.mockReturnValue("/report");
    mockApiClient.getSettings.mockResolvedValue({ monthly_budget: 1050, monthly_income: 1500, income_month: "2026-03" });
    mockApiClient.getDashboard.mockResolvedValue({
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
    });
    mockApiClient.getCategoryInsights.mockResolvedValue({
      top_categories: [],
      bottom_categories: [],
      total_spending: 0,
    });
    mockApiClient.getWordCloud.mockResolvedValue({
      top_category: "",
      frequencies: [],
    });
    mockApiClient.getFinancialPulse.mockResolvedValue({
      health_score: 80,
      average_transaction: 32.5,
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
    });
    mockApiClient.getPrediction.mockResolvedValue({
      next_month: "April 2026",
      predicted_spending: 880,
      is_budget_exceeded: false,
      monthly_budget: 1050,
    });
    mockApiClient.getLatencyReport.mockResolvedValue({
      scope: "current_user",
      record_count: 0,
      failed_count: 0,
      summary: { average_ms: 0, minimum_ms: 0, maximum_ms: 0, p95_ms: 0 },
      by_endpoint: [],
      latest: [],
    });
    mockApiClient.startFinanceBriefingAgent.mockResolvedValue({
      id: "job-1",
      status: "queued",
      task: "Prepare a finance briefing",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: null,
    });
    mockApiClient.getFinanceBriefingJob.mockResolvedValue({
      id: "job-1",
      status: "completed",
      task: "Prepare a finance briefing",
      created_at: "2026-03-21T10:00:00Z",
      started_at: "2026-03-21T10:00:01Z",
      completed_at: "2026-03-21T10:00:05Z",
      error: null,
      result: {
        headline: "Finance briefing",
        summary: "Stable month.",
        risk_level: "low",
        recommended_actions: [],
        email_subject: "Finance briefing",
        email_draft: "Stable month.",
        task: "Prepare a finance briefing",
        model: "mistral:latest",
        tools_used: ["get_dashboard_summary"],
        report_download_url: "/api/reports/monthly",
        generated_at: "2026-03-21T10:00:00Z",
      },
    });
    mockApiClient.listAgentWorkflows.mockResolvedValue([]);
    mockApiClient.listAgentRuns.mockResolvedValue([]);
    mockApiClient.runAutomationBootstrap.mockResolvedValue([]);
    mockApiClient.startAgentWorkflow.mockResolvedValue({
      id: "workflow-job-1",
      status: "queued",
      workflow_name: "month_end_close",
      task: "Run the workflow",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: null,
    });
    mockApiClient.getAgentWorkflowJob.mockResolvedValue({
      id: "workflow-job-1",
      status: "completed",
      workflow_name: "month_end_close",
      task: "Run the workflow",
      created_at: "2026-03-21T10:00:00Z",
      started_at: "2026-03-21T10:00:01Z",
      completed_at: "2026-03-21T10:00:03Z",
      error: null,
      result: {
        id: 1,
        workflow_name: "month_end_close",
        workflow_label: "Month-end close",
        status: "completed",
        headline: "Month-end pack ready",
        summary: "The KPI pack has been refreshed.",
        risk_level: "low",
        recommended_actions: [],
        automated_actions: ["Generated a fresh monthly PDF report for distribution."],
        email_subject: "Month-end pack ready",
        email_draft: "The report and summary are ready.",
        task: "Run the workflow",
        model: "mistral:latest",
        tools_used: ["generate_monthly_report"],
        report_download_url: "/api/reports/monthly",
        generated_at: "2026-03-21T10:00:00Z",
      },
    });
    mockApiClient.listRecurringItems.mockResolvedValue([
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
    ]);
    mockApiClient.getRecurringCalendar.mockResolvedValue({
      window_start: "2026-03-21",
      window_end: "2026-04-24",
      occurrences: [],
      completed_occurrences: [],
    });
    mockApiClient.updateMonthlyBudget.mockResolvedValue({ monthly_budget: 1200, monthly_income: 1500 });
    mockApiClient.updateMonthlyIncome.mockResolvedValue({ monthly_budget: 1200, monthly_income: 2400, income_month: "2026-03" });
    mockApiClient.createRecurringItem.mockResolvedValue({ id: 2 });
    mockApiClient.updateRecurringItem.mockResolvedValue({});
    mockApiClient.deleteRecurringItem.mockResolvedValue({});
    mockApiClient.markRecurringOccurrencePaid.mockResolvedValue({ message: "Reminder marked as paid for this date." });
    mockApiClient.markRecurringOccurrenceUnpaid.mockResolvedValue({ message: "Reminder restored for this date." });
  });

  it("surfaces search errors and preserves the empty filtered state", async () => {
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setSearchId("999");
    });
    await act(async () => {
      await result.current.searchExpenseById();
    });

    await waitFor(() => expect(result.current.errorMessage).toBe("Expense not found."));
    expect(result.current.errorMessage).toBe("Expense not found.");
    expect(result.current.expenses).toEqual([]);
  });

  it("runs recurring item create, update, and delete flows", async () => {
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.createRecurringItem({
        category: "Subscriptions",
        description: "Gym",
        amount: "30.00",
        entry_type: "expense",
        frequency: "monthly",
        start_date: "2026-03-28",
        active: true,
      });
      await result.current.updateRecurringItem(1, {
        category: "Housing",
        description: "Updated rent",
        amount: "725.00",
        entry_type: "expense",
        frequency: "monthly",
        start_date: "2026-03-01",
        active: true,
      });
      await result.current.deleteRecurringItem(1);
    });

    expect(mockApiClient.createRecurringItem).toHaveBeenCalled();
    expect(mockApiClient.updateRecurringItem).toHaveBeenCalledWith(1, expect.any(Object));
    expect(mockApiClient.deleteRecurringItem).toHaveBeenCalledWith(1);
  });
});



