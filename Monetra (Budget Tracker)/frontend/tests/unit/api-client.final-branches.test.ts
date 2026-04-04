import { apiClient } from "@/lib/api-client";

describe("apiClient final branch coverage", () => {
  let errorSpy: jest.SpyInstance;

  beforeEach(() => {
    global.fetch = jest.fn();
    errorSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    errorSpy.mockRestore();
    delete (Object.prototype as Record<string, unknown>).headers;
  });

  it("returns raw responses for non-json payloads", async () => {
    const response = {
      ok: true,
      headers: { get: () => "text/csv" },
      json: async () => ({ data: { ignored: true } }),
    };
    (global.fetch as jest.Mock).mockResolvedValue(response);

    const result = await apiClient.getAuthSession();

    expect(result).toBe(response);
  });

  it("logs string-based import request failures", async () => {
    (global.fetch as jest.Mock).mockRejectedValue("offline string");

    await expect(apiClient.importExpenses(new File(["csv"], "expenses.csv", { type: "text/csv" }))).rejects.toBe("offline string");
    expect(errorSpy).toHaveBeenCalledWith(
      "[Monetra API] Import request failed.",
      expect.objectContaining({ error: "offline string" }),
    );
  });

  it("covers inherited request headers and missing content-type branches", async () => {
    Object.defineProperty(Object.prototype, "headers", {
      configurable: true,
      get() {
        return { "X-Test-Header": "present" };
      },
      set() {},
    });

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      headers: { get: () => null },
      json: async () => ({ data: { ignored: true } }),
    });

    const response = await apiClient.createExpense({
      date: "2026-04-03",
      category: "Travel",
      description: "Tube",
      amount: "6.40",
      entry_type: "expense",
    });

    expect(response).toEqual(
      expect.objectContaining({
        headers: expect.objectContaining({ get: expect.any(Function) }),
      }),
    );

    const requestOptions = (global.fetch as jest.Mock).mock.calls[0][1] as Record<string, unknown>;
    const mergedHeaders =
      (requestOptions.headers as Record<string, unknown> | undefined) ??
      (Object.getPrototypeOf(requestOptions).headers as Record<string, unknown> | undefined);

    expect(mergedHeaders).toEqual(
      expect.objectContaining({
        "X-Test-Header": "present",
      }),
    );
  });

  it("covers unreadable json fallback handlers for request and import paths", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: false,
        headers: { get: () => "application/json" },
        json: async () => {
          throw new Error("broken json");
        },
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error("broken json");
        },
      });

    await expect(apiClient.getDashboard()).rejects.toThrow("Request failed.");
    await expect(
      apiClient.importExpenses(new File(["csv"], "expenses.csv", { type: "text/csv" })),
    ).resolves.toBeUndefined();
  });
});
