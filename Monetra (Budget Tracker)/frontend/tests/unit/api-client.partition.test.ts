describe("apiClient partitions", () => {
  beforeEach(() => {
    jest.resetModules();
    global.fetch = jest.fn();
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:5000";
  });

  it("builds export and report urls with the configured base url", async () => {
    const { apiClient } = await import("@/lib/api-client");

    expect(apiClient.exportExpenses()).toBe("http://127.0.0.1:5000/api/expenses/export");
    expect(apiClient.downloadMonthlyReport()).toBe("http://127.0.0.1:5000/api/reports/monthly");
    expect(apiClient.downloadMonthlyReport("2026-05")).toBe("http://127.0.0.1:5000/api/reports/monthly?month=2026-05");
  });

  it("builds recurring calendar requests for different day partitions", async () => {
    const { apiClient } = await import("@/lib/api-client");
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ data: { window_start: "2026-03-01", window_end: "2026-03-21", occurrences: [], completed_occurrences: [] } }),
    });

    await apiClient.getRecurringCalendar(14);

    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:5000/api/recurring-items/calendar?days=14",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("throws a clear import failure when csv upload is rejected", async () => {
    const { apiClient } = await import("@/lib/api-client");
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: async () => ({ error: "CSV file is required." }),
    });

    await expect(
      apiClient.importExpenses(new File(["csv"], "expenses.csv", { type: "text/csv" })),
    ).rejects.toThrow("CSV file is required.");
  });

  it("posts AI agent requests to the finance briefing endpoint", async () => {
    const { apiClient } = await import("@/lib/api-client");
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ data: { id: "job-1", status: "queued", task: "Prepare a finance briefing", created_at: "2026-03-21T10:00:00Z", started_at: null, completed_at: null, error: null, result: null } }),
    });

    await apiClient.startFinanceBriefingAgent("Prepare a finance briefing");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:5000/api/agents/finance-briefing",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ task: "Prepare a finance briefing" }),
      }),
    );
  });
});
