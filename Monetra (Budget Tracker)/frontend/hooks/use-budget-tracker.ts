"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import {
  AgentBriefingResponse,
  AgentWorkflowDefinition,
  AgentWorkflowJob,
  AgentWorkflowRun,
  CategoryInsightsResponse,
  DashboardSummary,
  Expense,
  FinancialPulseResponse,
  FormState,
  LatencyReportResponse,
  MonthlyIncomeRecord,
  PredictionResponse,
  RagAnswerResponse,
  RagStatusResponse,
  RecurringCalendarResponse,
  RecurringItem,
  RecurringItemPayload,
  SavingsGoal,
  SavingsGoalPayload,
  WordCloudResponse,
} from "@/lib/types";

const emptyForm: FormState = {
  date: "",
  category: "",
  description: "",
  amount: "",
  entry_type: "expense",
};
const defaultAgentTask =
  "Prepare a CFO-style monthly finance briefing with cash-flow risk, recurring bill pressure, recommended actions, and an email-ready summary.";
const defaultRagQuestion =
  "What are the biggest spending drivers this month and which recurring commitments are likely to pressure cash flow next?";

function delay(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function currentMonthKey() {
  return new Date().toISOString().slice(0, 7);
}

function expenseDisplayId(expense: Expense) {
  return expense.user_expense_id ?? expense.id;
}

/* istanbul ignore next */
function shouldSkipAutomationBootstrap() {
  return process.env.NODE_ENV !== "test" && process.env.NEXT_PUBLIC_AUTOMATION_BOOTSTRAP_ENABLED !== "true";
}

function shouldRefreshAutomationAfterAgentAction(actionType: string) {
  return !["month_end_email_sent", "upcoming_bills_email_sent", "upcoming_bills_email_skipped"].includes(actionType);
}

type EmailDispatchId = "upcoming_bills_email" | "all_upcoming_bills_email" | "month_end_email";

export function monthFromAgentAction(result: AgentBriefingResponse): string | undefined {
  const month = result.action_result?.payload?.income_month ?? result.action_result?.payload?.budget_month;
  return typeof month === "string" && /^\d{4}-\d{2}$/.test(month) ? month : undefined;
}

export function resolveRequestedIncomeMonth(
  selectedIncomeMonth: string | undefined,
  incomeMonthDraft: string,
  fallbackMonth: string,
) {
  return selectedIncomeMonth?.trim() || incomeMonthDraft || fallbackMonth;
}

export function resolveIncomeMonthDraft(
  settingsData: Partial<Pick<DashboardSummary, "budget_month" | "income_month">>,
  dashboardData: Partial<Pick<DashboardSummary, "budget_month" | "income_month" | "month_key">>,
  requestedIncomeMonth: string,
) {
  return settingsData.budget_month
    ?? settingsData.income_month
    ?? dashboardData.budget_month
    ?? dashboardData.income_month
    ?? dashboardData.month_key
    ?? requestedIncomeMonth;
}

export function resolveActiveOperationLabel(state: {
  activeOperationRefLabel?: string | null;
  activeOperationLabel?: string | null;
  isAutomationRefreshing?: boolean;
  isAgentRunning?: boolean;
  isRagQueryRunning?: boolean;
  isRagReindexing?: boolean;
  isBootstrappingAutomation?: boolean;
  activeWorkflowName?: string | null;
  activeEmailDispatchId?: string | null;
}) {
  return state.activeOperationRefLabel ||
    state.activeOperationLabel ||
    (state.isAutomationRefreshing ? "Background automation refresh" : null) ||
    (state.isAgentRunning ? "AI agent request" : null) ||
    (state.isRagQueryRunning ? "RAG query" : null) ||
    (state.isRagReindexing ? "RAG reindex" : null) ||
    (state.isBootstrappingAutomation ? "Automation bootstrap" : null) ||
    (state.activeWorkflowName ? `${state.activeWorkflowName.replaceAll("_", " ")} workflow` : null) ||
    (state.activeEmailDispatchId ? `${state.activeEmailDispatchId.replaceAll("_", " ")} dispatch` : null);
}

export function resolveBudgetMonth(value: string | null | undefined, fallback: string) {
  return value ?? fallback;
}

export function useBudgetTracker() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [filteredExpenses, setFilteredExpenses] = useState<Expense[] | null>(null);
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [categoryInsights, setCategoryInsights] = useState<CategoryInsightsResponse | null>(null);
  const [wordCloud, setWordCloud] = useState<WordCloudResponse | null>(null);
  const [financialPulse, setFinancialPulse] = useState<FinancialPulseResponse | null>(null);
  const [monthlyIncomeRecords, setMonthlyIncomeRecords] = useState<MonthlyIncomeRecord[]>([]);
  const [recurringItems, setRecurringItems] = useState<RecurringItem[]>([]);
  const [recurringCalendar, setRecurringCalendar] = useState<RecurringCalendarResponse | null>(null);
  const [savingsGoals, setSavingsGoals] = useState<SavingsGoal[]>([]);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [latencyReport, setLatencyReport] = useState<LatencyReportResponse | null>(null);
  const [ragQuestionDraft, setRagQuestionDraft] = useState(defaultRagQuestion);
  const [ragAnswer, setRagAnswer] = useState<RagAnswerResponse | null>(null);
  const [ragStatus, setRagStatus] = useState<RagStatusResponse | null>(null);
  const [isRagQueryRunning, setIsRagQueryRunning] = useState(false);
  const [isRagReindexing, setIsRagReindexing] = useState(false);
  const [agentTaskDraft, setAgentTaskDraft] = useState(defaultAgentTask);
  const [agentBriefing, setAgentBriefing] = useState<AgentBriefingResponse | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [agentWorkflows, setAgentWorkflows] = useState<AgentWorkflowDefinition[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentWorkflowRun[]>([]);
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [isBootstrappingAutomation, setIsBootstrappingAutomation] = useState(false);
  const [activeWorkflowName, setActiveWorkflowName] = useState<string | null>(null);
  const [activeEmailDispatchId, setActiveEmailDispatchId] = useState<string | null>(null);
  const [activeOperationLabel, setActiveOperationLabel] = useState<string | null>(null);
  const [isAutomationRefreshing, setIsAutomationRefreshing] = useState(false);
  const activeOperationRef = useRef<string | null>(null);
  const automationRefreshRef = useRef(false);
  const [searchId, setSearchId] = useState("");
  const [budgetDraft, setBudgetDraft] = useState("");
  const [incomeDraft, setIncomeDraft] = useState("");
  const [incomeMonthDraft, setIncomeMonthDraft] = useState(currentMonthKey());
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const visibleExpenses = useMemo(
    () => filteredExpenses ?? expenses,
    [expenses, filteredExpenses],
  );
  const isOperationLocked = Boolean(
    activeOperationLabel ||
      isLoading ||
      isAutomationRefreshing ||
      isAgentRunning ||
      isRagQueryRunning ||
      isRagReindexing ||
      isBootstrappingAutomation ||
      activeWorkflowName ||
      activeEmailDispatchId,
  );

  function beginExclusiveOperation(label: string) {
    const activeLabel = resolveActiveOperationLabel({
      activeOperationRefLabel: activeOperationRef.current,
      activeOperationLabel,
      isAutomationRefreshing,
      isAgentRunning,
      isRagQueryRunning,
      isRagReindexing,
      isBootstrappingAutomation,
      activeWorkflowName,
      activeEmailDispatchId,
    });

    if (activeLabel) {
      setStatusMessage(`${activeLabel} is still running. Wait for it to finish before starting another action.`);
      return false;
    }

    activeOperationRef.current = label;
    setActiveOperationLabel(label);
    return true;
  }

  function endExclusiveOperation(label: string) {
    if (activeOperationRef.current === label) {
      activeOperationRef.current = null;
      setActiveOperationLabel(null);
    }
  }

  async function loadAllData(selectedIncomeMonth?: string) {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const requestedIncomeMonth = resolveRequestedIncomeMonth(selectedIncomeMonth, incomeMonthDraft, currentMonthKey());
      if (selectedIncomeMonth?.trim()) {
        setIncomeMonthDraft(requestedIncomeMonth);
      }
      const [
        expenseData,
        dashboardData,
        settingsData,
        incomeRecordData,
        categoryData,
        wordCloudData,
        financialPulseData,
        recurringItemsData,
        recurringCalendarData,
        savingsGoalsData,
        workflowData,
        agentRunData,
        ragStatusData,
        latencyData,
      ] = await Promise.all([
        apiClient.listExpenses(),
        apiClient.getDashboard(),
        apiClient.getSettings(requestedIncomeMonth),
        apiClient.listMonthlyIncomeRecords(),
        apiClient.getCategoryInsights(),
        apiClient.getWordCloud(),
        apiClient.getFinancialPulse(),
        apiClient.listRecurringItems(),
        apiClient.getRecurringCalendar(),
        apiClient.listSavingsGoals(),
        apiClient.listAgentWorkflows(),
        apiClient.listAgentRuns(),
        apiClient.getRagStatus(),
        apiClient.getLatencyReport(),
      ]);

      setExpenses(expenseData);
      setFilteredExpenses(null);
      setDashboard(dashboardData);
      setBudgetDraft(settingsData.monthly_budget.toFixed(2));
      setIncomeDraft(settingsData.monthly_income.toFixed(2));
      setIncomeMonthDraft(resolveIncomeMonthDraft(settingsData, dashboardData, requestedIncomeMonth));
      setMonthlyIncomeRecords(incomeRecordData);
      setCategoryInsights(categoryData);
      setWordCloud(wordCloudData);
      setFinancialPulse(financialPulseData);
      setRecurringItems(recurringItemsData);
      setRecurringCalendar(recurringCalendarData);
      setSavingsGoals(savingsGoalsData);
      setAgentWorkflows(workflowData);
      setAgentRuns(agentRunData);
      setRagStatus(ragStatusData);
      setLatencyReport(latencyData);
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setIsLoading(false);
    }
  }
  useEffect(() => {
    void loadAllData();
  }, []);

  async function refreshLatencyReport() {
    try {
      const report = await apiClient.getLatencyReport();
      setLatencyReport(report);
    } catch (error) {
      console.error("[Monetra Latency] Unable to refresh latency report.", error);
    }
  }

  async function recordClientOperationFailure(operation: string, error: unknown, startedAt: number) {
    try {
      await apiClient.recordClientFailure({
        operation,
        error: error instanceof Error ? error.message : String(error),
        duration_ms: Math.max(0, Math.round(performance.now() - startedAt)),
      });
      await refreshLatencyReport();
    } catch (telemetryError) {
      console.error("[Monetra Latency] Unable to record client operation failure.", telemetryError);
    }
  }

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refreshLatencyReport();
    }, 8000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    /* istanbul ignore if -- production disables automatic workflow startup unless explicitly enabled */
    if (shouldSkipAutomationBootstrap()) {
      return;
    }
    if (isLoading || !agentWorkflows.length || isBootstrappingAutomation) {
      return;
    }
    const automationKey = `monetra-automation-bootstrap:${new Date().toISOString().slice(0, 10)}`;
    if (typeof window === "undefined" || window.sessionStorage.getItem(automationKey)) {
      return;
    }

    void (async () => {
      try {
        setIsBootstrappingAutomation(true);
        const results = await apiClient.runAutomationBootstrap();
        if (results.length) {
          setAgentRuns(results);
          setStatusMessage("Automation workflows were triggered automatically for this session.");
        }
        window.sessionStorage.setItem(automationKey, "done");
      } catch (error) {
        setErrorMessage((error as Error).message);
      } finally {
        setIsBootstrappingAutomation(false);
      }
    })();
  }, [agentWorkflows, isLoading, isBootstrappingAutomation]);

  function resetForm() {
    setSelectedExpense(null);
    setForm(emptyForm);
  }

  function selectExpense(expense: Expense) {
    setSelectedExpense(expense);
      setForm({
        date: expense.date,
        category: expense.category,
        description: expense.description,
        amount: expense.amount.toString(),
        entry_type: expense.entry_type,
      });
  }

  async function createExpense() {
    const operationLabel = "Create transaction";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      const created = await apiClient.createExpense({
        ...form,
        amount: form.amount,
      });
      setStatusMessage(`Expense #${expenseDisplayId(created)} added successfully.`);
      resetForm();
      await loadAllData();
      void refreshAutomationCenter("expense_created");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function updateExpense() {
    const operationLabel = "Update transaction";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    if (!selectedExpense) {
      setErrorMessage("Select an expense before updating.");
      endExclusiveOperation(operationLabel);
      return;
    }

    try {
      setErrorMessage(null);
      await apiClient.updateExpense(selectedExpense.id, {
        ...form,
        amount: form.amount,
      });
      setStatusMessage(`Expense #${expenseDisplayId(selectedExpense)} updated successfully.`);
      resetForm();
      await loadAllData();
      void refreshAutomationCenter("expense_updated");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function deleteExpense() {
    const operationLabel = "Delete transaction";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    if (!selectedExpense) {
      setErrorMessage("Select an expense before deleting.");
      endExclusiveOperation(operationLabel);
      return;
    }

    try {
      setErrorMessage(null);
      await apiClient.deleteExpense(selectedExpense.id);
      setStatusMessage(`Expense #${expenseDisplayId(selectedExpense)} deleted successfully.`);
      resetForm();
      await loadAllData();
      void refreshAutomationCenter("expense_deleted");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function searchExpenseById() {
    if (!searchId.trim()) {
      setFilteredExpenses(null);
      return;
    }

    try {
      setErrorMessage(null);
      const normalizedId = Number(searchId);
      const expense = expenses.find((item) => expenseDisplayId(item) === normalizedId);
      if (!expense) {
        throw new Error(`Expense #${normalizedId} was not found for your account.`);
      }
      setFilteredExpenses([expense]);
      setStatusMessage(`Showing search result for expense #${expenseDisplayId(expense)}.`);
    } catch (error) {
      setFilteredExpenses([]);
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  function showAllRecords() {
    setFilteredExpenses(null);
    setSearchId("");
    setStatusMessage("Showing all records.");
  }

  async function refreshAutomationCenter(eventType: string) {
    if (automationRefreshRef.current) {
      return;
    }
    try {
      if (typeof apiClient.runAutomationRefresh !== "function") {
        return;
      }
      automationRefreshRef.current = true;
      setIsAutomationRefreshing(true);
      const jobs = await apiClient.runAutomationRefresh(eventType);
      if (!jobs.length) {
        return;
      }
      setStatusMessage("Dashboard data is already refreshed. Background workflows are syncing reports, AI context, and automation history with the latest saved data...");
      const startedAt = Date.now();
      await Promise.all(
        jobs.map((job) => waitForWorkflowRun(job.id, job.workflow_name, startedAt))
      );
      const refreshedRuns = await apiClient.listAgentRuns();
      setAgentRuns(refreshedRuns);
      setStatusMessage("Background automation refresh completed. Dashboard labels, reports, AI context, and automation history are up to date.");
    } catch (error) {
      console.error("[Monetra Automation] Automatic workflow refresh failed.", error);
    } finally {
      automationRefreshRef.current = false;
      setIsAutomationRefreshing(false);
    }
  }
  async function importExpenses(file: File) {
    const operationLabel = "Import transactions";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      const result = await apiClient.importExpenses(file);
      setStatusMessage(
        `Imported ${result.imported_rows} rows and skipped ${result.skipped_rows}.`,
      );
      await loadAllData();
      void refreshAutomationCenter("expenses_imported");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function predictNextMonth() {
    try {
      setErrorMessage(null);
      const result = await apiClient.getPrediction();
      setPrediction(result);
      setStatusMessage(`Prediction refreshed for ${result.next_month}.`);
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  function checkBudgetStatus() {
    if (!dashboard) {
      return;
    }

    const statusText =
      dashboard.status === "over"
        ? "You are over budget."
        : dashboard.status === "warning"
          ? "You are close to your budget limit."
          : "You are within budget.";

    setStatusMessage(
      `${dashboard.month_label}: spent GBP ${dashboard.current_month_total.toFixed(2)}. ${statusText}`,
    );
  }

  async function saveMonthlyBudget() {
    const operationLabel = "Save monthly budget";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      const result = await apiClient.updateMonthlyBudget(Number(budgetDraft), incomeMonthDraft);
      setBudgetDraft(result.monthly_budget.toFixed(2));
      const budgetMonth = resolveBudgetMonth(result.budget_month, incomeMonthDraft);
      setIncomeMonthDraft(budgetMonth);
      setStatusMessage(`Monthly budget updated to GBP ${result.monthly_budget.toFixed(2)} for ${budgetMonth}.`);
      await loadAllData(budgetMonth);
      void refreshAutomationCenter("monthly_budget_updated");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function saveMonthlyIncome() {
    const operationLabel = "Save monthly income";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      const result = await apiClient.updateMonthlyIncome(Number(incomeDraft), incomeMonthDraft);
      setIncomeDraft(result.monthly_income.toFixed(2));
      setIncomeMonthDraft(result.income_month ?? incomeMonthDraft);
      setStatusMessage(`Monthly income updated to GBP ${result.monthly_income.toFixed(2)} for ${result.income_month ?? incomeMonthDraft}.`);
      await loadAllData(result.income_month ?? incomeMonthDraft);
      void refreshAutomationCenter("monthly_income_updated");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function createRecurringItem(payload: RecurringItemPayload) {
    const operationLabel = "Create recurring reminder";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      const created = await apiClient.createRecurringItem(payload);
      setStatusMessage(`Recurring item #${created.id} created successfully.`);
      await loadAllData();
      void refreshAutomationCenter("recurring_item_created");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function updateRecurringItem(itemId: number, payload: RecurringItemPayload) {
    const operationLabel = "Update recurring reminder";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      await apiClient.updateRecurringItem(itemId, payload);
      setStatusMessage(`Recurring item #${itemId} updated successfully.`);
      await loadAllData();
      void refreshAutomationCenter("recurring_item_updated");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function deleteRecurringItem(itemId: number) {
    const operationLabel = "Delete recurring reminder";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      await apiClient.deleteRecurringItem(itemId);
      setStatusMessage(`Recurring item #${itemId} deleted successfully.`);
      await loadAllData();
      void refreshAutomationCenter("recurring_item_deleted");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function markRecurringOccurrencePaid(itemId: number, occurrenceDate: string, transactionId: number) {
    const operationLabel = "Mark recurring payment paid";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      const result = await apiClient.markRecurringOccurrencePaid(itemId, occurrenceDate, transactionId);
      setStatusMessage(result.message);
      await loadAllData();
      void refreshAutomationCenter("recurring_occurrence_paid");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function markRecurringOccurrenceUnpaid(itemId: number, occurrenceDate: string) {
    const operationLabel = "Mark recurring payment unpaid";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      const result = await apiClient.markRecurringOccurrenceUnpaid(itemId, occurrenceDate);
      setStatusMessage(result.message);
      await loadAllData();
      void refreshAutomationCenter("recurring_occurrence_unpaid");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function runRagQuery() {
    const operationLabel = "RAG query";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    const normalizedQuestion = ragQuestionDraft.trim();
    if (!normalizedQuestion) {
      setErrorMessage("Enter a finance question before querying the knowledge base.");
      endExclusiveOperation(operationLabel);
      return;
    }

    try {
      setErrorMessage(null);
      setIsRagQueryRunning(true);
      setStatusMessage("Querying the finance knowledge base...");
      const result = await apiClient.queryRag(normalizedQuestion);
      setRagAnswer(result);
      const latestStatus = await apiClient.getRagStatus();
      setRagStatus(latestStatus);
      setStatusMessage(`RAG answer generated from ${result.sources.length} knowledge chunk${result.sources.length === 1 ? "" : "s"}.`);
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      setIsRagQueryRunning(false);
      endExclusiveOperation(operationLabel);
    }
  }

  async function createSavingsGoal(payload: SavingsGoalPayload) {
    const operationLabel = "Create savings goal";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      const created = await apiClient.createSavingsGoal(payload);
      setStatusMessage(`Savings goal #${created.id} created successfully.`);
      await loadAllData();
      void refreshAutomationCenter("savings_goal_created");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function updateSavingsGoal(goalId: number, payload: SavingsGoalPayload) {
    const operationLabel = "Update savings goal";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      await apiClient.updateSavingsGoal(goalId, payload);
      setStatusMessage(`Savings goal #${goalId} updated successfully.`);
      await loadAllData();
      void refreshAutomationCenter("savings_goal_updated");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function deleteSavingsGoal(goalId: number) {
    const operationLabel = "Delete savings goal";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      await apiClient.deleteSavingsGoal(goalId);
      setStatusMessage(`Savings goal #${goalId} deleted successfully.`);
      await loadAllData();
      void refreshAutomationCenter("savings_goal_deleted");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      endExclusiveOperation(operationLabel);
    }
  }

  async function reindexRagKnowledge(force = true) {
    const operationLabel = "RAG reindex";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    try {
      setErrorMessage(null);
      setIsRagReindexing(true);
      setStatusMessage("Reindexing the finance knowledge base...");
      const status = await apiClient.reindexRag(force);
      setRagStatus(status);
      setStatusMessage(
        status.reindexed
          ? `Knowledge base rebuilt with ${status.chunk_count} chunks across ${status.document_count} documents.`
          : "Knowledge base is already up to date.",
      );
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      setIsRagReindexing(false);
      endExclusiveOperation(operationLabel);
    }
  }
  async function runFinanceBriefingAgent() {
    const operationLabel = "AI agent request";
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    const startedAt = performance.now();
    try {
      setErrorMessage(null);
      setAgentError(null);
      setIsAgentRunning(true);
      setStatusMessage("AI agent request queued. Preparing Ollama job...");
      const job = await apiClient.startFinanceBriefingAgent(agentTaskDraft);
      const result = await waitForFinanceBriefing(job.id);
      setAgentBriefing(result);
      const actionType =
        result.action_result && typeof result.action_result.type === "string"
          ? result.action_result.type
          : null;
      if (actionType) {
        await loadAllData(monthFromAgentAction(result));
        if (shouldRefreshAutomationAfterAgentAction(actionType)) {
          void refreshAutomationCenter(actionType);
        } else {
          const refreshedRuns = await apiClient.listAgentRuns();
          setAgentRuns(refreshedRuns);
        }
      }
      setStatusMessage(`AI briefing generated with ${result.tools_used.length} tool calls.`);
    } catch (error) {
      const message = (error as Error).message;
      await recordClientOperationFailure(operationLabel, error, startedAt);
      setStatusMessage(null);
      setAgentError(message);
      setErrorMessage(message);
    } finally {
      setIsAgentRunning(false);
      endExclusiveOperation(operationLabel);
    }
  }

  async function waitForFinanceBriefing(jobId: string) {
    for (;;) {
      const job = await apiClient.getFinanceBriefingJob(jobId);
      if (job.status === "completed" && job.result) {
        return job.result;
      }
      if (job.status === "failed") {
        throw new Error(job.error ?? "The AI agent failed to complete the request.");
      }

      setStatusMessage(
        job.status === "running"
          ? "AI agent is processing your command in pounds sterling..."
          : "AI agent request queued. Waiting for the worker to start.",
      );
      await delay(2000);
    }
  }

  async function runAutomationWorkflow(workflowName: string) {
    const operationLabel = `${workflowName.replaceAll("_", " ")} workflow`;
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    const startedAt = performance.now();
    try {
      setErrorMessage(null);
      setActiveWorkflowName(workflowName);
      setStatusMessage("Workflow request queued. Preparing the agent worker...");
      const job = await apiClient.startAgentWorkflow(workflowName);
      const result = await waitForWorkflowRun(job.id, workflowName, Date.now());
      await loadAllData();
      const refreshedRuns = await apiClient.listAgentRuns();
      setAgentRuns([result, ...refreshedRuns].slice(0, 8));
      setStatusMessage(`${result.workflow_label} completed: ${result.headline} ${result.tools_used.length} automated steps used.`);
    } catch (error) {
      await recordClientOperationFailure(operationLabel, error, startedAt);
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      setActiveWorkflowName(null);
      endExclusiveOperation(operationLabel);
    }
  }

  async function waitForWorkflowRun(
    jobId: string,
    workflowName: string,
    startedAt: number,
  ) {
    for (;;) {
      const job: AgentWorkflowJob = await apiClient.getAgentWorkflowJob(jobId);
      const elapsedSeconds = Math.max(0, Math.round((Date.now() - startedAt) / 1000));
      if (job.status === "completed" && job.result) {
        return job.result;
      }
      if (job.status === "failed") {
        const workflowError =
          job.error === null || job.error === undefined
            ? `The ${workflowName} workflow failed.`
            : job.error;
        throw new Error(workflowError);
      }

      setStatusMessage(
        job.status === "running"
          ? `${workflowName.replaceAll("_", " ")} is running through the agent pipeline. Elapsed: ${elapsedSeconds}s. Saved dashboard labels are safe to read or refresh now; reports, emails, AI summaries, and automation history update when this workflow completes.`
          : `Waiting for ${workflowName.replaceAll("_", " ")} to start. Status: ${job.status}. Elapsed: ${elapsedSeconds}s. Saved dashboard labels remain safe to read; derived workflow outputs update after completion.`,
      );
      await delay(2000);
    }
  }

  async function runManualEmailDispatch(dispatchId: EmailDispatchId) {
    const operationLabel = `${dispatchId.replaceAll("_", " ")} dispatch`;
    if (!beginExclusiveOperation(operationLabel)) {
      return;
    }
    const startedAt = performance.now();
    try {
      setErrorMessage(null);
      setActiveEmailDispatchId(dispatchId);
      setStatusMessage(
        dispatchId === "upcoming_bills_email"
          ? "Preparing late reminders plus bills due today and the next 7 days. This covers 8 calendar dates total..."
          : dispatchId === "all_upcoming_bills_email"
            ? "Preparing all projected upcoming bills..."
            : "Preparing the month-end report email...",
      );
      const result =
        dispatchId === "upcoming_bills_email"
          ? await apiClient.sendUpcomingBillsEmailNow()
          : dispatchId === "all_upcoming_bills_email"
            ? await apiClient.sendAllUpcomingBillsEmailNow()
            : await apiClient.sendMonthEndEmailNow();
      setAgentRuns((current) => [result, ...current.filter((item) => item.id !== result.id)].slice(0, 8));
      setStatusMessage(result.summary);
    } catch (error) {
      await recordClientOperationFailure(operationLabel, error, startedAt);
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      setActiveEmailDispatchId(null);
      endExclusiveOperation(operationLabel);
    }
  }

  async function sendUpcomingBillsEmailNow() {
    await runManualEmailDispatch("upcoming_bills_email");
  }

  async function sendAllUpcomingBillsEmailNow() {
    await runManualEmailDispatch("all_upcoming_bills_email");
  }

  async function sendMonthEndEmailNow() {
    await runManualEmailDispatch("month_end_email");
  }

  return {
    allExpenses: expenses,
    expenses: visibleExpenses,
    selectedExpense,
    form,
    dashboard,
    categoryInsights,
    wordCloud,
    financialPulse,
    monthlyIncomeRecords,
    recurringItems,
    recurringCalendar,
    savingsGoals,
    prediction,
    latencyReport,
    ragQuestionDraft,
    ragAnswer,
    ragStatus,
    agentTaskDraft,
    agentBriefing,
    agentError,
    agentWorkflows,
    agentRuns,
    isAgentRunning,
    isRagQueryRunning,
    isRagReindexing,
    isBootstrappingAutomation,
    isAutomationRefreshing,
    activeOperationLabel,
    isOperationLocked,
    activeWorkflowName,
    activeEmailDispatchId,
    searchId,
    budgetDraft,
    incomeDraft,
    incomeMonthDraft,
    statusMessage,
    errorMessage,
    isLoading,
    exportUrl: apiClient.exportExpenses(),
    reportUrl: apiClient.downloadMonthlyReport(incomeMonthDraft),
    setForm,
    setSearchId,
    setBudgetDraft,
    setIncomeDraft,
    setIncomeMonthDraft,
    setRagQuestionDraft,
    setAgentTaskDraft,
    selectExpense,
    resetForm,
    createExpense,
    updateExpense,
    deleteExpense,
    searchExpenseById,
    showAllRecords,
    importExpenses,
    predictNextMonth,
    checkBudgetStatus,
    saveMonthlyBudget,
    saveMonthlyIncome,
    createRecurringItem,
    updateRecurringItem,
    deleteRecurringItem,
    createSavingsGoal,
    updateSavingsGoal,
    deleteSavingsGoal,
    markRecurringOccurrencePaid,
    markRecurringOccurrenceUnpaid,
    runRagQuery,
    reindexRagKnowledge,
    runFinanceBriefingAgent,
    runAutomationWorkflow,
    sendUpcomingBillsEmailNow,
    sendAllUpcomingBillsEmailNow,
    sendMonthEndEmailNow,
    refreshLatencyReport,
    refresh: loadAllData,
  };
}
