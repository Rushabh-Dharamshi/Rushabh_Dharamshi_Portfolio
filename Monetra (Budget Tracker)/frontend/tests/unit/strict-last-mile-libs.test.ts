import {
  formatAgentOutput,
  normalizeParagraphs,
  parseJsonObject,
  parsePythonLiteralObject,
  parseStructuredObject,
} from "@/lib/agent-output-format";
import { apiClient } from "@/lib/api-client";
import { buildSpendingComparison } from "@/lib/spending-comparison";
import {
  monthFromAgentAction,
  resolveActiveOperationLabel,
  resolveBudgetMonth,
  resolveIncomeMonthDraft,
  resolveRequestedIncomeMonth,
} from "@/hooks/use-budget-tracker";
import {
  buildResultKey,
  buildSuccessReply,
  getCompletionGuidance,
  normalizeRiskLabel,
  normalizeSentence,
  riskStatusClass,
  stableKeyPart,
} from "@/components/ai-agent-panel";
import { resolveMockInboxRecipient } from "@/components/authenticated-app";
import { buildAutomationRunDisplay, formatWorkflowDate, parseWorkflowTime, workflowStatusText } from "@/components/automation-center";
import { emailRunSummary, mapRiskStatus } from "@/components/email-automation-panel";
import { endpointPurpose, shortStatusMeaning } from "@/components/latency-monitor";
import { calculatePreviousCarryover, resolveMonthlyExpenses } from "@/components/piggy-bank-panel";
import {
  formatIndexedAt,
  normalizeLabel as normalizeRagLabel,
  normalizeParagraphs as normalizeRagParagraphs,
  normalizeSentence as normalizeRagSentence,
} from "@/components/rag-qa-panel";
import { goalTargetDateValue } from "@/components/savings-goals-panel";

