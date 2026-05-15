import { act, renderHook, waitFor } from "@testing-library/react";

import { useBudgetTracker } from "@/hooks/use-budget-tracker";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    listExpenses: jest.fn().mockResolvedValue([
      {
        id: 1,
        date: "2026-03-01",
        category: "Food",
        description: "Groceries",
        amount: 20.5,
        entry_type: "expense",
      },
    ]),
    searchExpenseById: jest.fn().mockResolvedValue({
      id: 1,
      date: "2026-03-01",
      category: "Food",
      description: "Groceries",
      amount: 20.5,
      entry_type: "expense",
    }),
    createExpense: jest.fn().mockResolvedValue({
      id: 2,
      date: "2026-03-02",
      category: "Travel",
      description: "Bus",
      amount: 4.2,
      entry_type: "expense",
    }),
    updateExpense: jest.fn().mockResolvedValue({}),
    deleteExpense: jest.fn().mockResolvedValue({ message: "deleted" }),
    importExpenses: jest.fn().mockResolvedValue({ imported_rows: 1, skipped_rows: 0 }),
    exportExpenses: jest.fn().mockReturnValue("/export"),
    downloadMonthlyReport: jest.fn().mockReturnValue("/report"),
    getSettings: jest.fn().mockResolvedValue({ monthly_budget: 1050, monthly_income: 1500, income_month: "2026-03" }),
    getDashboard: jest.fn().mockResolvedValue({
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
    }),
    getCategoryInsights: jest.fn().mockResolvedValue({
      top_categories: [{ category: "Food", amount: 220 }],
      bottom_categories: [{ category: "Travel", amount: 80 }],
      total_spending: 300,
    }),
    getWordCloud: jest.fn().mockResolvedValue({
      top_category: "Food",
      frequencies: [{ label: "Groceries", value: 220 }],
    }),
    getFinancialPulse: jest.fn().mockResolvedValue({
      health_score: 82,
      average_transaction: 25,
      transaction_count: 4,
      spend_velocity: 14.2,
      top_category_share: 42,
      runway_days: 18,
      narrative: "Steady spending rhythm.",
      cash_in: 1500,
      cash_out: 420,
      net_cash_flow: 1080,
      income_coverage: 357.14,
      recent_transactions: [],
      recent_expenses: [],
    }),
    getPrediction: jest.fn().mockResolvedValue({
      next_month: "April 2026",
      predicted_spending: 880,
      is_budget_exceeded: false,
      monthly_budget: 1050,
    }),
    getRagStatus: jest.fn().mockResolvedValue({
      collection_name: "monetra-finance-knowledge",
      embedding_model: "nomic-embed-text",
      is_indexed: true,
      document_count: 4,
      chunk_count: 8,
      last_indexed_at: "2026-03-21T09:00:00Z",
      manifest_version: "2026-03-21T09:00:00Z",
      reindexed: false,
    }),
    queryRag: jest.fn().mockResolvedValue({
      answer: "Spending is concentrated in groceries and recurring housing costs.",
      confidence: "high",
      sources: [],
      follow_up_questions: [],
    }),
    reindexRag: jest.fn().mockResolvedValue({
      collection_name: "monetra-finance-knowledge",
      embedding_model: "nomic-embed-text",
      is_indexed: true,
      document_count: 4,
      chunk_count: 8,
      last_indexed_at: "2026-03-21T09:05:00Z",
      manifest_version: "2026-03-21T09:05:00Z",
      reindexed: true,
    }),
    startFinanceBriefingAgent: jest.fn().mockResolvedValue({
      id: "job-1",
      status: "queued",
      task: "Prepare a finance briefing",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: null,
    }),
    getFinanceBriefingJob: jest.fn().mockResolvedValue({
      id: "job-1",
      status: "completed",
      task: "Prepare a finance briefing",
      created_at: "2026-03-21T10:00:00Z",
      started_at: "2026-03-21T10:00:01Z",
      completed_at: "2026-03-21T10:00:05Z",
      error: null,
      result: {
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
    }),
    listAgentWorkflows: jest.fn().mockResolvedValue([
      {
        id: "month_end_close",
        label: "Month-end close",
        description: "Generate the monthly report and review KPIs.",
        automation_focus: "Automates month-end reporting.",
        default_task: "Run the month-end close workflow.",
      },
    ]),
    listAgentRuns: jest.fn().mockResolvedValue([]),
    runAutomationBootstrap: jest.fn().mockResolvedValue([]),
    startAgentWorkflow: jest.fn().mockResolvedValue({
      id: "workflow-job-1",
      status: "queued",
      workflow_name: "month_end_close",
      task: "Run the workflow",
      created_at: "2026-03-21T10:00:00Z",
      started_at: null,
      completed_at: null,
      error: null,
      result: null,
    }),
    getAgentWorkflowJob: jest.fn().mockResolvedValue({
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
        recommended_actions: ["Share the pack with stakeholders."],
        automated_actions: ["Generated a fresh monthly PDF report for distribution."],
        email_subject: "Month-end pack ready",
        email_draft: "The report and summary are ready.",
        task: "Run the workflow",
        model: "mistral:latest",
        tools_used: ["generate_monthly_report"],
        report_download_url: "/api/reports/monthly",
        generated_at: "2026-03-21T10:00:00Z",
      },
    }),
    listRecurringItems: jest.fn().mockResolvedValue([]),
    getRecurringCalendar: jest.fn().mockResolvedValue({
      window_start: "2026-03-01",
      window_end: "2026-04-04",
      occurrences: [],
      completed_occurrences: [],
    }),
    updateMonthlyBudget: jest.fn().mockResolvedValue({ monthly_budget: 1200, monthly_income: 1500 }),
    updateMonthlyIncome: jest.fn().mockResolvedValue({ monthly_budget: 1200, monthly_income: 2400, income_month: "2026-03" }),
    createRecurringItem: jest.fn().mockResolvedValue({ id: 1 }),
    updateRecurringItem: jest.fn().mockResolvedValue({}),
    deleteRecurringItem: jest.fn().mockResolvedValue({ message: "deleted" }),
    markRecurringOccurrencePaid: jest.fn().mockResolvedValue({ message: "Reminder marked as paid for this date." }),
    markRecurringOccurrenceUnpaid: jest.fn().mockResolvedValue({ message: "Reminder restored for this date." }),
  },
}));

