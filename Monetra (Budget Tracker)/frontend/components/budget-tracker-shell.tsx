"use client";

import { ReactNode } from "react";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { AutomationCenter } from "@/components/automation-center";
import { DashboardSummaryCards } from "@/components/dashboard-summary";
import { ExpenseForm } from "@/components/expense-form";
import { ExpenseTable } from "@/components/expense-table";
import { FinancialPulse } from "@/components/financial-pulse";
import { InsightsPanel } from "@/components/insights-panel";
import { KpiVisuals } from "@/components/kpi-visuals";
import { LatencyMonitor } from "@/components/latency-monitor";
import { RagQaPanel } from "@/components/rag-qa-panel";
import { OperationsPanel } from "@/components/operations-panel";
import { PiggyBankPanel } from "@/components/piggy-bank-panel";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";
import { SpendingComparisonPanel } from "@/components/spending-comparison-panel";
import { useBudgetTracker } from "@/hooks/use-budget-tracker";
import { formatCurrency } from "@/lib/format";

interface BudgetTrackerShellProps {
  username?: string;
  onLogout?: () => Promise<void> | void;
  onDeleteAccount?: () => Promise<void> | void;
  demoEmailInbox?: ReactNode;
}

export function BudgetTrackerShell({ username = "Rushabh", onLogout, onDeleteAccount, demoEmailInbox }: BudgetTrackerShellProps) {
  const tracker = useBudgetTracker();
  const summary = tracker.dashboard;

  return (
    <main className="page-shell">
      <header className="hero hero-with-actions">
        <div className="hero-grid">
          <div className="hero-copy-column">
            <p className="eyebrow">Budget Tracker</p>
            <h1>Live budget command centre for spending, cash flow, and finance automation.</h1>
            <p className="hero-copy">
              Monitor spending in pounds sterling, manage recurring commitments, update monthly income by month,
              and run AI-assisted workflows from one focused dashboard.
            </p>
            <div className="hero-pill-row">
              <span className="hero-pill">GBP-native finance tracking</span>
              <span className="hero-pill">Ollama agent</span>
              <span className="hero-pill">MCP tool execution</span>
            </div>
          </div>

          <aside className="hero-aside">
            <div className="hero-agent-card">
              <span className="hero-agent-label">System mode</span>
              <strong>Agentic AI</strong>
              <p>
                Multi-step finance reasoning with planning, tool use, verification, and automation workflows.
              </p>
            </div>

            <div className="hero-stat-grid">
              <div className="hero-stat-card">
                <span>Monthly budget</span>
                <strong>{summary ? formatCurrency(summary.monthly_budget) : "--"}</strong>
              </div>
              <div className="hero-stat-card">
                <span>Monthly income</span>
                <strong>{summary ? formatCurrency(summary.monthly_income) : "--"}</strong>
              </div>
              <div className="hero-stat-card">
                <span>Cash flow</span>
                <strong>{summary ? formatCurrency(summary.net_cash_flow) : "--"}</strong>
              </div>
              <div className="hero-stat-card">
                <span>Budget status</span>
                <strong>{summary ? summary.status : "loading"}</strong>
              </div>
            </div>
          </aside>
        </div>

        <div className="hero-actions">
          <div className="session-chip">Signed in as {username}</div>
          {onLogout ? (
            <button className="secondary-button" type="button" onClick={() => void onLogout()}>
              Sign out
            </button>
          ) : null}
          {onDeleteAccount ? (
            <button className="secondary-button danger-account-button" type="button" onClick={() => void onDeleteAccount()}>
              Delete account
            </button>
          ) : null}
        </div>
      </header>

      {tracker.errorMessage ? <div className="message error">{tracker.errorMessage}</div> : null}
      {tracker.statusMessage ? <div className="message success">{tracker.statusMessage}</div> : null}
      {demoEmailInbox}
      {tracker.isOperationLocked ? (
        <div className="message info">
          <strong>Action lock active.</strong>
          {" "}
          <span>
            {tracker.activeOperationLabel ?? "A finance operation"} is running. Conflicting buttons are disabled until the current job completes.
          </span>
        </div>
      ) : null}

      {tracker.isLoading ? <div className="panel">Loading budget data...</div> : null}

      <fieldset
        className="dashboard-layout dashboard-layout-fieldset"
        disabled={tracker.isOperationLocked}
        aria-busy={tracker.isOperationLocked}
      >
        <div className="left-rail">
          <AutomationCenter
            workflows={tracker.agentWorkflows}
            runs={tracker.agentRuns}
            recurringCalendar={tracker.recurringCalendar}
            activeWorkflowName={tracker.activeWorkflowName}
            liveStatusMessage={tracker.activeWorkflowName ? tracker.statusMessage : null}
            onRunWorkflow={tracker.runAutomationWorkflow}
          />
          <DashboardSummaryCards summary={tracker.dashboard} />
          <LatencyMonitor report={tracker.latencyReport} onRefresh={tracker.refreshLatencyReport} />
          <FinancialPulse pulse={tracker.financialPulse} />
          <RecurringCalendarPanel
            items={tracker.recurringItems}
            calendar={tracker.recurringCalendar}
            onCreate={tracker.createRecurringItem}
            onUpdate={tracker.updateRecurringItem}
            onDelete={tracker.deleteRecurringItem}
            onMarkPaid={tracker.markRecurringOccurrencePaid}
            onMarkUnpaid={tracker.markRecurringOccurrenceUnpaid}
          />
          <PiggyBankPanel
            summary={tracker.dashboard}
            expenses={tracker.allExpenses}
            monthlyIncomeRecords={tracker.monthlyIncomeRecords}
          />
          <KpiVisuals expenses={tracker.allExpenses} summary={tracker.dashboard} />
        </div>

        <div className="right-rail">
          <RagQaPanel
            questionDraft={tracker.ragQuestionDraft}
            answer={tracker.ragAnswer}
            status={tracker.ragStatus}
            isQuerying={tracker.isRagQueryRunning}
            isReindexing={tracker.isRagReindexing}
            onQuestionDraftChange={tracker.setRagQuestionDraft}
            onAsk={tracker.runRagQuery}
            onReindex={tracker.reindexRagKnowledge}
          />
          <AiAgentPanel
            taskDraft={tracker.agentTaskDraft}
            result={tracker.agentBriefing}
            errorMessage={tracker.agentError}
            isRunning={tracker.isAgentRunning}
            onTaskDraftChange={tracker.setAgentTaskDraft}
            onRun={tracker.runFinanceBriefingAgent}
          />
          <ExpenseForm
            form={tracker.form}
            selectedExpenseId={tracker.selectedExpense?.id ?? null}
            onChange={tracker.setForm}
            onCreate={tracker.createExpense}
            onUpdate={tracker.updateExpense}
            onDelete={tracker.deleteExpense}
            onClear={tracker.resetForm}
          />
          <OperationsPanel
            summary={tracker.dashboard}
            prediction={tracker.prediction}
            exportUrl={tracker.exportUrl}
            reportUrl={tracker.reportUrl}
            budgetDraft={tracker.budgetDraft}
            incomeDraft={tracker.incomeDraft}
            incomeMonthDraft={tracker.incomeMonthDraft}
            onImport={tracker.importExpenses}
            onPredict={tracker.predictNextMonth}
            onCheckBudget={tracker.checkBudgetStatus}
            onBudgetDraftChange={tracker.setBudgetDraft}
            onIncomeDraftChange={tracker.setIncomeDraft}
            onIncomeMonthChange={tracker.setIncomeMonthDraft}
            onSaveBudget={tracker.saveMonthlyBudget}
            onSaveIncome={tracker.saveMonthlyIncome}
          />
          <SpendingComparisonPanel expenses={tracker.allExpenses} />
          <InsightsPanel
            categories={tracker.categoryInsights}
            wordCloud={tracker.wordCloud}
          />
          <ExpenseTable
            expenses={tracker.expenses}
            selectedExpenseId={tracker.selectedExpense?.id ?? null}
            searchId={tracker.searchId}
            onSearchIdChange={tracker.setSearchId}
            onSearch={tracker.searchExpenseById}
            onShowAll={tracker.showAllRecords}
            onSelect={tracker.selectExpense}
          />
        </div>
      </fieldset>
    </main>
  );
}

