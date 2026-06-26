import { act, renderHook, waitFor } from "@testing-library/react";

import { buildSpendingComparison } from "@/lib/spending-comparison";

const mockApiClient = {
  listExpenses: jest.fn(),
  searchExpenseById: jest.fn(),
  createExpense: jest.fn(),
  updateExpense: jest.fn(),
  deleteExpense: jest.fn(),
  importExpenses: jest.fn(),
  exportExpenses: jest.fn(),
  downloadMonthlyReport: jest.fn(),
  getSettings: jest.fn(),
  listMonthlyIncomeRecords: jest.fn(),
  getDashboard: jest.fn(),
  getCategoryInsights: jest.fn(),
  getWordCloud: jest.fn(),
  getFinancialPulse: jest.fn(),
  getPrediction: jest.fn(),
  getLatencyReport: jest.fn(),
  recordClientFailure: jest.fn(),
  getRagStatus: jest.fn(),
  reindexRag: jest.fn(),
  queryRag: jest.fn(),
  startFinanceBriefingAgent: jest.fn(),
  getFinanceBriefingJob: jest.fn(),
  listAgentWorkflows: jest.fn(),
  listAgentRuns: jest.fn(),
  runAutomationBootstrap: jest.fn(),
  startAgentWorkflow: jest.fn(),
  getAgentWorkflowJob: jest.fn(),
  runAutomationRefresh: jest.fn(),
  sendUpcomingBillsEmailNow: jest.fn(),
  sendAllUpcomingBillsEmailNow: jest.fn(),
  sendMonthEndEmailNow: jest.fn(),
  listRecurringItems: jest.fn(),
  getRecurringCalendar: jest.fn(),
  updateMonthlyBudget: jest.fn(),
  updateMonthlyIncome: jest.fn(),
  createRecurringItem: jest.fn(),
  updateRecurringItem: jest.fn(),
  deleteRecurringItem: jest.fn(),
  markRecurringOccurrencePaid: jest.fn(),
  markRecurringOccurrenceUnpaid: jest.fn(),
  createSavingsGoal: jest.fn(),
  updateSavingsGoal: jest.fn(),
  deleteSavingsGoal: jest.fn(),
};

jest.mock("@/lib/api-client", () => ({ apiClient: mockApiClient }));

import { useBudgetTracker } from "@/hooks/use-budget-tracker";

