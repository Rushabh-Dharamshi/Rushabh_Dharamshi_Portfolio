"use client";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { AutomationCenter } from "@/components/automation-center";
import { DashboardSummaryCards } from "@/components/dashboard-summary";
import { ExpenseForm } from "@/components/expense-form";
import { ExpenseTable } from "@/components/expense-table";
import { FinancialPulse } from "@/components/financial-pulse";
import { InsightsPanel } from "@/components/insights-panel";
import { KpiVisuals } from "@/components/kpi-visuals";
import { OperationsPanel } from "@/components/operations-panel";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";
import { SpendingComparisonPanel } from "@/components/spending-comparison-panel";
import { useBudgetTracker } from "@/hooks/use-budget-tracker";
import { formatCurrency } from "@/lib/format";

interface BudgetTrackerShellProps {
  username?: string;
  onLogout?: () => Promise<void> | void;
}

export function BudgetTrackerShell({ username = "Rushabh", onLogout }: BudgetTrackerShellProps) {
  const tracker = useBudgetTracker();
  const summary = tracker.dashboard;

  return (
    <main className="page-shell">
      <header className="hero hero-with-actions">
        <div className="hero-grid">
          <div className="hero-copy-column">
            <p className="eyebrow">Budget Tracker</p>
            <h1>Dashboard with live KPIs, workflow automation, and agentic finance operations.</h1>
            <p className="hero-copy">
              Monitor spending in pounds sterling, manage recurring commitments, update monthly income by month,
              and run local AI workflows through a polished Next.js interface backed by Flask, PostgreSQL,
              Ollama, LangChain, LangGraph, and MCP tools.
            </p>
            <div className="hero-pill-row">
              <span className="hero-pill">GBP-native finance tracking</span>
              <span className="hero-pill">Local Ollama agent</span>
              <span className="hero-pill">MCP tool execution</span>
            </div>
          </div>

          <aside className="hero-aside">
            <div className="hero-agent-card">
              <span className="hero-agent-label">System mode</span>
              <strong>Local agentic AI</strong>
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
        </div>
      </header>

      {tracker.errorMessage ? <div className="message error">{tracker.errorMessage}</div> : null}
      {tracker.statusMessage ? <div className="message success">{tracker.statusMessage}</div> : null}

      {tracker.isLoading ? <div className="panel">Loading budget data...</div> : null}

      <div className="dashboard-layout">
        <div className="left-rail">
          <AutomationCenter
            workflows={tracker.agentWorkflows}
            runs={tracker.agentRuns}
            activeWorkflowName={tracker.activeWorkflowName}
            onRunWorkflow={tracker.runAutomationWorkflow}
          />
          <DashboardSummaryCards summary={tracker.dashboard} />
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
          <RecurringCalendarPanel
            items={tracker.recurringItems}
            calendar={tracker.recurringCalendar}
            onCreate={tracker.createRecurringItem}
            onUpdate={tracker.updateRecurringItem}
            onDelete={tracker.deleteRecurringItem}
            onMarkPaid={tracker.markRecurringOccurrencePaid}
            onMarkUnpaid={tracker.markRecurringOccurrenceUnpaid}
          />
        </div>

        <div className="right-rail">
          <AiAgentPanel
            taskDraft={tracker.agentTaskDraft}
            result={tracker.agentBriefing}
            isRunning={tracker.isAgentRunning}
            onTaskDraftChange={tracker.setAgentTaskDraft}
            onRun={tracker.runFinanceBriefingAgent}
          />
          <KpiVisuals expenses={tracker.allExpenses} summary={tracker.dashboard} />
          <FinancialPulse pulse={tracker.financialPulse} />
          <ExpenseTable
            expenses={tracker.expenses}
            selectedExpenseId={tracker.selectedExpense?.id ?? null}
            searchId={tracker.searchId}
            onSearchIdChange={tracker.setSearchId}
            onSearch={tracker.searchExpenseById}
            onShowAll={tracker.showAllRecords}
            onSelect={tracker.selectExpense}
          />
          <SpendingComparisonPanel expenses={tracker.allExpenses} />
          <InsightsPanel
            categories={tracker.categoryInsights}
            wordCloud={tracker.wordCloud}
          />
        </div>
      </div>
    </main>
  );
}

