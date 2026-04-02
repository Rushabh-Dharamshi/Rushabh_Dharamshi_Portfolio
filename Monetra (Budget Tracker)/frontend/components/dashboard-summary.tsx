import { formatCurrency, formatPercent } from "@/lib/format";
import { DashboardSummary } from "@/lib/types";

interface DashboardSummaryProps {
  summary: DashboardSummary | null;
}

export function DashboardSummaryCards({ summary }: DashboardSummaryProps) {
  if (!summary) {
    return null;
  }

  return (
    <section className="panel summary-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Budget overview</p>
          <h2>{summary.month_label}</h2>
          <p className="section-copy">
            A live operating view of spend, income, cash flow, and remaining runway against the monthly budget.
          </p>
        </div>
        <span className={`status-pill status-${summary.status}`}>{summary.status}</span>
      </div>

      <div className="metric-grid">
        <article className="metric-card">
          <span>Remaining budget</span>
          <strong>{formatCurrency(summary.remaining_budget)}</strong>
        </article>
        <article className="metric-card">
          <span>Monthly expenses</span>
          <strong>{formatCurrency(summary.monthly_expenses)}</strong>
        </article>
        <article className="metric-card">
          <span>Monthly income</span>
          <strong>{formatCurrency(summary.monthly_income)}</strong>
        </article>
        <article className="metric-card">
          <span>Net cash flow</span>
          <strong>{formatCurrency(summary.net_cash_flow)}</strong>
        </article>
        <article className="metric-card">
          <span>Weekly spending</span>
          <strong>{formatCurrency(summary.weekly_spending)}</strong>
        </article>
        <article className="metric-card">
          <span>Monthly budget</span>
          <strong>{formatCurrency(summary.monthly_budget)}</strong>
        </article>
      </div>

      <div className="progress-block">
        <div className="progress-meta">
          <span>Budget consumption</span>
          <strong>{formatPercent(summary.percent_spent)}</strong>
        </div>
        <div className="progress-track">
          <div
            className={`progress-fill progress-${summary.status}`}
            style={{ width: `${Math.min(summary.percent_spent, 100)}%` }}
          />
        </div>
      </div>
    </section>
  );
}

