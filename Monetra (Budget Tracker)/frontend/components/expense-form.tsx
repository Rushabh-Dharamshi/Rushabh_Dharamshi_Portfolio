import { FormState } from "@/lib/types";

interface ExpenseFormProps {
  form: FormState;
  selectedExpenseId: number | null;
  onChange: (next: FormState) => void;
  onCreate: () => void;
  onUpdate: () => void;
  onDelete: () => void;
  onClear: () => void;
}

export function ExpenseForm({
  form,
  selectedExpenseId,
  onChange,
  onCreate,
  onUpdate,
  onDelete,
  onClear,
}: ExpenseFormProps) {
  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    onChange({ ...form, [key]: value, entry_type: "expense" });
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Expense management</p>
          <h2>{selectedExpenseId ? `Editing expense #${selectedExpenseId}` : "Create expense transaction"}</h2>
          <p className="section-copy">
            Capture expense transactions with clean, validated fields so monthly spend, imports, dashboards, and reports all stay aligned. Monthly income is managed separately in Operations.
          </p>
        </div>
      </div>

      <div className="form-grid">
        <label>
          <span>Date</span>
          <input
            type="date"
            value={form.date}
            onChange={(event) => updateField("date", event.target.value)}
          />
        </label>
        <label>
          <span>Type</span>
          <input type="text" value="Expense" disabled />
        </label>
        <label>
          <span>Category</span>
          <input
            type="text"
            value={form.category}
            onChange={(event) => updateField("category", event.target.value)}
            placeholder="Housing, Travel, Food"
          />
        </label>
        <label className="full-span">
          <span>Description</span>
          <input
            type="text"
            value={form.description}
            onChange={(event) => updateField("description", event.target.value)}
            placeholder="Weekly groceries"
          />
        </label>
        <label>
          <span>Amount (GBP)</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.amount}
            onChange={(event) => updateField("amount", event.target.value)}
          />
        </label>
      </div>

      <div className="action-row">
        <button className="button button-primary" type="button" onClick={onCreate}>
          Add expense
        </button>
        <button
          className="button button-secondary"
          type="button"
          onClick={onUpdate}
          disabled={!selectedExpenseId}
        >
          Update expense
        </button>
        <button
          className="button button-danger"
          type="button"
          onClick={onDelete}
          disabled={!selectedExpenseId}
        >
          Delete expense
        </button>
        <button className="button button-ghost" type="button" onClick={onClear}>
          Clear inputs
        </button>
      </div>
    </section>
  );
}