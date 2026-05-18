import { formatCurrency } from "@/lib/format";
import { Expense } from "@/lib/types";

interface ExpenseTableProps {
  expenses: Expense[];
  selectedExpenseId: number | null;
  searchId: string;
  onSearchIdChange: (value: string) => void;
  onSearch: () => void;
  onShowAll: () => void;
  onSelect: (expense: Expense) => void;
}

export function ExpenseTable({
  expenses,
  selectedExpenseId,
  searchId,
  onSearchIdChange,
  onSearch,
  onShowAll,
  onSelect,
}: ExpenseTableProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Expenses</p>
          <h2>Expense records</h2>
          <p className="section-copy">
            Select an expense row to edit it, or search by transaction ID when you need a precise expense record quickly.
          </p>
        </div>
        <span className="status-pill status-within">{expenses.length} visible</span>
      </div>

      <div className="table-toolbar">
        <input
          type="number"
          placeholder="Search by ID"
          value={searchId}
          onChange={(event) => onSearchIdChange(event.target.value)}
        />
        <button className="button button-secondary" type="button" onClick={onSearch}>
          Search
        </button>
        <button className="button button-ghost" type="button" onClick={onShowAll}>
          Show all
        </button>
      </div>

      <div className="table-wrapper expense-table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Date</th>
              <th>Category</th>
              <th>Description</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((expense) => (
              <tr
                key={expense.id}
                className={expense.id === selectedExpenseId ? "selected-row" : ""}
                onClick={() => onSelect(expense)}
              >
                <td>{expense.id}</td>
                <td>{expense.date}</td>
                <td>{expense.category}</td>
                <td>{expense.description}</td>
                <td>{formatCurrency(expense.amount)}</td>
              </tr>
            ))}
            {expenses.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-state">
                  No expense records found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
