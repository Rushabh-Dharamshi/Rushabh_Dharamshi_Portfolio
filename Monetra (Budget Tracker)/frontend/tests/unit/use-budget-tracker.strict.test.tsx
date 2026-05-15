import { act, renderHook, waitFor } from "@testing-library/react";

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
  getDashboard: jest.fn(),
  getCategoryInsights: jest.fn(),
  getWordCloud: jest.fn(),
  getFinancialPulse: jest.fn(),
  getPrediction: jest.fn(),
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

const expense = {
  id: 1,
  date: "2026-03-01",
  category: "Food",
  description: "Groceries",
  amount: 20.5,
  entry_type: "expense" as const,
};

function seedHappyPath() {
  jest.resetAllMocks();
  window.sessionStorage.clear();
  mockApiClient.listExpenses.mockResolvedValue([expense]);
  mockApiClient.searchExpenseById.mockResolvedValue(expense);
  mockApiClient.createExpense.mockResolvedValue({ id: 2 });
  mockApiClient.updateExpense.mockResolvedValue({});
  mockApiClient.deleteExpense.mockResolvedValue({});
  mockApiClient.importExpenses.mockResolvedValue({ imported_rows: 1, skipped_rows: 0 });
  mockApiClient.exportExpenses.mockReturnValue("/export");
  mockApiClient.downloadMonthlyReport.mockReturnValue("/report");
  mockApiClient.getSettings.mockResolvedValue({ monthly_budget: 1050, monthly_income: 1500, income_month: "2026-03" });
  mockApiClient.getDashboard.mockResolvedValue(baseDashboard);
  mockApiClient.getCategoryInsights.mockResolvedValue({ top_categories: [], bottom_categories: [], total_spending: 0 });
  mockApiClient.getWordCloud.mockResolvedValue({ top_category: "Food", frequencies: [] });
  mockApiClient.getFinancialPulse.mockResolvedValue({ health_score: 80, average_transaction: 20, transaction_count: 1, spend_velocity: 10, top_category_share: 50, runway_days: 12, narrative: "Stable", cash_in: 1500, cash_out: 420, net_cash_flow: 1080, income_coverage: 300, recent_transactions: [], recent_expenses: [] });
  mockApiClient.getPrediction.mockResolvedValue({ next_month: "April 2026", predicted_spending: 900, is_budget_exceeded: false, monthly_budget: 1050 });
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
}

