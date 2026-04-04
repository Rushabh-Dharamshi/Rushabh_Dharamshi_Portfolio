import { apiClient } from "@/lib/api-client";

describe("apiClient strict coverage", () => {
  let errorSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.resetModules();
    global.fetch = jest.fn();
    errorSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    errorSpy.mockRestore();
  });

  it("covers remaining JSON wrapper endpoints", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ data: { ok: true } }),
    });

    await apiClient.searchExpenseById(9);
    await apiClient.createExpense({ date: "2026-04-03", category: "Travel", description: "Bus", amount: "4.50", entry_type: "expense" });
    await apiClient.updateExpense(9, { date: "2026-04-03", category: "Travel", description: "Bus", amount: "5.00", entry_type: "expense" });
    await apiClient.getCategoryInsights();
    await apiClient.getWordCloud();
    await apiClient.getFinancialPulse();
    await apiClient.getPrediction();

    expect((global.fetch as jest.Mock).mock.calls.some((call) => String(call[0]).includes("/api/expenses/9"))).toBe(true);
    expect((global.fetch as jest.Mock).mock.calls.some((call) => String(call[0]).includes("/api/analytics/wordcloud"))).toBe(true);
    expect((global.fetch as jest.Mock).mock.calls.some((call) => String(call[0]).includes("/api/predictions/next-month"))).toBe(true);
  });

  it("logs and rethrows network request failures", async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error("offline"));

    await expect(
      apiClient.updateExpense(4, { date: "2026-04-03", category: "Travel", description: "Bus", amount: "5.00", entry_type: "expense" }),
    ).rejects.toThrow("offline");

    expect(errorSpy).toHaveBeenCalledWith(
      "[Monetra API] Network request failed.",
      expect.objectContaining({ method: "PUT", path: "/api/expenses/4" }),
    );
  });

  it("logs and rethrows import network failures", async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error("upload offline"));

    await expect(
      apiClient.importExpenses(new File(["csv"], "expenses.csv", { type: "text/csv" })),
    ).rejects.toThrow("upload offline");

    expect(errorSpy).toHaveBeenCalledWith(
      "[Monetra API] Import request failed.",
      expect.objectContaining({ method: "POST", path: "/api/expenses/import" }),
    );
  });

  it("covers default-argument and fallback error branches", async () => {
    (global.fetch as jest.Mock)
      .mockRejectedValueOnce("offline string")
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        headers: { get: () => "application/json" },
        json: async () => ({ error: null }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        headers: { get: () => "application/json" },
        json: async () => ({ error: null }),
      })
      .mockResolvedValue({
        ok: true,
        headers: { get: () => "application/json" },
        json: async () => ({ data: { ok: true } }),
      });

    await expect(apiClient.login("Rushabh", "secret")).rejects.toBe("offline string");
    expect(errorSpy).toHaveBeenCalledWith(
      "[Monetra API] Network request failed.",
      expect.objectContaining({ error: "offline string" }),
    );

    await expect(apiClient.deleteExpense(1)).rejects.toThrow("Request failed.");
    await expect(apiClient.importExpenses(new File(["csv"], "expenses.csv", { type: "text/csv" }))).rejects.toThrow("Import failed.");

    await apiClient.getSettings();
    await apiClient.updateMonthlyIncome(2400);
    await apiClient.getRecurringCalendar();
    await apiClient.listAgentRuns();
    await apiClient.startAgentWorkflow("month_end_close");
  });
});
