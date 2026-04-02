import { formatCurrency } from "@/lib/format";
import { DashboardSummary, PredictionResponse } from "@/lib/types";

interface OperationsPanelProps {
  summary: DashboardSummary | null;
  prediction: PredictionResponse | null;
  exportUrl: string;
  reportUrl: string;
  budgetDraft: string;
  incomeDraft: string;
  incomeMonthDraft: string;
  onImport: (file: File) => void;
  onPredict: () => void;
  onCheckBudget: () => void;
  onBudgetDraftChange: (value: string) => void;
  onIncomeDraftChange: (value: string) => void;
  onIncomeMonthChange: (value: string) => void;
  onSaveBudget: () => void;
  onSaveIncome: () => void;
}

export function OperationsPanel({
  summary,
  prediction,
  exportUrl,
  reportUrl,
  budgetDraft,
  incomeDraft,
  incomeMonthDraft,
  onImport,
  onPredict,
  onCheckBudget,
  onBudgetDraftChange,
  onIncomeDraftChange,
  onIncomeMonthChange,
  onSaveBudget,
  onSaveIncome,
}: OperationsPanelProps) {
  return (
    <section className="panel operations-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Import, reporting, budget and income planning</h2>
          <p className="section-copy">
            Update the monthly budget and record income for a specific month, move data in and out, generate detailed reports, and forecast next month&apos;s spend from one control surface.
          </p>
        </div>
      </div>

      <div className="budget-editor">
        <label className="control-stack">
          <span className="control-label">Monthly budget (GBP)</span>
          <input
            type="number"
            min="1"
            step="0.01"
            value={budgetDraft}
            onChange={(event) => onBudgetDraftChange(event.target.value)}
          />
        </label>
        <button className="button button-primary" type="button" onClick={onSaveBudget}>
          Save budget
        </button>
      </div>

      <div className="budget-editor income-editor">
        <label className="control-stack">
          <span className="control-label">Income month</span>
          <input
            type="month"
            value={incomeMonthDraft}
            onChange={(event) => onIncomeMonthChange(event.target.value)}
          />
        </label>
        <label className="control-stack">
          <span className="control-label">Monthly income (GBP)</span>
          <input
            type="number"
            min="1"
            step="0.01"
            value={incomeDraft}
            onChange={(event) => onIncomeDraftChange(event.target.value)}
          />
        </label>
        <button className="button button-secondary" type="button" onClick={onSaveIncome}>
          Save income for month
        </button>
      </div>

      <div className="operations-grid">
        <label className="file-upload">
          <span>Import CSV</span>
          <input
            type="file"
            accept=".csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                onImport(file);
                event.target.value = "";
              }
            }}
          />
        </label>

        <a className="button button-secondary" href={exportUrl} download>
          Export CSV
        </a>
        <a className="button button-secondary" href={reportUrl} download>
          Generate PDF report
        </a>
        <button className="button button-primary" type="button" onClick={onPredict}>
          Predict next month
        </button>
        <button className="button button-ghost" type="button" onClick={onCheckBudget}>
          Check budget status
        </button>
      </div>

      {summary ? (
        <p className="muted">
          Budget status: {summary.status} at {summary.percent_spent.toFixed(1)}% of monthly budget. Cash flow this month: {formatCurrency(summary.net_cash_flow)}. Monthly income recorded for {summary.month_label}: {formatCurrency(summary.monthly_income)}.
        </p>
      ) : null}

      {prediction ? (
        <div className="prediction-card">
          <span>Next month prediction</span>
          <strong>{prediction.next_month}</strong>
          <p>{formatCurrency(prediction.predicted_spending)}</p>
          <small>
            {prediction.is_budget_exceeded
              ? "Forecast exceeds the budget threshold."
              : "Forecast remains within the budget threshold."}
          </small>
        </div>
      ) : null}
    </section>
  );
}