describe("useBudgetTracker strict coverage", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    seedHappyPath();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("covers initial load failure and bootstrap failure paths", async () => {
    mockApiClient.listExpenses.mockRejectedValueOnce(new Error("Initial load failed"));
    const { result } = renderHook(() => useBudgetTracker());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.errorMessage).toBe("Initial load failed");

    seedHappyPath();
    mockApiClient.runAutomationBootstrap.mockRejectedValueOnce(new Error("Bootstrap failed"));
    const rerendered = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(rerendered.result.current.isLoading).toBe(false));
    await waitFor(() => expect(rerendered.result.current.errorMessage).toBe("Bootstrap failed"));
  });

  it("covers polling, refresh, and failure branches across actions", async () => {
    const automationErrorSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
    mockApiClient.getFinanceBriefingJob
      .mockResolvedValueOnce({ id: "brief-1", status: "queued", result: null })
      .mockResolvedValueOnce({ id: "brief-1", status: "running", result: null })
      .mockResolvedValueOnce({ id: "brief-1", status: "completed", result: { headline: "Brief", summary: "ok", risk_level: "low", recommended_actions: [], email_subject: "Brief", email_draft: "Brief", task: "brief", model: "qwen", tools_used: [{}, {}], report_download_url: null, action_result: { type: "expense_created" } } });
    mockApiClient.getAgentWorkflowJob
      .mockResolvedValueOnce({ id: "wf-1", status: "queued", result: null })
      .mockResolvedValueOnce({ id: "wf-1", status: "running", result: null })
      .mockResolvedValueOnce({ id: "wf-1", status: "completed", result: { id: 9, workflow_name: "month_end_close", workflow_label: "Month-end close", status: "completed", headline: "Done", summary: "done", risk_level: "low", recommended_actions: [], automated_actions: [], email_subject: "Done", email_draft: "Done", task: "run", model: "qwen", tools_used: [{}, {}] } });

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.selectExpense(expense);
      result.current.setForm({ date: "2026-03-02", category: "Travel", description: "Bus", amount: "4.20", entry_type: "expense" });
      result.current.setSearchId("");
    });

    await act(async () => {
      await result.current.searchExpenseById();
    });
    expect(result.current.expenses).toHaveLength(1);

    mockApiClient.runAutomationRefresh.mockRejectedValueOnce(new Error("refresh failed"));
    await act(async () => {
      await result.current.createExpense();
    });
    expect(automationErrorSpy).toHaveBeenCalledWith("[Monetra Automation] Automatic workflow refresh failed.", expect.any(Error));

    act(() => {
      result.current.selectExpense(expense);
    });
    mockApiClient.updateExpense.mockRejectedValueOnce(new Error("Update failed"));
    await act(async () => {
      await result.current.updateExpense();
    });
    expect(result.current.errorMessage).toBe("Update failed");

    act(() => {
      result.current.selectExpense(expense);
    });
    mockApiClient.deleteExpense.mockRejectedValueOnce(new Error("Delete failed"));
    await act(async () => {
      await result.current.deleteExpense();
    });
    expect(result.current.errorMessage).toBe("Delete failed");

    mockApiClient.importExpenses.mockRejectedValueOnce(new Error("Import failed"));
    await act(async () => {
      await result.current.importExpenses(new File(["csv"], "import.csv", { type: "text/csv" }));
    });
    expect(result.current.errorMessage).toBe("Import failed");

    mockApiClient.getPrediction.mockRejectedValueOnce(new Error("Prediction failed"));
    await act(async () => {
      await result.current.predictNextMonth();
    });
    expect(result.current.errorMessage).toBe("Prediction failed");

    await act(async () => {
      const promise = result.current.runFinanceBriefingAgent();
      await jest.advanceTimersByTimeAsync(4000);
      await promise;
    });
    expect(result.current.agentBriefing?.headline).toBe("Brief");

    await act(async () => {
      const promise = result.current.runAutomationWorkflow("month_end_close");
      await jest.advanceTimersByTimeAsync(4000);
      await promise;
    });
    expect(result.current.agentRuns[0]?.workflow_name).toBe("month_end_close");

    automationErrorSpy.mockRestore();
  });

  it("covers remaining error branches for budget, recurring, workflow, and email actions", async () => {
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    mockApiClient.updateMonthlyBudget.mockRejectedValueOnce(new Error("Budget failed"));
    await act(async () => {
      await result.current.saveMonthlyBudget();
    });
    expect(result.current.errorMessage).toBe("Budget failed");

    mockApiClient.updateMonthlyIncome.mockRejectedValueOnce(new Error("Income failed"));
    await act(async () => {
      await result.current.saveMonthlyIncome();
    });
    expect(result.current.errorMessage).toBe("Income failed");

    mockApiClient.createRecurringItem.mockRejectedValueOnce(new Error("Create recurring failed"));
    await act(async () => {
      await result.current.createRecurringItem({ category: "Bills", description: "Water", amount: "12.00", entry_type: "expense", frequency: "monthly", start_date: "2026-04-01", end_date: "", active: true });
    });
    expect(result.current.errorMessage).toBe("Create recurring failed");

    mockApiClient.updateRecurringItem.mockRejectedValueOnce(new Error("Update recurring failed"));
    await act(async () => {
      await result.current.updateRecurringItem(1, { category: "Bills", description: "Water", amount: "12.00", entry_type: "expense", frequency: "monthly", start_date: "2026-04-01", end_date: "", active: true });
    });
    expect(result.current.errorMessage).toBe("Update recurring failed");

    mockApiClient.deleteRecurringItem.mockRejectedValueOnce(new Error("Delete recurring failed"));
    await act(async () => {
      await result.current.deleteRecurringItem(1);
    });
    expect(result.current.errorMessage).toBe("Delete recurring failed");

    mockApiClient.markRecurringOccurrencePaid.mockRejectedValueOnce(new Error("Paid link failed"));
    await act(async () => {
      await result.current.markRecurringOccurrencePaid(1, "2026-04-01", 77);
    });
    expect(result.current.errorMessage).toBe("Paid link failed");

    mockApiClient.markRecurringOccurrenceUnpaid.mockRejectedValueOnce(new Error("Unpaid failed"));
    await act(async () => {
      await result.current.markRecurringOccurrenceUnpaid(1, "2026-04-01");
    });
    expect(result.current.errorMessage).toBe("Unpaid failed");

    mockApiClient.getFinanceBriefingJob.mockResolvedValueOnce({ id: "brief-1", status: "failed", error: "Brief failed", result: null });
    await act(async () => {
      await result.current.runFinanceBriefingAgent();
    });
    expect(result.current.errorMessage).toBe("Brief failed");

    mockApiClient.getAgentWorkflowJob.mockResolvedValueOnce({ id: "wf-1", status: "failed", error: null, result: null });
    await act(async () => {
      await result.current.runAutomationWorkflow("month_end_close");
    });
    expect(result.current.errorMessage).toBe("The month_end_close workflow failed.");

    mockApiClient.sendMonthEndEmailNow.mockRejectedValueOnce(new Error("Month-end failed"));
    await act(async () => {
      await result.current.sendMonthEndEmailNow();
    });
    expect(result.current.errorMessage).toBe("Month-end failed");
  });

  it("covers explicit workflow errors and deduplicates repeated workflow runs", async () => {
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.runAutomationWorkflow("month_end_close");
    });
    expect(result.current.agentRuns).toHaveLength(1);
    expect(result.current.agentRuns[0]?.id).toBe(5);

    mockApiClient.startAgentWorkflow.mockResolvedValueOnce({
      id: "wf-2",
      status: "queued",
      workflow_name: "month_end_close",
      task: "run",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: null,
    });
    mockApiClient.getAgentWorkflowJob.mockResolvedValueOnce({
      id: "wf-2",
      status: "completed",
      workflow_name: "month_end_close",
      task: "run",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: {
        id: 5,
        workflow_name: "month_end_close",
        workflow_label: "Month-end close",
        status: "completed",
        headline: "Close again",
        summary: "Workflow finished again",
        risk_level: "low",
        recommended_actions: [],
        automated_actions: [],
        email_subject: "Close again",
        email_draft: "Close again",
        task: "run",
        model: "qwen",
        tools_used: [],
      },
    });

    await act(async () => {
      await result.current.runAutomationWorkflow("month_end_close");
    });
    expect(result.current.agentRuns).toHaveLength(1);
    expect(result.current.agentRuns[0]?.headline).toBe("Close again");

    mockApiClient.getAgentWorkflowJob.mockResolvedValueOnce({
      id: "wf-1",
      status: "failed",
      error: "Workflow exploded",
      result: null,
    });
    await act(async () => {
      await result.current.runAutomationWorkflow("month_end_close");
    });
    expect(result.current.errorMessage).toBe("Workflow exploded");
  });

  it("does not trigger automation refresh when the briefing returns no action result", async () => {
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    mockApiClient.runAutomationRefresh.mockClear();
    mockApiClient.getFinanceBriefingJob.mockResolvedValueOnce({
      id: "brief-1",
      status: "completed",
      task: "brief",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: {
        headline: "Brief",
        summary: "No action",
        risk_level: "low",
        recommended_actions: [],
        email_subject: "Brief",
        email_draft: "Brief",
        task: "brief",
        model: "qwen",
        tools_used: [],
        report_download_url: null,
      },
    });

    await act(async () => {
      await result.current.runFinanceBriefingAgent();
    });

    expect(mockApiClient.runAutomationRefresh).not.toHaveBeenCalled();
    expect(result.current.errorMessage).toBeNull();
  });

  it("covers budget status variants and bootstrap skip branch", async () => {
    const key = `monetra-automation-bootstrap:${new Date().toISOString().slice(0, 10)}`;
    window.sessionStorage.setItem(key, "done");
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.checkBudgetStatus();
    });
    expect(result.current.statusMessage).toContain("You are within budget.");

    mockApiClient.getDashboard.mockResolvedValueOnce({ ...baseDashboard, status: "warning" });
    await act(async () => {
      await result.current.refresh();
    });
    act(() => {
      result.current.checkBudgetStatus();
    });
    expect(result.current.statusMessage).toContain("close to your budget limit");

    mockApiClient.getDashboard.mockResolvedValueOnce({ ...baseDashboard, status: "over" });
    await act(async () => {
      await result.current.refresh();
    });
    act(() => {
      result.current.checkBudgetStatus();
    });
    expect(result.current.statusMessage).toContain("over budget");
  });

  it("covers search success message, empty income month fallback, and null-dashboard budget check", async () => {
    seedHappyPath();
    mockApiClient.getSettings.mockResolvedValueOnce({ monthly_budget: 1050, monthly_income: 1500, income_month: null });
    mockApiClient.getDashboard.mockResolvedValueOnce({ ...baseDashboard, income_month: null });
    mockApiClient.searchExpenseById.mockResolvedValueOnce({ ...expense, id: 88 });

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setSearchId("88");
    });
    await act(async () => {
      await result.current.searchExpenseById();
    });
    expect(result.current.statusMessage).toBe("Showing search result for expense #88.");
    expect(result.current.expenses[0]?.id).toBe(88);
    expect(result.current.incomeMonthDraft).toBe(baseDashboard.month_key);

    mockApiClient.getDashboard.mockRejectedValueOnce(new Error("dashboard unavailable"));
    const failure = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(failure.result.current.isLoading).toBe(false));
    act(() => {
      failure.result.current.checkBudgetStatus();
    });
    expect(failure.result.current.statusMessage).toBeNull();
  });

  it("does not launch automation workflows after email-only agent actions", async () => {
    mockApiClient.getFinanceBriefingJob.mockResolvedValueOnce({
      id: "brief-email",
      status: "completed",
      result: {
        headline: "Month-end report sent",
        summary: "Email sent.",
        risk_level: "low",
        recommended_actions: [],
        email_subject: "Month-end report",
        email_draft: "Sent.",
        task: "send an email of my current financial report",
        model: "qwen",
        tools_used: [],
        report_download_url: "/api/reports/monthly",
        action_result: { type: "month_end_email_sent" },
      },
    });
    mockApiClient.runAutomationRefresh.mockClear();
    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.runFinanceBriefingAgent();
    });

    expect(mockApiClient.runAutomationRefresh).not.toHaveBeenCalled();
  });
});