describe("useBudgetTracker", () => {
  it("loads data and supports user actions", async () => {
    const { result } = renderHook(() => useBudgetTracker());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.allExpenses).toHaveLength(1);
    expect(result.current.expenses).toHaveLength(1);
    expect(result.current.financialPulse?.health_score).toBe(82);

    act(() => {
      result.current.setForm({
        date: "2026-03-02",
        category: "Travel",
        description: "Bus",
        amount: "4.20",
        entry_type: "expense",
      });
    });
    await act(async () => {
      await result.current.createExpense();
      result.current.setSearchId("1");
      await result.current.searchExpenseById();
      await result.current.predictNextMonth();
      result.current.setAgentTaskDraft("Prepare a finance briefing");
      await result.current.runFinanceBriefingAgent();
      result.current.checkBudgetStatus();
      result.current.showAllRecords();
      result.current.setBudgetDraft("1200");
      await result.current.saveMonthlyBudget();
      result.current.setIncomeDraft("2400");
      result.current.setIncomeMonthDraft("2026-03");
      await result.current.saveMonthlyIncome();
      await result.current.importExpenses(
        new File(["csv"], "import.csv", { type: "text/csv" }),
      );
    });

    expect(result.current.prediction?.next_month).toBe("April 2026");
    expect(result.current.agentBriefing?.headline).toBe("Local finance briefing");
    expect(result.current.exportUrl).toBe("/export");
    expect(result.current.budgetDraft).toBe("1050.00");
    expect(result.current.incomeDraft).toBe("1500.00");

    await act(async () => {
      await result.current.runAutomationWorkflow("month_end_close");
    });

    expect(result.current.agentRuns[0]?.workflow_name).toBe("month_end_close");
  });
});





