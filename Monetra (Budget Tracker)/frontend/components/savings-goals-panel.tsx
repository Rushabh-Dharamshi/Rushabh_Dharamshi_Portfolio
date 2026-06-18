"use client";

import { useState } from "react";

import { formatCurrency } from "@/lib/format";
import { SavingsGoal, SavingsGoalPayload } from "@/lib/types";

interface SavingsGoalsPanelProps {
  goals?: SavingsGoal[];
  onCreate: (payload: SavingsGoalPayload) => void;
  onUpdate: (goalId: number, payload: SavingsGoalPayload) => void;
  onDelete: (goalId: number) => void;
}

const emptyGoal: SavingsGoalPayload = {
  name: "",
  target_amount: "",
  current_amount: "",
  target_date: "",
};

export function SavingsGoalsPanel({ goals, onCreate, onUpdate, onDelete }: SavingsGoalsPanelProps) {
  const [selectedGoalId, setSelectedGoalId] = useState<number | null>(null);
  const [form, setForm] = useState<SavingsGoalPayload>(emptyGoal);

  function selectGoal(goal: SavingsGoal) {
    setSelectedGoalId(goal.id);
    setForm({
      name: goal.name,
      target_amount: goal.target_amount.toString(),
      current_amount: goal.current_amount.toString(),
      target_date: goal.target_date ?? "",
    });
  }

  function resetForm() {
    setSelectedGoalId(null);
    setForm(emptyGoal);
  }

  return (
    <section className="panel savings-goals-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Savings goals</p>
          <h2>Track progress toward financial targets</h2>
          <p className="section-copy">
            Plan emergency funds, deposits, holidays, and other targets alongside monthly spending.
          </p>
        </div>
      </div>

      <div className="savings-goal-form">
        <label className="control-stack">
          <span className="control-label">Goal name</span>
          <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </label>
        <label className="control-stack">
          <span className="control-label">Target amount (GBP)</span>
          <input
            type="number"
            min="1"
            step="0.01"
            value={form.target_amount}
            onChange={(event) => setForm({ ...form, target_amount: event.target.value })}
          />
        </label>
        <label className="control-stack">
          <span className="control-label">Current amount (GBP)</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.current_amount}
            onChange={(event) => setForm({ ...form, current_amount: event.target.value })}
          />
        </label>
        <label className="control-stack">
          <span className="control-label">Target date</span>
          <input
            type="date"
            value={goalTargetDateValue(form.target_date)}
            onChange={(event) => setForm({ ...form, target_date: event.target.value })}
          />
        </label>
      </div>

      <div className="action-row">
        <button className="button button-primary" type="button" onClick={() => { onCreate(form); resetForm(); }}>
          Add goal
        </button>
        <button
          className="button button-secondary"
          type="button"
          disabled={!selectedGoalId}
          onClick={() => onUpdate(selectedGoalId as number, form)}
        >
          Update goal
        </button>
        <button
          className="button button-danger"
          type="button"
          disabled={!selectedGoalId}
          onClick={() => {
            if (selectedGoalId) {
              onDelete(selectedGoalId);
              resetForm();
            }
          }}
        >
          Delete goal
        </button>
      </div>

      <div className="savings-goal-list">
        {(goals ?? []).map((goal) => {
          const remainingAmount = Math.max(goal.target_amount - goal.current_amount, 0);
          const progressPercent = Math.min(Math.max(goal.progress_percent, 0), 100);
          return (
            <button className="savings-goal-row" type="button" key={goal.id} onClick={() => selectGoal(goal)}>
              <div className="savings-goal-header">
                <strong>{goal.name}</strong>
                <span>{goal.target_date ? `Target ${goal.target_date}` : "No target date"}</span>
              </div>
              <div className="savings-goal-metrics">
                <span>
                  Saved
                  <strong>{formatCurrency(goal.current_amount)}</strong>
                </span>
                <span>
                  Remaining
                  <strong>{formatCurrency(remainingAmount)}</strong>
                </span>
                <span>
                  Goal
                  <strong>{formatCurrency(goal.target_amount)}</strong>
                </span>
              </div>
              <div className="savings-progress-track" aria-label={`${goal.name} savings progress`}>
                <span style={{ width: `${progressPercent}%` }} />
              </div>
            </button>
          );
        })}
        {!(goals ?? []).length ? <p className="muted">No savings goals created yet.</p> : null}
      </div>
    </section>
  );
}

export function goalTargetDateValue(value: SavingsGoalPayload["target_date"]): string {
  return value ?? "";
}
