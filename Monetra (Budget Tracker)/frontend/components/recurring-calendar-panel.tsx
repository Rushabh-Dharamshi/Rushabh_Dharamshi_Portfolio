"use client";

import { useMemo, useState } from "react";

import { formatCurrency } from "@/lib/format";
import {
  RecurringCalendarResponse,
  RecurringItem,
  RecurringItemPayload,
} from "@/lib/types";

interface RecurringCalendarPanelProps {
  items: RecurringItem[];
  calendar: RecurringCalendarResponse | null;
  onCreate: (payload: RecurringItemPayload) => void;
  onUpdate: (itemId: number, payload: RecurringItemPayload) => void;
  onDelete: (itemId: number) => void;
  onMarkPaid: (itemId: number, occurrenceDate: string, transactionId: number) => void;
  onMarkUnpaid: (itemId: number, occurrenceDate: string) => void;
}

const emptyForm: RecurringItemPayload = {
  category: "",
  description: "",
  amount: "",
  entry_type: "expense",
  frequency: "monthly",
  start_date: "",
  end_date: "",
  active: true,
};

export function RecurringCalendarPanel({
  items,
  calendar,
  onCreate,
  onUpdate,
  onDelete,
  onMarkPaid,
  onMarkUnpaid,
}: RecurringCalendarPanelProps) {
  const [form, setForm] = useState<RecurringItemPayload>(emptyForm);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [transactionDrafts, setTransactionDrafts] = useState<Record<string, string>>({});
  const monthBreakdown = useMemo(() => buildReminderMonthBreakdown(items, calendar?.window_start), [items, calendar?.window_start]);
  const nextWeekOccurrences = useMemo(
    () =>
      (calendar?.occurrences ?? [])
        .filter((occurrence) => occurrence.days_until_due >= 0 && occurrence.days_until_due <= 7)
        .sort((left, right) => left.days_until_due - right.days_until_due || left.description.localeCompare(right.description)),
    [calendar?.occurrences],
  );
  const allReminderOccurrences = useMemo(
    () =>
      monthBreakdown.months.flatMap((month) =>
        month.items.map((occurrence) => ({
          ...occurrence,
          monthLabel: month.label,
        })),
      ),
    [monthBreakdown],
  );

  function fillForm(item: RecurringItem) {
    setSelectedItemId(item.id);
    setForm({
      category: item.category,
      description: item.description,
      amount: item.amount.toString(),
      entry_type: "expense",
      frequency: item.frequency,
      start_date: item.start_date,
      end_date: item.end_date ?? "",
      active: item.active,
    });
  }

  function resetForm() {
    setSelectedItemId(null);
    setForm(emptyForm);
  }

  function occurrenceKey(itemId: number, occurrenceDate: string) {
    return `${itemId}:${occurrenceDate}`;
  }

  return (
    <section className="panel recurring-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Recurring planner</p>
          <h2>Upcoming bills and frequent purchases</h2>
          <p className="section-copy">
            Track repeating travel, rent, subscriptions, and regular income so upcoming cash movement is visible before it hits the ledger.
          </p>
        </div>
      </div>

      <div className="recurring-layout">
        <div className="recurring-calendar-shell">
          <div className="recurring-summary-strip">
            <article className="metric-card">
              <span>Open reminders</span>
              <strong>{calendar?.occurrences.length ?? 0}</strong>
              <small>Upcoming reminder dates still waiting for you to link a matching paid expense number.</small>
            </article>
            <article className="metric-card">
              <span>Completed reminders</span>
              <strong>{calendar?.completed_occurrences.length ?? 0}</strong>
              <small>Reminder occurrences already matched to a verified expense number.</small>
            </article>
          </div>

          <div className="message info verification-note">
            <strong>How expense number verification works.</strong>
            {" "}
            <span>
              Monetra checks that the expense number exists in your account, has the same type, amount, and category as the reminder, and is not already linked to another paid reminder occurrence.
            </span>
          </div>

          <div className="upcoming-list reminder-list-section">
            <div className="card-header">
              <h3>Upcoming reminders due soon</h3>
              <span className="muted">{nextWeekOccurrences.length} due today + next 7 days</span>
            </div>
            <p className="muted">This list includes today and the next 7 days, so it covers 8 calendar dates total.</p>
            <div className="bounded-reminder-list next-week-reminder-list">
              {nextWeekOccurrences.map((occurrence) => {
              const draftKey = occurrenceKey(occurrence.recurring_item_id, occurrence.date);
              return (
                <article
                  key={`${occurrence.recurring_item_id}-${occurrence.date}-${occurrence.description}`}
                  className="activity-item"
                >
                  <div>
                    <strong>{occurrence.description}</strong>
                    <p>
                      {occurrence.category} | {occurrence.frequency} | due in {occurrence.days_until_due} day{occurrence.days_until_due === 1 ? "" : "s"}
                    </p>
                  </div>
                  <div className="activity-item-actions recurring-payment-actions">
                    <span className={occurrence.entry_type === "income" ? "amount-positive" : ""}>
                      {occurrence.entry_type === "income" ? "+" : "-"}
                      {formatCurrency(occurrence.amount)}
                    </span>
                    <input
                      className="transaction-link-input"
                      type="number"
                      min="1"
                      inputMode="numeric"
                      placeholder="Paid expense #"
                      value={transactionDrafts[draftKey] ?? ""}
                      onChange={(event) =>
                        setTransactionDrafts((current) => ({
                          ...current,
                          [draftKey]: event.target.value,
                        }))
                      }
                    />
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => {
                        const transactionId = Number(transactionDrafts[draftKey]);
                        if (!Number.isFinite(transactionId) || transactionId <= 0) {
                          return;
                        }
                        onMarkPaid(occurrence.recurring_item_id, occurrence.date, transactionId);
                      }}
                    >
                      Verify and mark paid
                    </button>
                  </div>
                </article>
              );
            })}
            </div>
            {!nextWeekOccurrences.length ? (
              <p className="muted">No recurring reminders are due today or in the next 7 days.</p>
            ) : null}
          </div>

          <div className="upcoming-list reminder-breakdown reminder-list-section">
            <div className="card-header">
              <h3>All reminders</h3>
              <span className="muted">{monthBreakdown.totalOccurrences} scheduled</span>
            </div>
            <p className="muted">
              Bounded reminders are shown through their saved end date. Open-ended reminders are projected for the next 12 months.
            </p>
            <div className="bounded-reminder-list all-reminder-list">
              {allReminderOccurrences.map((occurrence) => {
                const draftKey = occurrenceKey(occurrence.recurring_item_id, occurrence.date);
                return (
                  <article
                    key={`${occurrence.monthLabel}-${occurrence.recurring_item_id}-${occurrence.date}`}
                    className="month-breakdown-row month-breakdown-row-with-actions"
                  >
                    <div>
                      <strong>{occurrence.description}</strong>
                      <p>
                        {occurrence.monthLabel} | {occurrence.category} | {occurrence.frequency} | due {occurrence.date}
                      </p>
                    </div>
                    <div className="activity-item-actions recurring-payment-actions">
                      <span className={occurrence.entry_type === "income" ? "amount-positive" : ""}>
                        {occurrence.entry_type === "income" ? "+" : "-"}
                        {formatCurrency(occurrence.amount)}
                      </span>
                      <input
                        className="transaction-link-input"
                        type="number"
                      min="1"
                      inputMode="numeric"
                        placeholder="Paid expense #"
                        value={transactionDrafts[draftKey] ?? ""}
                        onChange={(event) =>
                          setTransactionDrafts((current) => ({
                            ...current,
                            [draftKey]: event.target.value,
                          }))
                        }
                      />
                      <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => {
                          const transactionId = Number(transactionDrafts[draftKey]);
                          if (!Number.isFinite(transactionId) || transactionId <= 0) {
                            return;
                          }
                          onMarkPaid(occurrence.recurring_item_id, occurrence.date, transactionId);
                        }}
                      >
                        Verify and mark paid
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
            {!allReminderOccurrences.length ? (
              <p className="muted">No saved recurring reminders are scheduled ahead.</p>
            ) : null}
          </div>

          <div className="upcoming-list reminder-list-section completed-reminder-section">
            <div className="card-header">
              <h3>Completed for this window</h3>
              <span className="muted">{calendar?.completed_occurrences.length ?? 0} cleared</span>
            </div>
            <div className="bounded-reminder-list completed-reminder-list">
              {calendar?.completed_occurrences.map((occurrence) => (
                <article
                  key={`paid-${occurrence.recurring_item_id}-${occurrence.date}-${occurrence.description}`}
                  className="activity-item"
                >
                  <div>
                    <strong>{occurrence.description}</strong>
                    <p>
                      {occurrence.category} | cleared for {occurrence.date}
                      {(occurrence.user_transaction_id ?? occurrence.transaction_id) ? ` | expense #${occurrence.user_transaction_id ?? occurrence.transaction_id}` : ""}
                    </p>
                  </div>
                  <button
                    className="button button-ghost"
                    type="button"
                    onClick={() => onMarkUnpaid(occurrence.recurring_item_id, occurrence.date)}
                  >
                    Restore reminder
                  </button>
                </article>
              ))}
            </div>
            {!calendar?.completed_occurrences.length ? (
              <p className="muted">Nothing has been marked as paid in this window yet.</p>
            ) : null}
          </div>
        </div>

        <div className="recurring-management">
          <div className="card-header">
            <h3>{selectedItemId ? `Editing reminder #${selectedItemId}` : "New recurring reminder"}</h3>
            <button className="button button-ghost" type="button" onClick={resetForm}>
              Clear
            </button>
          </div>

          <div className="form-grid recurring-form-grid">
            <label>
              <span>Category</span>
              <input
                type="text"
                value={form.category}
                onChange={(event) => setForm({ ...form, category: event.target.value })}
              />
            </label>
            <input type="hidden" value="expense" readOnly />
            <label className="full-span">
              <span>Description</span>
              <input
                type="text"
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </label>
            <label>
              <span>Amount (GBP)</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.amount}
                onChange={(event) => setForm({ ...form, amount: event.target.value })}
              />
            </label>
            <label>
              <span>Frequency</span>
              <select
                value={form.frequency}
                onChange={(event) =>
                  setForm({
                    ...form,
                    frequency: event.target.value as RecurringItemPayload["frequency"],
                  })
                }
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </label>
            <label>
              <span>Start date (inclusive)</span>
              <input
                type="date"
                value={form.start_date}
                onChange={(event) => setForm({ ...form, start_date: event.target.value })}
              />
            </label>
            <label>
              <span>End date (optional)</span>
              <input
                type="date"
                value={form.end_date ?? ""}
                onChange={(event) => setForm({ ...form, end_date: event.target.value })}
              />
            </label>
            <label className="toggle-field">
              <span>
                Active
                <small id="recurring-active-help">
                  Ticked means this reminder appears in upcoming schedules and upcoming-bills email checks. Unticked pauses it: the reminder stays saved, but Monetra stops showing it as due or using it in upcoming-bills emails until you turn it back on.
                </small>
              </span>
              <input
                type="checkbox"
                aria-describedby="recurring-active-help"
                checked={form.active}
                onChange={(event) => setForm({ ...form, active: event.target.checked })}
              />
            </label>
          </div>

          <div className="action-row">
            <button
              className="button button-primary"
              type="button"
              onClick={() => {
                onCreate(form);
                resetForm();
              }}
            >
              Add reminder
            </button>
            <button
              className="button button-secondary"
              type="button"
              disabled={!selectedItemId}
              onClick={() => {
                if (selectedItemId) {
                  onUpdate(selectedItemId, form);
                }
              }}
            >
              Update reminder
            </button>
            <button
              className="button button-danger"
              type="button"
              disabled={!selectedItemId}
              onClick={() => {
                if (selectedItemId) {
                  onDelete(selectedItemId);
                  resetForm();
                }
              }}
            >
              Delete reminder
            </button>
          </div>

          <div className="card-header recurring-reminders-header">
            <h3>Recurring reminders</h3>
            <span className="muted">{items.length} saved</span>
          </div>
          <div className="bar-list recurring-reminder-list">
            {items.map((item) => (
              <button
                key={item.id}
                className="recurring-item-row"
                type="button"
                onClick={() => fillForm(item)}
              >
                <div>
                  <strong>{item.description}</strong>
                  <p>
                    {item.category} | {item.frequency} | starts {item.start_date}{item.end_date ? ` | ends ${item.end_date}` : ""}
                  </p>
                </div>
                <span className={item.entry_type === "income" ? "amount-positive" : ""}>
                  {item.entry_type === "income" ? "+" : "-"}
                  {formatCurrency(item.amount)}
                </span>
              </button>
            ))}
            {!items.length ? <p className="muted">No recurring expense reminders created yet.</p> : null}
          </div>
        </div>
      </div>
    </section>
  );
}

type ReminderBreakdownOccurrence = {
  recurring_item_id: number;
  date: string;
  category: string;
  description: string;
  amount: number;
  entry_type: "expense" | "income";
  frequency: "weekly" | "monthly";
};

function buildReminderMonthBreakdown(items: RecurringItem[], rawAnchorDate?: string) {
  const anchorDate = rawAnchorDate ? parseLocalDate(rawAnchorDate) : new Date();
  const horizonEnd = endOfMonth(addMonths(anchorDate, 11));
  const months = new Map<
    string,
    {
      key: string;
      label: string;
      occurrenceCount: number;
      items: ReminderBreakdownOccurrence[];
    }
  >();

  items
    .filter((item) => item.active)
    .forEach((item) => {
      const dueDates = enumerateReminderOccurrences(item, anchorDate, horizonEnd);
      dueDates.forEach((dueDate) => {
        const monthKey = `${dueDate.getFullYear()}-${`${dueDate.getMonth() + 1}`.padStart(2, "0")}`;
        const bucket =
          months.get(monthKey) ?? {
            key: monthKey,
            label: dueDate.toLocaleString("en-GB", { month: "long", year: "numeric" }),
            occurrenceCount: 0,
            items: [],
          };
        bucket.occurrenceCount += 1;
        bucket.items.push({
          recurring_item_id: item.id,
          date: formatLocalKey(dueDate),
          category: item.category,
          description: item.description,
          amount: item.amount,
          entry_type: item.entry_type,
          frequency: item.frequency,
        });
        months.set(monthKey, bucket);
      });
    });

  const normalizedMonths = Array.from(months.values())
    .map((month) => ({
      ...month,
      items: month.items.sort(
        (left, right) => left.date.localeCompare(right.date) || left.description.localeCompare(right.description)
      ),
    }))
    .sort((left, right) => left.key.localeCompare(right.key));

  return {
    totalOccurrences: normalizedMonths.reduce((total, month) => total + month.occurrenceCount, 0),
    months: normalizedMonths,
  };
}

function enumerateReminderOccurrences(item: RecurringItem, anchorDate: Date, horizonEnd: Date) {
  const startDate = parseLocalDate(item.start_date);
  const effectiveEndDate = item.end_date ? parseLocalDate(item.end_date) : horizonEnd;
  const finalDate = effectiveEndDate < horizonEnd ? effectiveEndDate : horizonEnd;
  const occurrences: Date[] = [];

  let dueDate = firstDueOnOrAfter(startDate, item.frequency, anchorDate);
  while (dueDate <= finalDate) {
    occurrences.push(new Date(dueDate));
    dueDate = nextDueDate(dueDate, item.frequency);
  }

  return occurrences;
}

function firstDueOnOrAfter(startDate: Date, frequency: "weekly" | "monthly", targetDate: Date) {
  let dueDate = new Date(startDate);
  while (dueDate < stripTime(targetDate)) {
    dueDate = nextDueDate(dueDate, frequency);
  }
  return dueDate;
}

function nextDueDate(currentDueDate: Date, frequency: "weekly" | "monthly") {
  if (frequency === "weekly") {
    const next = new Date(currentDueDate);
    next.setDate(next.getDate() + 7);
    return next;
  }

  const year = currentDueDate.getFullYear();
  const month = currentDueDate.getMonth();
  const targetDay = currentDueDate.getDate();
  const nextMonthStart = new Date(year, month + 1, 1);
  const nextMonthEnd = endOfMonth(nextMonthStart);
  return new Date(nextMonthStart.getFullYear(), nextMonthStart.getMonth(), Math.min(targetDay, nextMonthEnd.getDate()));
}

function addMonths(value: Date, monthCount: number) {
  return new Date(value.getFullYear(), value.getMonth() + monthCount, 1);
}

function endOfMonth(value: Date) {
  return new Date(value.getFullYear(), value.getMonth() + 1, 0);
}

function stripTime(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function parseLocalDate(rawDate: string) {
  const [year, month, day] = rawDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatLocalKey(value: Date) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}
