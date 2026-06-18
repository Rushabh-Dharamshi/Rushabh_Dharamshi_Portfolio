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
            Choose a planning month, then save the planned budget and expected income for that same month. Imports, exports, reports, forecasts, and budget checks stay in one control surface.
          </p>
        </div>
      </div>

      <div className="budget-editor income-editor">
        <label className="control-stack">
          <span className="control-label">Planning month</span>
          <input
            type="month"
            value={incomeMonthDraft}
            onChange={(event) => onIncomeMonthChange(event.target.value)}
          />
          <small>The month these budget and income values belong to.</small>
        </label>
      </div>

      <div className="budget-editor">
        <label className="control-stack">
          <span className="control-label">Monthly budget for selected month (GBP)</span>
          <input
            type="number"
            min="1"
            step="0.01"
            value={budgetDraft}
            onChange={(event) => onBudgetDraftChange(event.target.value)}
          />
          <small>Your planned living-cost limit for the selected month. This is not income.</small>
        </label>
        <button className="button button-primary" type="button" onClick={onSaveBudget}>
          Save budget for month
        </button>
      </div>

      <div className="budget-editor income-editor">
        <label className="control-stack">
          <span className="control-label">Monthly income for selected month (GBP)</span>
          <input
            type="number"
            min="1"
            step="0.01"
            value={incomeDraft}
            onChange={(event) => onIncomeDraftChange(event.target.value)}
          />
          <small>Money expected or recorded as income for the selected month.</small>
        </label>
        <button className="button button-secondary" type="button" onClick={onSaveIncome}>
          Save income for month
        </button>
      </div>

      <div className="operations-grid">
        <label className="file-upload">
          <span className="file-upload-icon" aria-hidden="true">CSV</span>
          <span className="file-upload-copy">
            <strong>Import transactions</strong>
            <small>Only .csv files are accepted</small>
          </span>
          <span className="file-upload-action" aria-hidden="true">Choose CSV file</span>
          <input
            type="file"
            aria-label="Import CSV"
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
          Generate selected-month PDF
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
          Budget status for {summary.month_label}: {summary.status} at {summary.percent_spent.toFixed(1)}% of the {formatCurrency(summary.monthly_budget)} monthly budget. Cash flow this month: {formatCurrency(summary.net_cash_flow)}. Monthly income recorded for {summary.month_label}: {formatCurrency(summary.monthly_income)}.
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

