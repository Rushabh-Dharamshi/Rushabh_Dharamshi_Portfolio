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
  listSavingsGoals: jest.fn(),
  updateMonthlyBudget: jest.fn(),
  updateMonthlyIncome: jest.fn(),
  createSavingsGoal: jest.fn(),
  updateSavingsGoal: jest.fn(),
  deleteSavingsGoal: jest.fn(),
  createRecurringItem: jest.fn(),
  updateRecurringItem: jest.fn(),
  deleteRecurringItem: jest.fn(),
  markRecurringOccurrencePaid: jest.fn(),
  markRecurringOccurrenceUnpaid: jest.fn(),
};

jest.mock("@/lib/api-client", () => ({ apiClient: mockApiClient }));

import { useBudgetTracker } from "@/hooks/use-budget-tracker";

const workflowRun = {
  id: 1,
  workflow_name: "month_end_close",
  workflow_label: "Month-end close",
  status: "completed",
  headline: "Month-end pack ready",
  summary: "The KPI pack has been refreshed.",
  risk_level: "low",
  recommended_actions: [],
  automated_actions: ["Generated report"],
  email_subject: "Month-end pack ready",
  email_draft: "Ready.",
  task: "Run the workflow",
  model: "mistral",
  tools_used: ["generate_monthly_report"],
  report_download_url: "/api/reports/monthly",
  generated_at: "2026-03-21T10:00:00Z",
};

const emptyLatencyReport = {
  scope: "current_user",
  record_count: 0,
  failed_count: 0,
  summary: { average_ms: 0, minimum_ms: 0, maximum_ms: 0, p95_ms: 0 },
  by_endpoint: [],
  latest: [],
};

