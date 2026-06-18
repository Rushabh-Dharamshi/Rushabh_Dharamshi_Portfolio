import { useMemo, useState } from "react";

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
  const [textFilter, setTextFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [startDateFilter, setStartDateFilter] = useState("");
  const [endDateFilter, setEndDateFilter] = useState("");
  const filteredExpenses = useMemo(() => {
    const normalizedText = textFilter.trim().toLowerCase();
    const normalizedCategory = categoryFilter.trim().toLowerCase();
    return expenses.filter((expense) => {
      const matchesText =
        !normalizedText ||
        expense.description.toLowerCase().includes(normalizedText) ||
        expense.category.toLowerCase().includes(normalizedText);
      const matchesCategory = !normalizedCategory || expense.category.toLowerCase() === normalizedCategory;
      const matchesStart = !startDateFilter || expense.date >= startDateFilter;
      const matchesEnd = !endDateFilter || expense.date <= endDateFilter;
      return matchesText && matchesCategory && matchesStart && matchesEnd;
    });
  }, [categoryFilter, endDateFilter, expenses, startDateFilter, textFilter]);

  const categories = useMemo(
    () => Array.from(new Set(expenses.map((expense) => expense.category))).sort((left, right) => left.localeCompare(right)),
    [expenses],
  );
  const visibleExpenseTotal = useMemo(
    () =>
      filteredExpenses
        .filter((expense) => expense.entry_type === "expense")
        .reduce((total, expense) => total + expense.amount, 0),
    [filteredExpenses],
  );
  const visibleIncomeTotal = useMemo(
    () =>
      filteredExpenses
        .filter((expense) => expense.entry_type === "income")
        .reduce((total, expense) => total + expense.amount, 0),
    [filteredExpenses],
  );
  const latestVisibleDate = useMemo(
    () => filteredExpenses.map((expense) => expense.date).sort().at(-1) ?? "No records",
    [filteredExpenses],
  );

  return (
    <section className="panel expense-records-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Expenses</p>
          <h2>Expense records</h2>
          <p className="section-copy">
            Select an expense row to edit it, or search by transaction ID when you need a precise expense record quickly.
          </p>
        </div>
        <span className="status-pill status-within">{filteredExpenses.length} visible</span>
      </div>

      <div className="expense-record-summary" aria-label="Visible expense record summary">
        <article>
          <span>Visible outflow</span>
          <strong>{formatCurrency(visibleExpenseTotal)}</strong>
        </article>
        <article>
          <span>Visible income</span>
          <strong className="amount-positive">{formatCurrency(visibleIncomeTotal)}</strong>
        </article>
        <article>
          <span>Categories</span>
          <strong>{categories.length}</strong>
        </article>
        <article>
          <span>Latest date</span>
          <strong>{latestVisibleDate}</strong>
        </article>
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

      <div className="table-toolbar transaction-filter-toolbar">
        <input
          type="search"
          placeholder="Filter description or category"
          value={textFilter}
          onChange={(event) => setTextFilter(event.target.value)}
        />
        <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
        <input
          type="date"
          aria-label="Filter start date"
          value={startDateFilter}
          onChange={(event) => setStartDateFilter(event.target.value)}
        />
        <input
          type="date"
          aria-label="Filter end date"
          value={endDateFilter}
          onChange={(event) => setEndDateFilter(event.target.value)}
        />
        <button
          className="button button-ghost"
          type="button"
          onClick={() => {
            setTextFilter("");
            setCategoryFilter("");
            setStartDateFilter("");
            setEndDateFilter("");
          }}
        >
          Clear filters
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
            {filteredExpenses.map((expense) => (
              <tr
                key={expense.id}
                className={expense.id === selectedExpenseId ? "selected-row" : ""}
                onClick={() => onSelect(expense)}
              >
                <td><span className="record-id-pill">#{expense.id}</span></td>
                <td>{expense.date}</td>
                <td><span className="category-pill">{expense.category}</span></td>
                <td>{expense.description}</td>
                <td>
                  <span className={expense.entry_type === "income" ? "record-amount amount-positive" : "record-amount amount-negative"}>
                    {expense.entry_type === "income" ? "+" : "-"}
                    {formatCurrency(expense.amount)}
                  </span>
                </td>
              </tr>
            ))}
            {filteredExpenses.length === 0 ? (
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
