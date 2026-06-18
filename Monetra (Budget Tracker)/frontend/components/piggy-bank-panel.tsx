"use client";

import { formatCurrency, formatPercent } from "@/lib/format";
import { DashboardSummary, Expense } from "@/lib/types";

interface PiggyBankPanelProps {
  summary: DashboardSummary | null;
  expenses?: Expense[];
  monthlyIncomeRecords?: Array<{
    month_key: string;
    monthly_income: number;
  }>;
}

export function PiggyBankPanel({ summary, expenses = [], monthlyIncomeRecords = [] }: PiggyBankPanelProps) {
  const monthlyBudget = summary?.monthly_budget ?? 0;
  const monthlyExpenses = resolveMonthlyExpenses(summary);
  const monthlyIncome = summary?.monthly_income ?? 0;
  const currentCashFlow = monthlyIncome - monthlyExpenses;
  const previousCarryover = calculatePreviousCarryover(expenses, monthlyIncomeRecords, summary?.month_key);
  const piggyBankBalance = Math.max(previousCarryover + currentCashFlow, 0);
  const shortfall = Math.max(-currentCashFlow, 0);
  const positiveCurrentFlow = Math.max(currentCashFlow, 0);
  const piggyPercent = monthlyIncome > 0 ? Math.min((positiveCurrentFlow / monthlyIncome) * 100, 100) : 0;
  const monthLabel = summary?.month_label ?? "Current month";

  return (
    <section className="panel piggy-bank-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Piggy bank</p>
          <h2>Cash-flow surplus carried forward</h2>
          <p className="section-copy">
            Monetra treats the piggy bank as a savings buffer. Positive monthly cash flow increases it, negative monthly cash flow reduces it, and the displayed balance never goes below zero.
          </p>
        </div>
      </div>

      <div className="piggy-bank-hero">
        <div className="piggy-bank-icon" aria-hidden="true">
          GBP
        </div>
        <div>
          <span>Total piggy-bank balance</span>
          <strong>{formatCurrency(piggyBankBalance)}</strong>
          <p>
            {shortfall > 0
              ? `${monthLabel} cash flow is negative by ${formatCurrency(shortfall)}, so the piggy-bank buffer is reduced by that amount where available.`
              : `${monthLabel} increases the piggy bank by ${formatCurrency(currentCashFlow)} because monthly income minus monthly expenses is positive.`}
          </p>
        </div>
      </div>

      <div className="piggy-bank-metrics">
        <article>
          <span>Monthly income</span>
          <strong>{formatCurrency(monthlyIncome)}</strong>
        </article>
        <article>
          <span>Monthly expenses</span>
          <strong>{formatCurrency(monthlyExpenses)}</strong>
        </article>
        <article>
          <span>This month&apos;s cash flow</span>
          <strong>{formatCurrency(currentCashFlow)}</strong>
        </article>
        <article>
          <span>Previous carryover</span>
          <strong>{formatCurrency(previousCarryover)}</strong>
        </article>
        <article>
          <span>Living-cost budget</span>
          <strong>{formatCurrency(monthlyBudget)}</strong>
        </article>
        <article>
          <span>This month&apos;s impact</span>
          <strong>{formatCurrency(currentCashFlow)}</strong>
        </article>
      </div>

      <div className="piggy-progress-block">
        <div className="piggy-progress-header">
          <span>Income flowing into piggy bank</span>
          <strong>{formatPercent(piggyPercent)}</strong>
        </div>
        <div className="piggy-progress-track" aria-label="Piggy bank monthly cash-flow contribution progress">
          <span style={{ width: `${piggyPercent}%` }} />
        </div>
      </div>
    </section>
  );
}

export function resolveMonthlyExpenses(summary: DashboardSummary | null): number {
  return summary?.current_month_total ?? summary?.monthly_expenses ?? 0;
}

export function calculatePreviousCarryover(
  expenses: Expense[],
  monthlyIncomeRecords: Array<{ month_key: string; monthly_income: number }>,
  currentMonthKey?: string,
): number {
  if (!currentMonthKey) {
    return 0;
  }
  const monthlyExpenses = new Map<string, number>();
  for (const item of expenses) {
    const monthKey = String(item.date || "").slice(0, 7);
    if (!monthKey || monthKey >= currentMonthKey) {
      continue;
    }
    const amount = Number(item.amount || 0);
    if (item.entry_type === "expense") {
      monthlyExpenses.set(monthKey, (monthlyExpenses.get(monthKey) ?? 0) + amount);
    }
  }

  const monthlyIncome = new Map<string, number>();
  for (const record of monthlyIncomeRecords) {
    const monthKey = String(record.month_key || "");
    if (!monthKey || monthKey >= currentMonthKey) {
      continue;
    }
    monthlyIncome.set(monthKey, Number(record.monthly_income || 0));
  }

  let carryover = 0;
  const monthKeys = Array.from(new Set([...monthlyIncome.keys(), ...monthlyExpenses.keys()])).sort();
  for (const monthKey of monthKeys) {
    const monthCashFlow = (monthlyIncome.get(monthKey) ?? 0) - (monthlyExpenses.get(monthKey) ?? 0);
    carryover = Math.max(carryover + monthCashFlow, 0);
  }
  return carryover;
}