describe("useBudgetTracker unit coverage", () => {
  beforeEach(() => {
    jest.resetAllMocks();
    window.sessionStorage.clear();
    mockApiClient.listExpenses.mockResolvedValue([
      { id: 1, date: "2026-03-01", category: "Food", description: "Groceries", amount: 20.5, entry_type: "expense" },
    ]);
    mockApiClient.searchExpenseById.mockResolvedValue({ id: 1, date: "2026-03-01", category: "Food", description: "Groceries", amount: 20.5, entry_type: "expense" });
    mockApiClient.createExpense.mockResolvedValue({ id: 2 });
    mockApiClient.updateExpense.mockResolvedValue({});
    mockApiClient.deleteExpense.mockResolvedValue({ message: "deleted" });
    mockApiClient.importExpenses.mockResolvedValue({ imported_rows: 1, skipped_rows: 0 });
    mockApiClient.exportExpenses.mockReturnValue("/export");
    mockApiClient.downloadMonthlyReport.mockReturnValue("/report");
    mockApiClient.getSettings.mockResolvedValue({ monthly_budget: 1050, monthly_income: 1500, income_month: "2026-03" });
    mockApiClient.listMonthlyIncomeRecords.mockResolvedValue([]);
    mockApiClient.getDashboard.mockResolvedValue({ monthly_budget: 1050, current_month_total: 420, monthly_expenses: 420, monthly_income: 1500, net_cash_flow: 1080, remaining_budget: 630, weekly_spending: 84.5, percent_spent: 40, status: "within", month_label: "March 2026", month_key: "2026-03", income_month: "2026-03" });
    mockApiClient.getCategoryInsights.mockResolvedValue({ top_categories: [], bottom_categories: [], total_spending: 0 });
    mockApiClient.getWordCloud.mockResolvedValue({ top_category: "Food", frequencies: [] });
    mockApiClient.getFinancialPulse.mockResolvedValue({ health_score: 80, average_transaction: 25, transaction_count: 4, spend_velocity: 14.2, top_category_share: 42, runway_days: 18, narrative: "Steady spending rhythm.", cash_in: 1500, cash_out: 420, net_cash_flow: 1080, income_coverage: 357.14, recent_transactions: [], recent_expenses: [] });
    mockApiClient.getPrediction.mockResolvedValue({ next_month: "April 2026", predicted_spending: 880, is_budget_exceeded: false, monthly_budget: 1050 });
    mockApiClient.getLatencyReport.mockResolvedValue(emptyLatencyReport);
    mockApiClient.recordClientFailure.mockResolvedValue({ recorded: true });
    mockApiClient.getRagStatus.mockResolvedValue({ available: true, collection_name: "monetra-finance-knowledge", indexed_at: "2026-04-15T09:00:00Z", document_count: 12, chunk_count: 36, signature: "sig" });
    mockApiClient.reindexRag.mockResolvedValue({ available: true, collection_name: "monetra-finance-knowledge", indexed_at: "2026-04-15T09:05:00Z", document_count: 13, chunk_count: 39, signature: "sig-2", reindexed: true });
    mockApiClient.queryRag.mockResolvedValue({ question: "What changed?", answer: "Spending is concentrated in food and housing.", confidence: "high", follow_up_questions: ["Which reminders are due next?"], sources: [{ source_label: "Dashboard March 2026", doc_type: "dashboard", document_id: "dashboard::2026-03", excerpt: "Monthly budget is GBP 1050.", score: 0.95, metadata: {} }], generated_at: "2026-04-15T09:10:00Z" });
    mockApiClient.startFinanceBriefingAgent.mockResolvedValue({ id: "job-1", status: "queued", task: "brief", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: null });
    mockApiClient.getFinanceBriefingJob.mockResolvedValue({ id: "job-1", status: "completed", task: "brief", created_at: "2026-03-21T10:00:00Z", started_at: "2026-03-21T10:00:01Z", completed_at: "2026-03-21T10:00:05Z", error: null, result: { headline: "Finance briefing", summary: "Stable month.", risk_level: "low", recommended_actions: [], email_subject: "Finance briefing", email_draft: "Stable month.", task: "Prepare", model: "mistral", tools_used: ["get_dashboard_summary"], report_download_url: "/api/reports/monthly", generated_at: "2026-03-21T10:00:00Z", action_result: { type: "expense_created" } } });
    mockApiClient.listAgentWorkflows.mockResolvedValue([{ id: "month_end_close", label: "Month-end close", description: "Generate report", automation_focus: "Automates reporting.", default_task: "Run." }]);
    mockApiClient.listAgentRuns.mockResolvedValue([]);
    mockApiClient.runAutomationBootstrap.mockResolvedValue([workflowRun]);
    mockApiClient.startAgentWorkflow.mockResolvedValue({ id: "workflow-job-1", status: "queued", workflow_name: "month_end_close", task: "Run", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: null });
    mockApiClient.getAgentWorkflowJob.mockResolvedValue({ id: "workflow-job-1", status: "completed", workflow_name: "month_end_close", task: "Run", created_at: "2026-03-21T10:00:00Z", started_at: "2026-03-21T10:00:05Z", completed_at: "2026-03-21T10:00:10Z", error: null, result: workflowRun });
    mockApiClient.runAutomationRefresh.mockResolvedValue([{ id: "workflow-job-1", workflow_name: "month_end_close", status: "queued", task: "Refresh", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: null }]);
    mockApiClient.sendUpcomingBillsEmailNow.mockResolvedValue({ ...workflowRun, id: 2, workflow_name: "upcoming_bills_email", workflow_label: "Upcoming bills email" });
    mockApiClient.sendAllUpcomingBillsEmailNow.mockResolvedValue({ ...workflowRun, id: 4, workflow_name: "all_upcoming_bills_email", workflow_label: "All upcoming bills email" });
    mockApiClient.sendMonthEndEmailNow.mockResolvedValue({ ...workflowRun, id: 3, workflow_name: "month_end_email", workflow_label: "Month-end email" });
    mockApiClient.listRecurringItems.mockResolvedValue([{ id: 1, category: "Housing", description: "Rent", amount: 700, entry_type: "expense", frequency: "monthly", start_date: "2026-03-01", active: true }]);
    mockApiClient.getRecurringCalendar.mockResolvedValue({ window_start: "2026-03-01", window_end: "2026-04-04", occurrences: [], completed_occurrences: [] });
    mockApiClient.listSavingsGoals.mockResolvedValue([]);
    mockApiClient.updateMonthlyBudget.mockResolvedValue({ monthly_budget: 1200, monthly_income: 1500 });
    mockApiClient.updateMonthlyIncome.mockResolvedValue({ monthly_budget: 1200, monthly_income: 2400, income_month: "2026-03" });
    mockApiClient.createSavingsGoal.mockResolvedValue({ id: 2 });
    mockApiClient.updateSavingsGoal.mockResolvedValue({});
    mockApiClient.deleteSavingsGoal.mockResolvedValue({});
    mockApiClient.createRecurringItem.mockResolvedValue({ id: 2 });
    mockApiClient.updateRecurringItem.mockResolvedValue({});
    mockApiClient.deleteRecurringItem.mockResolvedValue({});
    mockApiClient.markRecurringOccurrencePaid.mockResolvedValue({ message: "Reminder marked as paid for this date." });
    mockApiClient.markRecurringOccurrenceUnpaid.mockResolvedValue({ message: "Reminder restored for this date." });
  });

  it("loads data, bootstraps automation, and runs the main finance actions", async () => {
    const { result } = renderHook(() => useBudgetTracker());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await waitFor(() => expect(mockApiClient.runAutomationBootstrap).toHaveBeenCalled());

    expect(result.current.allExpenses).toHaveLength(1);
    expect(result.current.exportUrl).toBe("/export");
    expect(result.current.reportUrl).toBe("/report");

    act(() => {
      result.current.selectExpense(result.current.allExpenses[0]);
      result.current.setForm({ date: "2026-03-02", category: "Travel", description: "Bus", amount: "4.20", entry_type: "expense" });
      result.current.setSearchId("");
    });

    await act(async () => {
      await result.current.searchExpenseById();
      await result.current.createExpense();
      await result.current.updateExpense();
      await result.current.deleteExpense();
      result.current.setSearchId("1");
      await result.current.searchExpenseById();
      await result.current.importExpenses(new File(["csv"], "import.csv", { type: "text/csv" }));
      await result.current.predictNextMonth();
      result.current.setRagQuestionDraft("What changed?");
      await result.current.runRagQuery();
      await result.current.reindexRagKnowledge();
      result.current.checkBudgetStatus();
      result.current.showAllRecords();
      result.current.setBudgetDraft("1200");
      await result.current.saveMonthlyBudget();
      result.current.setIncomeDraft("2400");
      result.current.setIncomeMonthDraft("2026-03");
      await result.current.saveMonthlyIncome();
      await result.current.createRecurringItem({ category: "Subscriptions", description: "Gym", amount: "30.00", entry_type: "expense", frequency: "monthly", start_date: "2026-03-28", end_date: "", active: true });
      await result.current.updateRecurringItem(1, { category: "Housing", description: "Updated rent", amount: "725.00", entry_type: "expense", frequency: "monthly", start_date: "2026-03-01", end_date: "", active: true });
      await result.current.deleteRecurringItem(1);
      await result.current.markRecurringOccurrencePaid(1, "2026-04-01", 77);
      await result.current.markRecurringOccurrenceUnpaid(1, "2026-04-01");
      result.current.setAgentTaskDraft("Prepare a finance briefing");
      await result.current.runFinanceBriefingAgent();
      await result.current.runAutomationWorkflow("month_end_close");
      await result.current.sendUpcomingBillsEmailNow();
      await result.current.sendMonthEndEmailNow();
      await result.current.refresh();
    });

    expect(result.current.prediction?.next_month).toBe("April 2026");
    expect(result.current.agentBriefing?.headline).toBe("Finance briefing");
    expect(result.current.ragAnswer?.confidence).toBe("high");
    expect(result.current.ragStatus?.chunk_count).toBeGreaterThanOrEqual(36);
    expect(mockApiClient.reindexRag).toHaveBeenCalledWith(true);
    expect(mockApiClient.sendMonthEndEmailNow).toHaveBeenCalled();
    expect(mockApiClient.runAutomationRefresh).toHaveBeenCalled();
  });



  it("reports pluralized rag source counts on successful queries", async () => {
    mockApiClient.listAgentWorkflows.mockResolvedValue([]);
    mockApiClient.runAutomationBootstrap.mockResolvedValue([]);
    mockApiClient.queryRag.mockResolvedValue({
      question: "What changed?",
      answer: "Housing and travel are the main drivers.",
      confidence: "high",
      follow_up_questions: [],
      sources: [
        { source_label: "Dashboard March 2026", doc_type: "dashboard", document_id: "dashboard::2026-03", excerpt: "Budget.", score: 0.95, metadata: {} },
        { source_label: "Recurring #1", doc_type: "recurring", document_id: "recurring::1", excerpt: "Rent.", score: 0.91, metadata: {} },
      ],
      generated_at: "2026-04-15T09:10:00Z",
    });

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setRagQuestionDraft("What changed?");
    });
    await act(async () => {
      await result.current.runRagQuery();
    });

    expect(result.current.statusMessage).toBe("RAG answer generated from 2 knowledge chunks.");
  });
  it("covers rag validation, rag failures, and no-op reindex messaging", async () => {
    mockApiClient.listAgentWorkflows.mockResolvedValue([]);
    mockApiClient.runAutomationBootstrap.mockResolvedValue([]);
    mockApiClient.queryRag.mockRejectedValue(new Error("RAG failed"));
    mockApiClient.reindexRag
      .mockRejectedValueOnce(new Error("Reindex failed"))
      .mockResolvedValueOnce({
        available: true,
        collection_name: "monetra-finance-knowledge",
        indexed_at: "2026-04-15T09:20:00Z",
        document_count: 12,
        chunk_count: 36,
        signature: "sig",
        reindexed: false,
      });

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setRagQuestionDraft("   ");
    });
    await act(async () => {
      await result.current.runRagQuery();
    });
    expect(result.current.errorMessage).toBe("Enter a finance question before querying the knowledge base.");

    act(() => {
      result.current.setRagQuestionDraft("What changed?");
    });
    await act(async () => {
      await result.current.runRagQuery();
    });
    expect(result.current.errorMessage).toBe("RAG failed");

    await act(async () => {
      await result.current.reindexRagKnowledge();
    });
    expect(result.current.errorMessage).toBe("Reindex failed");

    await act(async () => {
      await result.current.reindexRagKnowledge();
    });
    expect(result.current.statusMessage).toBe("Knowledge base is already up to date.");
  });  it("surfaces validation and request errors for guarded actions", async () => {
    mockApiClient.listAgentWorkflows.mockResolvedValue([]);
    mockApiClient.runAutomationBootstrap.mockResolvedValue([]);
    mockApiClient.createExpense.mockRejectedValue(new Error("Create failed"));
    mockApiClient.sendUpcomingBillsEmailNow.mockRejectedValue(new Error("SMTP unavailable"));

    const { result } = renderHook(() => useBudgetTracker());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.updateExpense();
    });
    expect(result.current.errorMessage).toBe("Select an expense before updating.");

    await act(async () => {
      await result.current.deleteExpense();
    });
    expect(result.current.errorMessage).toBe("Select an expense before deleting.");

    act(() => {
      result.current.setSearchId("999");
      result.current.setForm({ date: "2026-03-02", category: "Travel", description: "Bus", amount: "4.20", entry_type: "expense" });
    });

    await act(async () => {
      await result.current.searchExpenseById();
    });
    expect(result.current.errorMessage).toBe("Expense #999 was not found for your account.");
    expect(result.current.expenses).toEqual([]);

    await act(async () => {
      await result.current.createExpense();
    });
    expect(result.current.errorMessage).toBe("Create failed");

    await act(async () => {
      await result.current.sendUpcomingBillsEmailNow();
    });
    expect(result.current.errorMessage).toBe("SMTP unavailable");
  });
});







