"use client";

import { useEffect, useMemo, useState } from "react";

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
  PredictionResponse,
  RecurringCalendarResponse,
  RecurringItem,
  RecurringItemPayload,
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

function delay(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function currentMonthKey() {
  return new Date().toISOString().slice(0, 7);
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
  const [recurringItems, setRecurringItems] = useState<RecurringItem[]>([]);
  const [recurringCalendar, setRecurringCalendar] = useState<RecurringCalendarResponse | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [agentTaskDraft, setAgentTaskDraft] = useState(defaultAgentTask);
  const [agentBriefing, setAgentBriefing] = useState<AgentBriefingResponse | null>(null);
  const [agentWorkflows, setAgentWorkflows] = useState<AgentWorkflowDefinition[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentWorkflowRun[]>([]);
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [isBootstrappingAutomation, setIsBootstrappingAutomation] = useState(false);
  const [activeWorkflowName, setActiveWorkflowName] = useState<string | null>(null);
  const [activeEmailDispatchId, setActiveEmailDispatchId] = useState<string | null>(null);
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

  async function loadAllData(selectedIncomeMonth?: string) {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const requestedIncomeMonth = selectedIncomeMonth ?? incomeMonthDraft ?? currentMonthKey();
      const [
        expenseData,
        dashboardData,
        settingsData,
        categoryData,
        wordCloudData,
        financialPulseData,
        recurringItemsData,
        recurringCalendarData,
        workflowData,
        agentRunData,
      ] = await Promise.all([
        apiClient.listExpenses(),
        apiClient.getDashboard(),
        apiClient.getSettings(requestedIncomeMonth),
        apiClient.getCategoryInsights(),
        apiClient.getWordCloud(),
        apiClient.getFinancialPulse(),
        apiClient.listRecurringItems(),
        apiClient.getRecurringCalendar(),
        apiClient.listAgentWorkflows(),
        apiClient.listAgentRuns(),
      ]);

      setExpenses(expenseData);
      setFilteredExpenses(null);
      setDashboard(dashboardData);
      setBudgetDraft(dashboardData.monthly_budget.toFixed(2));
      setIncomeDraft(settingsData.monthly_income.toFixed(2));
      setIncomeMonthDraft(settingsData.income_month ?? dashboardData.income_month ?? dashboardData.month_key ?? requestedIncomeMonth);
      setCategoryInsights(categoryData);
      setWordCloud(wordCloudData);
      setFinancialPulse(financialPulseData);
      setRecurringItems(recurringItemsData);
      setRecurringCalendar(recurringCalendarData);
      setAgentWorkflows(workflowData);
      setAgentRuns(agentRunData);
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setIsLoading(false);
    }
  }
  useEffect(() => {
    void loadAllData();
  }, []);

  useEffect(() => {
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
    try {
      setErrorMessage(null);
      const created = await apiClient.createExpense({
        ...form,
        amount: form.amount,
      });
      setStatusMessage(`Expense #${created.id} added successfully.`);
      resetForm();
      await loadAllData();
      void refreshAutomationCenter("expense_created");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function updateExpense() {
    if (!selectedExpense) {
      setErrorMessage("Select an expense before updating.");
      return;
    }

    try {
      setErrorMessage(null);
      await apiClient.updateExpense(selectedExpense.id, {
        ...form,
        amount: form.amount,
      });
      setStatusMessage(`Expense #${selectedExpense.id} updated successfully.`);
      resetForm();
      await loadAllData();
      void refreshAutomationCenter("expense_updated");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function deleteExpense() {
    if (!selectedExpense) {
      setErrorMessage("Select an expense before deleting.");
      return;
    }

    try {
      setErrorMessage(null);
      await apiClient.deleteExpense(selectedExpense.id);
      setStatusMessage(`Expense #${selectedExpense.id} deleted successfully.`);
      resetForm();
      await loadAllData();
      void refreshAutomationCenter("expense_deleted");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function searchExpenseById() {
    if (!searchId.trim()) {
      setFilteredExpenses(null);
      return;
    }

    try {
      setErrorMessage(null);
      const expense = await apiClient.searchExpenseById(Number(searchId));
      setFilteredExpenses([expense]);
      setStatusMessage(`Showing search result for expense #${expense.id}.`);
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
    try {
      if (typeof apiClient.runAutomationRefresh !== "function") {
        return;
      }
      const jobs = await apiClient.runAutomationRefresh(eventType);
      if (!jobs.length) {
        return;
      }
      setStatusMessage("Finance data saved. Refreshing the automation workflows with the latest live data...");
      await Promise.all(
        jobs.map((job) => waitForWorkflowRun(job.id, job.workflow_name, { quiet: true }))
      );
      const refreshedRuns = await apiClient.listAgentRuns();
      setAgentRuns(refreshedRuns);
      setStatusMessage("Automation Center refreshed with the latest finance changes.");
    } catch (error) {
      console.error("[Monetra Automation] Automatic workflow refresh failed.", error);
    }
  }
  async function importExpenses(file: File) {
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
    try {
      setErrorMessage(null);
      const result = await apiClient.updateMonthlyBudget(Number(budgetDraft));
      setBudgetDraft(result.monthly_budget.toFixed(2));
      setStatusMessage(`Monthly budget updated to GBP ${result.monthly_budget.toFixed(2)}.`);
      await loadAllData();
      void refreshAutomationCenter("monthly_budget_updated");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function saveMonthlyIncome() {
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
    }
  }

  async function createRecurringItem(payload: RecurringItemPayload) {
    try {
      setErrorMessage(null);
      const created = await apiClient.createRecurringItem(payload);
      setStatusMessage(`Recurring item #${created.id} created successfully.`);
      await loadAllData();
      void refreshAutomationCenter("recurring_item_created");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function updateRecurringItem(itemId: number, payload: RecurringItemPayload) {
    try {
      setErrorMessage(null);
      await apiClient.updateRecurringItem(itemId, payload);
      setStatusMessage(`Recurring item #${itemId} updated successfully.`);
      await loadAllData();
      void refreshAutomationCenter("recurring_item_updated");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function deleteRecurringItem(itemId: number) {
    try {
      setErrorMessage(null);
      await apiClient.deleteRecurringItem(itemId);
      setStatusMessage(`Recurring item #${itemId} deleted successfully.`);
      await loadAllData();
      void refreshAutomationCenter("recurring_item_deleted");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function markRecurringOccurrencePaid(itemId: number, occurrenceDate: string, transactionId: number) {
    try {
      setErrorMessage(null);
      const result = await apiClient.markRecurringOccurrencePaid(itemId, occurrenceDate, transactionId);
      setStatusMessage(result.message);
      await loadAllData();
      void refreshAutomationCenter("recurring_occurrence_paid");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function markRecurringOccurrenceUnpaid(itemId: number, occurrenceDate: string) {
    try {
      setErrorMessage(null);
      const result = await apiClient.markRecurringOccurrenceUnpaid(itemId, occurrenceDate);
      setStatusMessage(result.message);
      await loadAllData();
      void refreshAutomationCenter("recurring_occurrence_unpaid");
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    }
  }

  async function runFinanceBriefingAgent() {
    try {
      setErrorMessage(null);
      setIsAgentRunning(true);
      setStatusMessage("AI agent request queued. Preparing local Ollama job...");
      const job = await apiClient.startFinanceBriefingAgent(agentTaskDraft);
      const result = await waitForFinanceBriefing(job.id);
      setAgentBriefing(result);
      if (result.action_result?.type) {
        await loadAllData();
        void refreshAutomationCenter(result.action_result.type);
      }
      setStatusMessage(`AI briefing generated with ${result.tools_used.length} tool calls.`);
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      setIsAgentRunning(false);
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
          ? "AI agent is processing your command locally in pounds sterling..."
          : "AI agent request queued. Waiting for the local worker to start...",
      );
      await delay(2000);
    }
  }

  async function runAutomationWorkflow(workflowName: string) {
    try {
      setErrorMessage(null);
      setActiveWorkflowName(workflowName);
      setStatusMessage("Workflow request queued. Preparing the local agent worker...");
      const job = await apiClient.startAgentWorkflow(workflowName);
      const result = await waitForWorkflowRun(job.id, workflowName);
      setAgentRuns((current) => [result, ...current.filter((item) => item.id !== result.id)].slice(0, 8));
      setStatusMessage(`${result.workflow_label} completed with ${result.tools_used.length} automated steps.`);
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      setActiveWorkflowName(null);
    }
  }

  async function waitForWorkflowRun(
    jobId: string,
    workflowName: string,
    options?: { quiet?: boolean },
  ) {
    for (;;) {
      const job: AgentWorkflowJob = await apiClient.getAgentWorkflowJob(jobId);
      if (job.status === "completed" && job.result) {
        return job.result;
      }
      if (job.status === "failed") {
        throw new Error(job.error ?? `The ${workflowName} workflow failed.`);
      }

      if (!options?.quiet) {
        setStatusMessage(
          job.status === "running"
            ? `${workflowName.replaceAll("_", " ")} is running through the local agent pipeline...`
            : `Waiting for ${workflowName.replaceAll("_", " ")} to start...`,
        );
      }
      await delay(2000);
    }
  }

  async function runManualEmailDispatch(dispatchId: "upcoming_bills_email" | "month_end_email") {
    try {
      setErrorMessage(null);
      setActiveEmailDispatchId(dispatchId);
      setStatusMessage(
        dispatchId === "upcoming_bills_email"
          ? "Preparing the latest 7-day bills email..."
          : "Preparing the month-end report email...",
      );
      const result =
        dispatchId === "upcoming_bills_email"
          ? await apiClient.sendUpcomingBillsEmailNow()
          : await apiClient.sendMonthEndEmailNow();
      setAgentRuns((current) => [result, ...current.filter((item) => item.id !== result.id)].slice(0, 8));
      setStatusMessage(result.summary);
    } catch (error) {
      setStatusMessage(null);
      setErrorMessage((error as Error).message);
    } finally {
      setActiveEmailDispatchId(null);
    }
  }

  async function sendUpcomingBillsEmailNow() {
    await runManualEmailDispatch("upcoming_bills_email");
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
    recurringItems,
    recurringCalendar,
    prediction,
    agentTaskDraft,
    agentBriefing,
    agentWorkflows,
    agentRuns,
    isAgentRunning,
    isBootstrappingAutomation,
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
    reportUrl: apiClient.downloadMonthlyReport(),
    setForm,
    setSearchId,
    setBudgetDraft,
    setIncomeDraft,
    setIncomeMonthDraft,
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
    markRecurringOccurrencePaid,
    markRecurringOccurrenceUnpaid,
    runFinanceBriefingAgent,
    runAutomationWorkflow,
    sendUpcomingBillsEmailNow,
    sendMonthEndEmailNow,
    refresh: loadAllData,
  };
}