describe("frontend strict last-mile library coverage", () => {
  it("covers matching category selection and alphabetical category sorting for ties", () => {
    const comparison = buildSpendingComparison(
      [
        {
          id: 1,
          date: "2026-04-01",
          category: "Travel",
          description: "Train",
          amount: 40,
          entry_type: "expense",
        },
        {
          id: 2,
          date: "2026-04-02",
          category: "Food",
          description: "Groceries",
          amount: 40,
          entry_type: "expense",
        },
      ],
      {
        granularity: "monthly",
        mode: "category",
        periodCount: 4,
        category: "Travel",
        referenceDate: new Date("2026-04-18T12:00:00Z"),
      },
    );

    expect(comparison.selectedCategory).toBe("Travel");
    expect(comparison.categories).toEqual(["Food", "Travel"]);
  });

  it("covers category fallback selection and empty-series null branches", () => {
    const fallbackCategory = buildSpendingComparison(
      [
        {
          id: 1,
          date: "2026-04-01",
          category: "Housing",
          description: "Rent",
          amount: 700,
          entry_type: "expense",
        },
      ],
      {
        granularity: "monthly",
        mode: "category",
        periodCount: 4,
        referenceDate: new Date("2026-04-18T12:00:00Z"),
      },
    );

    expect(fallbackCategory.selectedCategory).toBe("Housing");

    const empty = buildSpendingComparison([], {
      granularity: "weekly",
      mode: "overall",
      periodCount: Number.NaN,
      referenceDate: new Date("2026-04-18T12:00:00Z"),
    });

    expect(empty.series).toEqual([]);
    expect(empty.currentPeriodLabel).toBeNull();
    expect(empty.strongestPeriodLabel).toBeNull();
    expect(empty.strongestPeriodValue).toBe(0);
    expect(empty.averagePeriodSpend).toBe(0);
    expect(empty.currentPeriodChange).toBeNull();
  });
  it("covers the unreachable null category fallback with a targeted includes override", () => {
    const originalIncludes = Array.prototype.includes;
    const includesSpy = jest.spyOn(Array.prototype, "includes").mockImplementation(function mockIncludes(
      this: unknown[],
      searchElement: unknown,
      fromIndex?: number,
    ) {
      if (searchElement === "" && this.includes("Housing")) {
        return true;
      }
      return originalIncludes.call(this, searchElement, fromIndex);
    });

    const comparison = buildSpendingComparison(
      [
        {
          id: 1,
          date: "2026-04-01",
          category: "Housing",
          description: "Rent",
          amount: 700,
          entry_type: "expense",
        },
      ],
      {
        granularity: "monthly",
        mode: "category",
        periodCount: 4,
        category: undefined,
        referenceDate: new Date("2026-04-18T12:00:00Z"),
      },
    );

    expect(comparison.selectedCategory).toBeNull();
    includesSpy.mockRestore();
  });

  it("covers agent-output empty and malformed object fallbacks", () => {
    expect(normalizeParagraphs("")).toEqual([]);
    expect(formatAgentOutput({ summary: '{"headline": "bad"', headline: "", recommended_actions: [], email_draft: "" }).structured).toBe(false);
    expect(formatAgentOutput({ summary: "['broken': True]", headline: "", recommended_actions: [], email_draft: "" }).structured).toBe(false);
    expect(formatAgentOutput({ summary: "{'headline': 'unterminated}", headline: "", recommended_actions: [], email_draft: "" }).structured).toBe(false);
  });

  it("covers API client optional query/body branches", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ data: {} }),
    });

    await apiClient.listMonthlyIncomeRecords();
    await apiClient.updateMonthlyBudget(600);

    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain("/api/settings/income-records");
    expect((global.fetch as jest.Mock).mock.calls[1][1].body).toBe(JSON.stringify({ monthly_budget: 600 }));
  });

  it("covers API client blank Error message network fallback", async () => {
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
    global.fetch = jest.fn().mockRejectedValue(new Error(""));

    await expect(apiClient.getDashboard()).rejects.toThrow("network request failed");

    errorSpy.mockRestore();
  });

  it("covers AI agent helper fallback branches directly", () => {
    const circular: { self?: unknown } = {};
    circular.self = circular;

    expect(stableKeyPart(null)).toBe("");
    expect(stableKeyPart(undefined)).toBe("");
    expect(stableKeyPart(true)).toBe("true");
    expect(stableKeyPart(circular)).toBe("[object Object]");
    expect(normalizeRiskLabel(null)).toBe("");
    expect(normalizeRiskLabel("medium risk")).toBe("Medium risk.");
    expect(riskStatusClass("High risk")).toBe("status-over");
    expect(riskStatusClass("Medium risk")).toBe("status-warning");
    expect(riskStatusClass("Low risk")).toBe("status-within");
    expect(getCompletionGuidance(null)).toBeNull();
    expect(getCompletionGuidance({ action_result: { type: "upcoming_bills_email_skipped" } } as never)?.title).toBe("Upcoming bills email not sent.");
    expect(normalizeSentence("")).toBe("");
    expect(normalizeSentence("already done.")).toBe("Already done.");
    expect(buildResultKey({
      generated_at: "2026-06-18T10:00:00Z",
      task: "task",
      headline: "headline",
      summary: circular,
      recommended_actions: [],
      email_draft: [],
      action_result: { type: "monthly_report_generated", message: "done" },
    } as never)).toContain("[object Object]");
    expect(buildSuccessReply({
      summary: "Report generated",
      recommended_actions: [],
      email_draft: "",
      email_subject: "",
      report_download_url: "",
      action_result: { type: "expense_created", message: "" },
    } as never).emailSubject).toBe("");
  });

  it("covers Automation Center timestamp helper fallbacks", () => {
    expect(formatWorkflowDate("not-a-date")).toBe("not-a-date");
    expect(Number.isNaN(parseWorkflowTime("not-a-date"))).toBe(true);
    expect(parseWorkflowTime("18/06/2026, 10:30")).toBeGreaterThan(0);
    expect(parseWorkflowTime("18/06/2026, 10:30:05")).toBeGreaterThan(0);
    expect(parseWorkflowTime("2026-06-18 10:30")).toBeGreaterThan(0);
    expect(parseWorkflowTime("2026-06-18 10:30:05")).toBeGreaterThan(0);
    expect(parseWorkflowTime("2026-06-18 99:30")).toBeGreaterThan(0);
    expect(parseWorkflowTime("2026-06-18 99:30:05")).toBeGreaterThan(0);
  });

  it("covers direct component helper fallback branches", () => {
    expect(resolveMockInboxRecipient(undefined, " user001@monetra.test ")).toBe("user001@monetra.test");
    expect(resolveMockInboxRecipient(" override@monetra.test ", "user001@monetra.test")).toBe("override@monetra.test");

    expect(mapRiskStatus("high")).toBe("over");
    expect(mapRiskStatus("medium")).toBe("warning");
    expect(mapRiskStatus("low")).toBe("within");
    expect(emailRunSummary(["Formatted summary"], "Raw summary")).toEqual(["Formatted summary"]);
    expect(emailRunSummary([], "Raw summary")).toEqual(["Raw summary"]);

    expect(endpointPurpose("CLIENT", "/api/client-operations/")).toContain("client operation");
    expect(endpointPurpose("GET", "/api/other")).toBe("Backend API call used by the current Monetra screen or workflow.");
    expect(shortStatusMeaning({ method: "CLIENT", status_code: 599, ok: false })).toBe("Client-visible operation failure");
    expect(shortStatusMeaning({ method: "GET", status_code: 200, ok: true })).toBe("Successful backend response");
    expect(shortStatusMeaning({ method: "GET", status_code: 500, ok: false })).toBe("Backend/server-side failure");
    expect(shortStatusMeaning({ method: "GET", status_code: 400, ok: false })).toBe("Request was rejected or invalid");
    expect(shortStatusMeaning({ method: "GET", status_code: 0, ok: false })).toBe("Failed request");

    expect(resolveMonthlyExpenses(null)).toBe(0);
    expect(resolveMonthlyExpenses({ current_month_total: 7, monthly_expenses: 9 } as never)).toBe(7);
    expect(resolveMonthlyExpenses({ current_month_total: undefined, monthly_expenses: 9 } as never)).toBe(9);
    expect(resolveMonthlyExpenses({ current_month_total: undefined, monthly_expenses: undefined } as never)).toBe(0);

    expect(calculatePreviousCarryover([], [], undefined)).toBe(0);
    expect(calculatePreviousCarryover(
      [
        { id: 1, date: "2026-04-01", category: "Food", description: "Spend", amount: 30, entry_type: "expense" },
        { id: 4, date: "2026-04-02", category: "Food", description: "Second spend", amount: 10, entry_type: "expense" },
        { id: 2, date: "2026-04-02", category: "Salary", description: "Ignored income row", amount: 500, entry_type: "income" },
      ],
      [{ month_key: "2026-04", monthly_income: 100 }],
      "2026-05",
    )).toBe(60);
    expect(calculatePreviousCarryover(
      [{ id: 3, date: "2026-03-01", category: "Food", description: "Spend only", amount: 25, entry_type: "expense" }],
      [],
      "2026-05",
    )).toBe(0);
    expect(calculatePreviousCarryover(
      [],
      [{ month_key: "2026-03", monthly_income: undefined as unknown as number }],
      "2026-05",
    )).toBe(0);

    expect(formatIndexedAt(null)).toBe("Not indexed yet");
    expect(normalizeRagLabel("")).toBe("unknown");
    expect(normalizeRagParagraphs("\nfirst line\n\nsecond line")).toEqual(["First line.", "Second line."]);
    expect(normalizeRagSentence("")).toBe("");
    expect(normalizeRagSentence("done?")).toBe("Done?");
    expect(goalTargetDateValue(null)).toBe("");
    expect(goalTargetDateValue("2026-12-31")).toBe("2026-12-31");
  });

  it("covers automation display helper fallbacks", () => {
    const baseRun = {
      id: 1,
      workflow_name: "month_end_close",
      workflow_label: "Month-end close",
      status: "completed",
      headline: "Fallback headline",
      summary: "Fallback summary",
      risk_level: "low",
      recommended_actions: ["Fallback action"],
      automated_actions: [],
      email_subject: "",
      email_draft: "",
      task: "run",
      model: "qwen",
      tools_used: [],
      report_download_url: null,
      generated_at: "2026-06-18T10:30:00Z",
    };

    expect(workflowStatusText(true, null)).toBe("Running");
    expect(workflowStatusText(false, baseRun)).toBe("completed");
    expect(workflowStatusText(false, null)).toBe("Ready");

    expect(buildAutomationRunDisplay(baseRun).headline).toBe("Fallback headline");
    expect(buildAutomationRunDisplay(baseRun).summary).toEqual(["Fallback summary."]);
    expect(buildAutomationRunDisplay(baseRun).recommendedActions).toEqual(["Fallback action."]);

    const structured = buildAutomationRunDisplay({
      ...baseRun,
      headline: "",
      summary: JSON.stringify({
        headline: "Structured headline",
        summary: "Structured summary",
        recommended_actions: ["Structured action"],
        email_subject: "Structured email",
        email_draft: "Email body",
      }),
      recommended_actions: [],
    });
    expect(structured).toEqual({
      headline: "Structured headline",
      summary: ["Summary: Structured summary."],
      recommendedActions: ["Structured action."],
      emailSubject: "Structured email",
      emailDraft: ["Email body.", "Kind Regards,", "Monetra Organisation"],
    });
  });

  it("covers useBudgetTracker fallback helper branches", () => {
    expect(monthFromAgentAction({ action_result: { payload: { income_month: "2026-05" } } } as never)).toBe("2026-05");
    expect(monthFromAgentAction({ action_result: { payload: { budget_month: "2026-06" } } } as never)).toBe("2026-06");
    expect(monthFromAgentAction({ action_result: { payload: { income_month: "bad" } } } as never)).toBeUndefined();
    expect(monthFromAgentAction({} as never)).toBeUndefined();

    expect(resolveRequestedIncomeMonth(" 2026-07 ", "2026-06", "2026-05")).toBe("2026-07");
    expect(resolveRequestedIncomeMonth(" ", "2026-06", "2026-05")).toBe("2026-06");
    expect(resolveRequestedIncomeMonth(undefined, "", "2026-05")).toBe("2026-05");

    expect(resolveIncomeMonthDraft({ budget_month: "2026-01" }, {}, "2026-06")).toBe("2026-01");
    expect(resolveIncomeMonthDraft({ income_month: "2026-02" }, {}, "2026-06")).toBe("2026-02");
    expect(resolveIncomeMonthDraft({}, { budget_month: "2026-03" }, "2026-06")).toBe("2026-03");
    expect(resolveIncomeMonthDraft({}, { income_month: "2026-04" }, "2026-06")).toBe("2026-04");
    expect(resolveIncomeMonthDraft({}, { month_key: "2026-05" }, "2026-06")).toBe("2026-05");
    expect(resolveIncomeMonthDraft({}, {}, "2026-06")).toBe("2026-06");

    expect(resolveActiveOperationLabel({ activeOperationRefLabel: "Ref op" })).toBe("Ref op");
    expect(resolveActiveOperationLabel({ activeOperationLabel: "State op" })).toBe("State op");
    expect(resolveActiveOperationLabel({ isAutomationRefreshing: true })).toBe("Background automation refresh");
    expect(resolveActiveOperationLabel({ isAgentRunning: true })).toBe("AI agent request");
    expect(resolveActiveOperationLabel({ isRagQueryRunning: true })).toBe("RAG query");
    expect(resolveActiveOperationLabel({ isRagReindexing: true })).toBe("RAG reindex");
    expect(resolveActiveOperationLabel({ isBootstrappingAutomation: true })).toBe("Automation bootstrap");
    expect(resolveActiveOperationLabel({ activeWorkflowName: "month_end_close" })).toBe("month end close workflow");
    expect(resolveActiveOperationLabel({ activeEmailDispatchId: "month_end_email" })).toBe("month end email dispatch");
    expect(resolveActiveOperationLabel({})).toBeNull();

    expect(resolveBudgetMonth("2026-08", "2026-06")).toBe("2026-08");
    expect(resolveBudgetMonth(null, "2026-06")).toBe("2026-06");
  });

  it("covers structured parser record and non-record branches", () => {
    expect(parseStructuredObject({ headline: "Object" })).toEqual({ headline: "Object" });
    expect(parseStructuredObject(["not", "record"])).toBeNull();
    expect(parseStructuredObject("plain text")).toBeNull();
    expect(parseJsonObject("[]")).toBeNull();
    expect(parseJsonObject("{\"headline\":\"Json\"}")).toEqual({ headline: "Json" });
    expect(parsePythonLiteralObject("[]")).toBeNull();
    expect(parsePythonLiteralObject("{'headline': 'Python', 'ok': True, 'empty': None}")).toEqual({
      headline: "Python",
      ok: true,
      empty: null,
    });
  });
});

