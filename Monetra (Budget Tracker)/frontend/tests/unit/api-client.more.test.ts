import { apiClient } from "@/lib/api-client";

describe("apiClient additional coverage", () => {
  beforeEach(() => {
    (global.fetch as jest.Mock | undefined)?.mockReset?.();
    global.fetch = jest.fn();
  });

  it("covers auth, settings, recurring, agent, and email endpoints", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ data: { authenticated: true, username: "Rushabh" } }),
    });

    await expect(apiClient.getAuthSession()).resolves.toEqual({ authenticated: true, username: "Rushabh" });
    await apiClient.login("Rushabh", "secret");
    await apiClient.logout();
    await apiClient.getSettings("2026-03");
    await apiClient.updateMonthlyBudget(1050);
    await apiClient.updateMonthlyIncome(1500, "2026-03");
    await apiClient.listRecurringItems();
    await apiClient.getRecurringCalendar(45);
    await apiClient.createRecurringItem({ category: "Bills", description: "Utility", amount: "24.51", entry_type: "expense", frequency: "monthly", start_date: "2026-04-23", end_date: "2026-06-23", active: true });
    await apiClient.updateRecurringItem(1, { category: "Bills", description: "Utility", amount: "24.51", entry_type: "expense", frequency: "monthly", start_date: "2026-04-23", end_date: "", active: true });
    await apiClient.deleteRecurringItem(1);
    await apiClient.markRecurringOccurrencePaid(1, "2026-04-23", 99);
    await apiClient.markRecurringOccurrenceUnpaid(1, "2026-04-23");
    await apiClient.startFinanceBriefingAgent("brief me");
    await apiClient.getFinanceBriefingJob("job-1");
    await apiClient.listAgentWorkflows();
    await apiClient.listAgentRuns(12);
    await apiClient.startAgentWorkflow("month_end_close", "run now");
    await apiClient.getAgentWorkflowJob("workflow-1");
    await apiClient.runAutomationBootstrap();
    await apiClient.runAutomationRefresh("expense_created");
    await apiClient.sendUpcomingBillsEmailNow();
    await apiClient.sendMonthEndEmailNow();

    expect((global.fetch as jest.Mock).mock.calls.some((call) => String(call[0]).includes("/api/auth/login"))).toBe(true);
    expect((global.fetch as jest.Mock).mock.calls.some((call) => String(call[0]).includes("/api/recurring-items/calendar?days=45"))).toBe(true);
    expect((global.fetch as jest.Mock).mock.calls.some((call) => String(call[0]).includes("/api/agents/automation/month-end-email"))).toBe(true);
  });

  it("returns raw response objects for non-json endpoints", async () => {
    const response = {
      ok: true,
      headers: { get: () => "text/csv" },
      blob: jest.fn(),
    };
    (global.fetch as jest.Mock).mockResolvedValue(response);

    await expect(apiClient.deleteExpense(12)).resolves.toBe(response as never);
  });
});
