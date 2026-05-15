import {
  AgentBriefingJob,
  AgentBriefingResponse,
  AgentWorkflowDefinition,
  AgentWorkflowJob,
  AgentWorkflowRun,
  AuthSessionResponse,
  CategoryInsightsResponse,
  DashboardSummary,
  Expense,
  ExpensePayload,
  FinancialPulseResponse,
  ImportResponse,
  PredictionResponse,
  RagAnswerResponse,
  RagStatusResponse,
  RecurringCalendarResponse,
  RecurringItem,
  RecurringItemPayload,
  SettingsResponse,
  WordCloudResponse,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function logApiFailure(message: string, details: Record<string, unknown>) {
  console.error(`[Monetra API] ${message}`, details);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method ?? "GET";
  const url = `${API_BASE_URL}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch (error) {
    logApiFailure("Network request failed.", {
      method,
      path,
      url,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: "Request failed." }));
    logApiFailure("Request returned a non-success status.", {
      method,
      path,
      url,
      status: response.status,
      payload,
    });
    throw new Error(payload.error ?? "Request failed.");
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  if (!isJson) {
    return response as unknown as T;
  }

  const payload = await response.json();
  return payload.data as T;
}

export const apiClient = {
  getAuthSession: () => request<AuthSessionResponse>("/api/auth/session"),
  login: (username: string, password: string) =>
    request<AuthSessionResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () =>
    request<{ message: string }>("/api/auth/logout", {
      method: "POST",
    }),
  listExpenses: () => request<Expense[]>("/api/expenses"),
  searchExpenseById: (expenseId: number) => request<Expense>(`/api/expenses/${expenseId}`),
  createExpense: (payload: ExpensePayload) =>
    request<Expense>("/api/expenses", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateExpense: (expenseId: number, payload: ExpensePayload) =>
    request<Expense>(`/api/expenses/${expenseId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteExpense: (expenseId: number) =>
    request<{ message: string }>(`/api/expenses/${expenseId}`, {
      method: "DELETE",
    }),
  importExpenses: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const path = "/api/expenses/import";
    const url = `${API_BASE_URL}${path}`;

    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        body: formData,
        credentials: "include",
      });
    } catch (error) {
      logApiFailure("Import request failed.", {
        method: "POST",
        path,
        url,
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }

    const payload = await response.json().catch(() => ({ error: "Import failed." }));
    if (!response.ok) {
      logApiFailure("Import request returned a non-success status.", {
        method: "POST",
        path,
        url,
        status: response.status,
        payload,
      });
      throw new Error(payload.error ?? "Import failed.");
    }
    return payload.data as ImportResponse;
  },
  exportExpenses: () => `${API_BASE_URL}/api/expenses/export`,
  downloadMonthlyReport: () => `${API_BASE_URL}/api/reports/monthly`,
  getDashboard: () => request<DashboardSummary>("/api/dashboard"),
  getCategoryInsights: () => request<CategoryInsightsResponse>("/api/analytics/categories"),
  getWordCloud: () => request<WordCloudResponse>("/api/analytics/wordcloud"),
  getFinancialPulse: () => request<FinancialPulseResponse>("/api/analytics/financial-pulse"),
  getPrediction: () => request<PredictionResponse>("/api/predictions/next-month"),
  getRagStatus: () => request<RagStatusResponse>("/api/rag/status"),
  reindexRag: (force = true) =>
    request<RagStatusResponse>("/api/rag/reindex", {
      method: "POST",
      body: JSON.stringify({ force }),
    }),
  queryRag: (question: string) =>
    request<RagAnswerResponse>("/api/rag/query", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  getSettings: (month?: string) => request<SettingsResponse>(month ? `/api/settings?month=${encodeURIComponent(month)}` : "/api/settings"),
  updateMonthlyBudget: (monthlyBudget: number) =>
    request<SettingsResponse>("/api/settings/budget", {
      method: "PUT",
      body: JSON.stringify({ monthly_budget: monthlyBudget }),
    }),
  updateMonthlyIncome: (monthlyIncome: number, month?: string) =>
    request<SettingsResponse>("/api/settings/income", {
      method: "PUT",
      body: JSON.stringify({ monthly_income: monthlyIncome, ...(month ? { month } : {}) }),
    }),
  listRecurringItems: () => request<RecurringItem[]>("/api/recurring-items"),
  getRecurringCalendar: (days = 35) =>
    request<RecurringCalendarResponse>(`/api/recurring-items/calendar?days=${days}`),
  createRecurringItem: (payload: RecurringItemPayload) =>
    request<RecurringItem>("/api/recurring-items", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateRecurringItem: (itemId: number, payload: RecurringItemPayload) =>
    request<RecurringItem>(`/api/recurring-items/${itemId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteRecurringItem: (itemId: number) =>
    request<{ message: string }>(`/api/recurring-items/${itemId}`, {
      method: "DELETE",
    }),
  markRecurringOccurrencePaid: (itemId: number, occurrenceDate: string, transactionId: number) =>
    request<{ message: string }>(`/api/recurring-items/${itemId}/occurrences/pay`, {
      method: "POST",
      body: JSON.stringify({ occurrence_date: occurrenceDate, transaction_id: transactionId }),
    }),
  markRecurringOccurrenceUnpaid: (itemId: number, occurrenceDate: string) =>
    request<{ message: string }>(`/api/recurring-items/${itemId}/occurrences/unpay`, {
      method: "POST",
      body: JSON.stringify({ occurrence_date: occurrenceDate }),
    }),
  startFinanceBriefingAgent: (task: string) =>
    request<AgentBriefingJob>("/api/agents/finance-briefing", {
      method: "POST",
      body: JSON.stringify({ task }),
    }),
  getFinanceBriefingJob: (jobId: string) =>
    request<AgentBriefingJob>(`/api/agents/finance-briefing/${jobId}`),
  listAgentWorkflows: () => request<AgentWorkflowDefinition[]>("/api/agents/workflows"),
  listAgentRuns: (limit = 8) => request<AgentWorkflowRun[]>(`/api/agents/runs?limit=${limit}`),
  startAgentWorkflow: (workflowName: string, task?: string) =>
    request<AgentWorkflowJob>(`/api/agents/workflows/${workflowName}/run`, {
      method: "POST",
      body: JSON.stringify(task ? { task } : {}),
    }),
  getAgentWorkflowJob: (jobId: string) =>
    request<AgentWorkflowJob>(`/api/agents/workflow-jobs/${jobId}`),
  runAutomationBootstrap: () => request<AgentWorkflowRun[]>("/api/agents/bootstrap", { method: "POST" }),
  runAutomationRefresh: (eventType: string) =>
    request<AgentWorkflowJob[]>("/api/agents/automation/refresh", {
      method: "POST",
      body: JSON.stringify({ event_type: eventType }),
    }),
  sendUpcomingBillsEmailNow: () =>
    request<AgentWorkflowRun>("/api/agents/automation/upcoming-bills-email", {
      method: "POST",
    }),
  sendMonthEndEmailNow: () =>
    request<AgentWorkflowRun>("/api/agents/automation/month-end-email", {
      method: "POST",
    }),
};





