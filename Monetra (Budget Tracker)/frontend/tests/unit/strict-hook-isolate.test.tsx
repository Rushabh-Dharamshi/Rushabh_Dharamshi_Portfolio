describe("frontend strict hook isolate coverage", () => {
  afterEach(() => {
    jest.resetModules();
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  it("covers current-month fallback, action-result reloads, and workflow fallback errors", async () => {
    jest.useFakeTimers().setSystemTime(new Date("2026-04-18T12:00:00Z"));

    const mockApiClient = {
      listExpenses: jest.fn().mockResolvedValue([]),
      searchExpenseById: jest.fn(),
      createExpense: jest.fn(),
      updateExpense: jest.fn(),
      deleteExpense: jest.fn(),
      importExpenses: jest.fn(),
      exportExpenses: jest.fn().mockReturnValue("/export"),
      downloadMonthlyReport: jest.fn().mockReturnValue("/report"),
      getSettings: jest.fn().mockResolvedValue({ monthly_budget: 1050, monthly_income: 1500, income_month: null }),
      listMonthlyIncomeRecords: jest.fn().mockResolvedValue([]),
      getDashboard: jest.fn().mockResolvedValue({ monthly_budget: 1050, current_month_total: 420, monthly_expenses: 420, monthly_income: 1500, net_cash_flow: 1080, remaining_budget: 630, weekly_spending: 84.5, percent_spent: 40, status: "within", month_label: "April 2026", month_key: "2026-04", income_month: null }),
      getCategoryInsights: jest.fn().mockResolvedValue({ top_categories: [], bottom_categories: [], total_spending: 0 }),
      getWordCloud: jest.fn().mockResolvedValue({ top_category: null, frequencies: [] }),
      getFinancialPulse: jest.fn().mockResolvedValue({ health_score: 80, average_transaction: 20, transaction_count: 1, spend_velocity: 10, top_category_share: 50, runway_days: 12, narrative: "Stable", cash_in: 1500, cash_out: 420, net_cash_flow: 1080, income_coverage: 300, recent_transactions: [], recent_expenses: [] }),
      listRecurringItems: jest.fn().mockResolvedValue([]),
      getRecurringCalendar: jest.fn().mockResolvedValue({ window_start: "2026-04-01", window_end: "2026-05-06", occurrences: [], completed_occurrences: [] }),
      listAgentWorkflows: jest.fn().mockResolvedValue([{ id: "month_end_close", label: "Month-end close", description: "desc", automation_focus: "focus", default_task: "run" }]),
      listAgentRuns: jest.fn().mockResolvedValue([]),
      runAutomationBootstrap: jest.fn().mockResolvedValue([]),
      runAutomationRefresh: jest.fn().mockResolvedValue([]),
      getPrediction: jest.fn(),
      getLatencyReport: jest.fn().mockResolvedValue({
        scope: "current_user",
        record_count: 0,
        failed_count: 0,
        summary: { average_ms: 0, minimum_ms: 0, maximum_ms: 0, p95_ms: 0 },
        by_endpoint: [],
        latest: [],
      }),
      recordClientFailure: jest.fn().mockResolvedValue({ recorded: true }),
      getRagStatus: jest.fn().mockResolvedValue({ available: true, collection_name: "monetra-finance-knowledge", indexed_at: null, document_count: 0, chunk_count: 0, signature: null }),
      reindexRag: jest.fn(),
      queryRag: jest.fn(),
      updateMonthlyBudget: jest.fn(),
      updateMonthlyIncome: jest.fn(),
      createRecurringItem: jest.fn(),
      updateRecurringItem: jest.fn(),
      deleteRecurringItem: jest.fn(),
      markRecurringOccurrencePaid: jest.fn(),
      markRecurringOccurrenceUnpaid: jest.fn(),
      sendUpcomingBillsEmailNow: jest.fn(),
      sendAllUpcomingBillsEmailNow: jest.fn(),
      sendMonthEndEmailNow: jest.fn(),
      startFinanceBriefingAgent: jest.fn().mockResolvedValue({ id: "brief-1" }),
      getFinanceBriefingJob: jest
        .fn()
        .mockResolvedValueOnce({
          id: "brief-1",
          status: "completed",
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
        }),
      startAgentWorkflow: jest.fn().mockResolvedValue({ id: "wf-1" }),
      getAgentWorkflowJob: jest.fn().mockResolvedValue({ id: "wf-1", status: "failed", error: null, result: null }),
    };

    let renderHookLocal!: typeof import("@testing-library/react").renderHook;
    let waitForLocal!: typeof import("@testing-library/react").waitFor;
    let actLocal!: typeof import("@testing-library/react").act;
    let useBudgetTracker!: typeof import("@/hooks/use-budget-tracker").useBudgetTracker;

    jest.isolateModules(() => {
      jest.doMock("@/lib/api-client", () => ({ apiClient: mockApiClient }));
      const reactModule = require("react");
      const realUseState = jest.requireActual("react").useState;
      let callCount = 0;
      jest.spyOn(reactModule, "useState").mockImplementation((initial: unknown) => {
        callCount += 1;
        if (callCount === 28) {
          return realUseState(null);
        }
        return realUseState(initial);
      });

      ({ renderHook: renderHookLocal, waitFor: waitForLocal, act: actLocal } = require("@testing-library/react/pure"));
      useBudgetTracker = require("@/hooks/use-budget-tracker").useBudgetTracker;
    });

    const { result } = renderHookLocal(() => useBudgetTracker());
    await waitForLocal(() => expect(result.current.isLoading).toBe(false));

    expect(mockApiClient.getSettings).toHaveBeenCalledWith("2026-04");

    await actLocal(async () => {
      await result.current.runFinanceBriefingAgent();
    });
    expect(mockApiClient.runAutomationRefresh).not.toHaveBeenCalled();

    await actLocal(async () => {
      await result.current.runAutomationWorkflow("month_end_close");
    });
    expect(result.current.errorMessage).toBe("The month_end_close workflow failed.");
  });
});



