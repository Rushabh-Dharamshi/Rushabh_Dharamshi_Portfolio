import { formatCurrency } from "@/lib/format";
import { FinancialPulseResponse } from "@/lib/types";

interface FinancialPulseProps {
  pulse: FinancialPulseResponse | null;
}

export function FinancialPulse({ pulse }: FinancialPulseProps) {
  if (!pulse) {
    return null;
  }

  return (
    <section className="panel pulse-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Innovation spotlight</p>
          <h2>Financial pulse</h2>
          <p className="section-copy">{pulse.narrative}</p>
        </div>
        <div className="pulse-score">
          <span>Health score</span>
          <strong>{pulse.health_score}</strong>
        </div>
      </div>

      <div className="metric-grid">
        <article className="metric-card">
          <span>Average transaction</span>
          <strong>{formatCurrency(pulse.average_transaction)}</strong>
          <small>Average size of recorded income and expense transactions this month.</small>
        </article>
        <article className="metric-card">
          <span>Spend velocity</span>
          <strong>{formatCurrency(pulse.spend_velocity)}/day</strong>
          <small>How quickly expenses are being recorded each day this month.</small>
        </article>
        <article className="metric-card">
          <span>Cash flow</span>
          <strong>{formatCurrency(pulse.net_cash_flow)}</strong>
          <small>Monthly income minus monthly expenses.</small>
        </article>
        <article className="metric-card">
          <span>Income coverage</span>
          <strong>{pulse.income_coverage.toFixed(1)}%</strong>
          <small>Monthly income divided by monthly expenses. Very high values usually mean expenses are still low.</small>
        </article>
        <article className="metric-card">
          <span>Top category share</span>
          <strong>{pulse.top_category_share.toFixed(1)}%</strong>
          <small>The share of monthly expenses coming from your largest spending category.</small>
        </article>
        <article className="metric-card">
          <span>Budget runway</span>
          <strong>{pulse.runway_days !== null ? `${pulse.runway_days} days` : "Stable"}</strong>
          <small>Estimated days your remaining budget lasts at the current daily spend rate.</small>
        </article>
      </div>

      <div className="recent-activity">
        <div className="card-header">
          <h3>Recent activity</h3>
          <span className="muted">{pulse.transaction_count} transactions this month</span>
        </div>

        {pulse.recent_transactions.length ? (
          <div className="activity-list">
            {pulse.recent_transactions.map((expense) => (
              <article key={expense.id} className="activity-item">
                <div>
                  <strong>{expense.description}</strong>
                  <p>
                    {expense.category} | {expense.date} | {expense.entry_type}
                  </p>
                </div>
                <span className={expense.entry_type === "income" ? "amount-positive" : ""}>
                  {expense.entry_type === "income" ? "+" : "-"}
                  {formatCurrency(expense.amount)}
                </span>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No recent transactions recorded.</p>
        )}
      </div>
    </section>
  );
}