const baseDashboard = {
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

const emptyLatencyReport = {
  scope: "current_user",
  record_count: 0,
  failed_count: 0,
  summary: { average_ms: 0, minimum_ms: 0, maximum_ms: 0, p95_ms: 0 },
  by_endpoint: [],
  latest: [],
};

function seedHappyPath() {
  jest.resetAllMocks();
  window.sessionStorage.clear();
  mockApiClient.listExpenses.mockResolvedValue([{ id: 1, date: "2026-03-01", category: "Food", description: "Groceries", amount: 20.5, entry_type: "expense" }]);
  mockApiClient.searchExpenseById.mockResolvedValue({ id: 1, date: "2026-03-01", category: "Food", description: "Groceries", amount: 20.5, entry_type: "expense" });
  mockApiClient.createExpense.mockResolvedValue({ id: 2 });
  mockApiClient.updateExpense.mockResolvedValue({});
  mockApiClient.deleteExpense.mockResolvedValue({});
  mockApiClient.importExpenses.mockResolvedValue({ imported_rows: 1, skipped_rows: 0 });
  mockApiClient.exportExpenses.mockReturnValue("/export");
  mockApiClient.downloadMonthlyReport.mockReturnValue("/report");
  mockApiClient.getSettings.mockResolvedValue({ monthly_budget: 1050, monthly_income: 1500, income_month: "2026-03" });
  mockApiClient.listMonthlyIncomeRecords.mockResolvedValue([]);
  mockApiClient.getDashboard.mockResolvedValue(baseDashboard);
  mockApiClient.getCategoryInsights.mockResolvedValue({ top_categories: [], bottom_categories: [], total_spending: 0 });
  mockApiClient.getWordCloud.mockResolvedValue({ top_category: "Food", frequencies: [] });
  mockApiClient.getFinancialPulse.mockResolvedValue({ health_score: 80, average_transaction: 20, transaction_count: 1, spend_velocity: 10, top_category_share: 50, runway_days: 12, narrative: "Stable", cash_in: 1500, cash_out: 420, net_cash_flow: 1080, income_coverage: 300, recent_transactions: [], recent_expenses: [] });
  mockApiClient.getPrediction.mockResolvedValue({ next_month: "April 2026", predicted_spending: 900, is_budget_exceeded: false, monthly_budget: 1050 });
  mockApiClient.getLatencyReport.mockResolvedValue(emptyLatencyReport);
  mockApiClient.getRagStatus.mockResolvedValue({ available: true, collection_name: "monetra-finance-knowledge", indexed_at: null, document_count: 0, chunk_count: 0, signature: null });
  mockApiClient.startFinanceBriefingAgent.mockResolvedValue({ id: "brief-1", status: "queued", task: "brief", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: null });
  mockApiClient.getFinanceBriefingJob.mockResolvedValue({ id: "brief-1", status: "completed", task: "brief", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: { headline: "Done", summary: "Summary", risk_level: "low", recommended_actions: [], email_subject: "Done", email_draft: "Done", task: "brief", model: "qwen", tools_used: [], report_download_url: null } });
  mockApiClient.listAgentWorkflows.mockResolvedValue([{ id: "month_end_close", label: "Month-end close", description: "desc", automation_focus: "focus", default_task: "run" }]);
  mockApiClient.listAgentRuns.mockResolvedValue([]);
  mockApiClient.runAutomationBootstrap.mockResolvedValue([]);
  mockApiClient.startAgentWorkflow.mockResolvedValue({ id: "wf-1", status: "queued", workflow_name: "month_end_close", task: "run", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: null });
  mockApiClient.getAgentWorkflowJob.mockResolvedValue({ id: "wf-1", status: "completed", workflow_name: "month_end_close", task: "run", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: { id: 5, workflow_name: "month_end_close", workflow_label: "Month-end close", status: "completed", headline: "Close", summary: "Workflow finished", risk_level: "low", recommended_actions: [], automated_actions: [], email_subject: "Close", email_draft: "Close", task: "run", model: "qwen", tools_used: [] } });
  mockApiClient.runAutomationRefresh.mockResolvedValue([]);
  mockApiClient.sendUpcomingBillsEmailNow.mockResolvedValue({ id: 6, workflow_name: "upcoming_bills_email", workflow_label: "Upcoming bills email", status: "completed", headline: "Bills", summary: "Bills sent", risk_level: "low", recommended_actions: [], automated_actions: [], email_subject: "Bills", email_draft: "Bills", task: "run", model: "qwen", tools_used: [] });
  mockApiClient.sendAllUpcomingBillsEmailNow.mockResolvedValue({ id: 8, workflow_name: "all_upcoming_bills_email", workflow_label: "All upcoming bills email", status: "completed", headline: "All bills", summary: "All bills sent", risk_level: "low", recommended_actions: [], automated_actions: [], email_subject: "All bills", email_draft: "All bills", task: "run", model: "qwen", tools_used: [] });
  mockApiClient.sendMonthEndEmailNow.mockResolvedValue({ id: 7, workflow_name: "month_end_email", workflow_label: "Month-end email", status: "completed", headline: "Month end", summary: "Month end sent", risk_level: "low", recommended_actions: [], automated_actions: [], email_subject: "Month end", email_draft: "Month end", task: "run", model: "qwen", tools_used: [] });
  mockApiClient.listRecurringItems.mockResolvedValue([{ id: 1, category: "Housing", description: "Rent", amount: 700, entry_type: "expense", frequency: "monthly", start_date: "2026-03-01", active: true }]);
  mockApiClient.getRecurringCalendar.mockResolvedValue({ window_start: "2026-03-01", window_end: "2026-04-04", occurrences: [], completed_occurrences: [] });
  mockApiClient.updateMonthlyBudget.mockResolvedValue({ monthly_budget: 1200, monthly_income: 1500 });
  mockApiClient.updateMonthlyIncome.mockResolvedValue({ monthly_budget: 1200, monthly_income: 2400, income_month: "2026-03" });
  mockApiClient.createRecurringItem.mockResolvedValue({ id: 2 });
  mockApiClient.updateRecurringItem.mockResolvedValue({});
  mockApiClient.deleteRecurringItem.mockResolvedValue({});
  mockApiClient.markRecurringOccurrencePaid.mockResolvedValue({ message: "Reminder marked as paid for this date." });
  mockApiClient.markRecurringOccurrenceUnpaid.mockResolvedValue({ message: "Reminder restored for this date." });
  mockApiClient.createSavingsGoal.mockResolvedValue({ id: 11 });
  mockApiClient.updateSavingsGoal.mockResolvedValue({});
  mockApiClient.deleteSavingsGoal.mockResolvedValue({});
}

describe("final hook, api client, and comparison coverage", () => {
  let errorSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.useFakeTimers();
    seedHappyPath();
    errorSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    errorSpy.mockRestore();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("covers explicit income-month fallback branches and quiet workflow polling", async () => {
    mockApiClient.getAgentWorkflowJob
      .mockResolvedValueOnce({ id: "refresh-job", status: "queued", workflow_name: "month_end_close", task: "run", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: null })
      .mockResolvedValueOnce({ id: "refresh-job", status: "completed", workflow_name: "month_end_close", task: "run", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: { id: 99, workflow_name: "month_end_close", workflow_label: "Month-end close", status: "completed", headline: "Refresh", summary: "done", risk_level: "low", recommended_actions: [], automated_actions: [], email_subject: "Refresh", email_draft: "Refresh", task: "run", model: "qwen", tools_used: [] } });
    mockApiClient.runAutomationRefresh.mockClear();

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    mockApiClient.getSettings.mockResolvedValueOnce({ monthly_budget: 1050, monthly_income: 1500, income_month: null });
    mockApiClient.getDashboard.mockResolvedValueOnce({ ...baseDashboard, income_month: null, month_key: null as unknown as string });
    await act(async () => {
      await result.current.refresh("2026-04");
    });
    expect(result.current.incomeMonthDraft).toBe("2026-04");

    act(() => {
      result.current.selectExpense({ id: 1, date: "2026-03-01", category: "Food", description: "Groceries", amount: 20.5, entry_type: "expense" });
      result.current.setForm({ date: "2026-03-02", category: "Travel", description: "Bus", amount: "4.20", entry_type: "expense" });
    });
    await act(async () => {
      const promise = result.current.createExpense();
      await jest.advanceTimersByTimeAsync(2500);
      await promise;
    });
    expect(result.current.statusMessage).toBe("Expense #2 added successfully.");
    expect(mockApiClient.runAutomationRefresh).not.toHaveBeenCalled();
  });

  it("covers month-income fallback, finance briefing fallback error, and import string errors", async () => {
    mockApiClient.updateMonthlyIncome.mockResolvedValueOnce({ monthly_budget: 1200, monthly_income: 2400, income_month: null });
    mockApiClient.getFinanceBriefingJob.mockResolvedValueOnce({ id: "brief-1", status: "failed", error: null, result: null });

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setIncomeMonthDraft("2026-06");
    });
    await act(async () => {
      await result.current.saveMonthlyIncome();
    });
    expect(result.current.statusMessage).toContain("2026-06");

    await act(async () => {
      await result.current.runFinanceBriefingAgent();
    });
    expect(result.current.errorMessage).toBe("The AI agent failed to complete the request.");
  });

  it("covers non-json API responses and additional spending-comparison branches", async () => {
    const comparison = buildSpendingComparison(
      [
        { id: 1, date: "2026-04-01", category: "Food", description: "Groceries", amount: 80, entry_type: undefined as unknown as "expense" },
        { id: 2, date: "2026-04-08", category: "Travel", description: "Train", amount: 40, entry_type: "expense" },
        { id: 3, date: "2026-03-04", category: "Food", description: "Cafe", amount: 20, entry_type: "expense" },
        { id: 4, date: "2026-04-10", category: "Salary", description: "Payroll", amount: 1000, entry_type: "income" },
      ],
      { granularity: "monthly", mode: "category", periodCount: 99, category: "Missing", referenceDate: new Date("2026-04-18T12:00:00Z") },
    );

    expect(comparison.selectedCategory).toBe("Food");
    expect(comparison.categories).toEqual(["Food", "Travel"]);
    expect(comparison.currentPeriodLabel).toBeTruthy();
    expect(comparison.strongestPeriodValue).toBeGreaterThanOrEqual(0);
    expect(comparison.averagePeriodSpend).toBeGreaterThanOrEqual(0);

    const weekly = buildSpendingComparison([], {
      granularity: "weekly",
      mode: "overall",
      periodCount: 1,
      referenceDate: new Date("2026-04-18T12:00:00Z"),
    });
    expect(weekly.currentPeriodChange).toBeNull();
    expect(weekly.series).toHaveLength(2);
  });

  it("covers the automation refresh early-return branch when refresh support is unavailable", async () => {
    const originalRefresh = mockApiClient.runAutomationRefresh;
    delete (mockApiClient as { runAutomationRefresh?: unknown }).runAutomationRefresh;

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.createExpense();
    });

    expect(result.current.statusMessage).toBe("Expense #2 added successfully.");

    mockApiClient.runAutomationRefresh = originalRefresh;
  });

  it("covers operation-lock early returns for savings-goal mutations", async () => {
    let resolveCreateExpense: (value: { id: number }) => void = () => undefined;
    mockApiClient.createExpense.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveCreateExpense = resolve;
      }),
    );
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let createExpensePromise: Promise<void> = Promise.resolve();
    act(() => {
      createExpensePromise = result.current.createExpense();
    });

    await act(async () => {
      await result.current.createSavingsGoal({ name: "Buffer", target_amount: "100", current_amount: "0", target_date: "" });
      await result.current.updateSavingsGoal(1, { name: "Buffer", target_amount: "100", current_amount: "10", target_date: "" });
      await result.current.deleteSavingsGoal(1);
    });

    expect(mockApiClient.createSavingsGoal).not.toHaveBeenCalled();
    expect(mockApiClient.updateSavingsGoal).not.toHaveBeenCalled();
    expect(mockApiClient.deleteSavingsGoal).not.toHaveBeenCalled();

    await act(async () => {
      resolveCreateExpense({ id: 2 });
      await createExpensePromise;
    });
  });

  it("covers create-expense lock return without launching automation refresh", async () => {
    let resolveCreateExpense: (value: { id: number }) => void = () => undefined;
    mockApiClient.createExpense
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveCreateExpense = resolve;
        }),
      )
      .mockResolvedValueOnce({ id: 3 });
    mockApiClient.runAutomationRefresh.mockClear();

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    const createExpenseBeforeRefreshState = result.current.createExpense;

    let firstCreatePromise: Promise<void> = Promise.resolve();
    act(() => {
      firstCreatePromise = result.current.createExpense();
    });

    await act(async () => {
      await createExpenseBeforeRefreshState();
    });
    expect(mockApiClient.createExpense).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveCreateExpense({ id: 2 });
      await firstCreatePromise;
    });

    await act(async () => {
      await createExpenseBeforeRefreshState();
    });
    expect(mockApiClient.createExpense).toHaveBeenCalledTimes(2);
    expect(mockApiClient.runAutomationRefresh).not.toHaveBeenCalled();
  });

  it("covers all-upcoming email dispatch status and API branch", async () => {
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.sendAllUpcomingBillsEmailNow();
    });

    expect(mockApiClient.sendAllUpcomingBillsEmailNow).toHaveBeenCalled();
    expect(result.current.statusMessage).toBe("All bills sent");
  });

  it("records string-based client operation failures", async () => {
    mockApiClient.sendMonthEndEmailNow.mockRejectedValueOnce("smtp offline");

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.sendMonthEndEmailNow();
    });

    expect(mockApiClient.recordClientFailure).toHaveBeenCalledWith(expect.objectContaining({
      operation: "month end email dispatch",
      error: "smtp offline",
    }));
  });

  it("covers finance-briefing action refreshes and workflow fallback errors on the live hook", async () => {
    mockApiClient.getFinanceBriefingJob.mockResolvedValueOnce({
      id: "brief-1",
      status: "completed",
      task: "brief",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: {
        headline: "Done",
        summary: "Summary",
        risk_level: "low",
        recommended_actions: [],
        email_subject: "Done",
        email_draft: "Done",
        task: "brief",
        model: "qwen",
        tools_used: [],
        report_download_url: null,
        action_result: { type: "expense_updated" },
      },
    });
    mockApiClient.getAgentWorkflowJob.mockResolvedValueOnce({
      id: "wf-1",
      status: "failed",
      workflow_name: "month_end_close",
      task: "run",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: null,
    });

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.runFinanceBriefingAgent();
    });
    expect(mockApiClient.runAutomationRefresh).not.toHaveBeenCalled();

    await act(async () => {
      await result.current.runAutomationWorkflow("month_end_close");
    });
    expect(result.current.errorMessage).toBe("The month_end_close workflow failed.");
  });
});


