describe("apiClient", () => {
  beforeEach(() => {
    jest.resetModules();
    global.fetch = jest.fn();
  });

  it("parses JSON responses", async () => {
    const { apiClient } = await import("@/lib/api-client");
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ data: [{ id: 1 }] }),
    });

    await expect(apiClient.listExpenses()).resolves.toEqual([{ id: 1 }]);
  });

  it("throws backend errors", async () => {
    const { apiClient } = await import("@/lib/api-client");
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      headers: { get: () => "application/json" },
      json: async () => ({ error: "Bad request" }),
    });

    await expect(apiClient.getDashboard()).rejects.toThrow("Bad request");
  });

  it("uploads csv files via form data", async () => {
    const { apiClient } = await import("@/lib/api-client");
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ data: { imported_rows: 2, skipped_rows: 0 } }),
    });

    const file = new File(["date,category,description,amount"], "expenses.csv", {
      type: "text/csv",
    });

    await expect(apiClient.importExpenses(file)).resolves.toEqual({
      imported_rows: 2,
      skipped_rows: 0,
    });
  });
});

