"use client";

import { useMemo } from "react";

import { formatCurrency } from "@/lib/format";
import { DashboardSummary, Expense } from "@/lib/types";

interface KpiVisualsProps {
  expenses: Expense[];
  summary: DashboardSummary | null;
}

interface CategoryDatum {
  label: string;
  value: number;
  share: number;
  color: string;
}

const chartPalette = ["#0f766e", "#f59e0b", "#2563eb", "#b42318", "#7c3aed", "#0891b2"];

export function KpiVisuals({ expenses, summary }: KpiVisualsProps) {
  const model = useMemo(() => buildVisualModel(expenses, summary), [expenses, summary]);

  if (!summary) {
    return null;
  }

  return (
    <section className="panel analytics-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">KPI studio</p>
          <h2>Charts and performance signals</h2>
          <p className="section-copy">
            Visualize category concentration, weekly cadence, and multi-month spend trends from live transaction data.
          </p>
        </div>
      </div>

      <div className="kpi-mini-grid">
        <article className="metric-card">
          <span>Month-end forecast</span>
          <strong>{formatCurrency(model.projectedMonthEnd)}</strong>
        </article>
        <article className="metric-card">
          <span>Largest category share</span>
          <strong>{model.topCategoryShare.toFixed(1)}%</strong>
        </article>
        <article className="metric-card">
          <span>Average daily burn</span>
          <strong>{formatCurrency(model.averageDailySpend)}</strong>
        </article>
        <article className="metric-card">
          <span>Current-month transactions</span>
          <strong>{model.currentMonthExpenses.length}</strong>
        </article>
      </div>

      <div className="visual-grid">
        <article className="insight-card">
          <div className="card-header">
            <h3>Category mix</h3>
            <span className="muted">Current month</span>
          </div>
          <div className="donut-layout">
            <DonutChart data={model.categoryMix} />
            <div className="donut-legend">
              {model.categoryMix.length ? (
                model.categoryMix.map((item) => (
                  <div key={item.label} className="legend-row">
                    <span className="legend-swatch" style={{ backgroundColor: item.color }} />
                    <div>
                      <strong>{item.label}</strong>
                      <p>
                        {formatCurrency(item.value)} | {item.share.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="muted">No transactions available for the current month.</p>
              )}
            </div>
          </div>
        </article>

        <article className="insight-card">
          <div className="card-header">
            <h3>Monthly trend</h3>
            <span className="muted">Last 6 months</span>
          </div>
          <TrendChart data={model.monthlyTrend} />
        </article>

        <article className="insight-card">
          <div className="card-header">
            <h3>Weekly cadence</h3>
            <span className="muted">Week-by-week current month</span>
          </div>
          <div className="bar-list">
            {model.weeklyBuckets.length ? (
              model.weeklyBuckets.map((item) => (
                <div key={item.label} className="bar-row">
                  <div className="bar-copy">
                    <span>{item.label}</span>
                    <strong>{formatCurrency(item.value)}</strong>
                  </div>
                  <div className="bar-track">
                    <div
                      className="bar-fill bar-positive"
                      style={{ width: `${item.percent}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="muted">Weekly comparisons will appear once current-month expenses are available.</p>
            )}
          </div>
        </article>
      </div>
    </section>
  );
}

function DonutChart({ data }: { data: CategoryDatum[] }) {
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <svg viewBox="0 0 120 120" className="donut-chart" aria-label="Category mix donut chart">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="#e6eceb" strokeWidth="18" />
      {data.map((item) => {
        const segment = (item.share / 100) * circumference;
        const circle = (
          <circle
            key={item.label}
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={item.color}
            strokeWidth="18"
            strokeDasharray={`${segment} ${circumference - segment}`}
            strokeDashoffset={-offset}
            transform="rotate(-90 60 60)"
          />
        );
        offset += segment;
        return circle;
      })}
      <circle cx="60" cy="60" r="30" fill="#fffaf2" />
      <text x="60" y="56" textAnchor="middle" className="donut-total-label">
        Total
      </text>
      <text x="60" y="72" textAnchor="middle" className="donut-total-value">
        {data.length}
      </text>
    </svg>
  );
}

function TrendChart({ data }: { data: { label: string; value: number }[] }) {
  if (!data.length) {
    return <p className="muted">Monthly trend data will appear once transactions are available.</p>;
  }

  const width = 480;
  const height = 190;
  const padding = 22;
  const maxValue = Math.max(...data.map((item) => item.value), 1);
  const minValue = Math.min(...data.map((item) => item.value), 0);
  const range = Math.max(maxValue - minValue, 1);

  const points = data
    .map((item, index) => {
      const x = padding + (index * (width - padding * 2)) / Math.max(data.length - 1, 1);
      const y =
        height -
        padding -
        ((item.value - minValue) / range) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="trend-chart" aria-label="Monthly spending trend chart">
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="trend-axis" />
      <polyline points={points} className="trend-line" />
      {data.map((item, index) => {
        const x = padding + (index * (width - padding * 2)) / Math.max(data.length - 1, 1);
        const y =
          height -
          padding -
          ((item.value - minValue) / range) * (height - padding * 2);

        return (
          <g key={item.label}>
            <circle cx={x} cy={y} r="4.5" className="trend-point" />
            <text x={x} y={height - 6} textAnchor="middle" className="trend-label">
              {item.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function buildVisualModel(expenses: Expense[], summary: DashboardSummary | null) {
  const spendingExpenses = expenses.filter((expense) => expense.entry_type === "expense");
  const now = new Date();
  const monthKey = now.toISOString().slice(0, 7);
  const currentMonthExpenses = spendingExpenses.filter((expense) => expense.date.startsWith(monthKey));
  const daysElapsed = Math.max(now.getDate(), 1);
  const averageDailySpend = summary ? summary.current_month_total / daysElapsed : 0;
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const projectedMonthEnd = averageDailySpend * daysInMonth;

  const categoryTotals = new Map<string, number>();
  currentMonthExpenses.forEach((expense) => {
    categoryTotals.set(expense.category, (categoryTotals.get(expense.category) ?? 0) + expense.amount);
  });

  const totalCurrentMonth = currentMonthExpenses.reduce((sum, expense) => sum + expense.amount, 0);
  const categoryMix = Array.from(categoryTotals.entries())
    .sort((left, right) => right[1] - left[1])
    .slice(0, 6)
    .map(([label, value], index) => ({
      label,
      value,
      share: totalCurrentMonth ? (value / totalCurrentMonth) * 100 : 0,
      color: chartPalette[index % chartPalette.length],
    }));

  const monthlyTotals = new Map<string, number>();
  spendingExpenses.forEach((expense) => {
    const key = expense.date.slice(0, 7);
    monthlyTotals.set(key, (monthlyTotals.get(key) ?? 0) + expense.amount);
  });

  const monthlyTrend = Array.from(monthlyTotals.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .slice(-6)
    .map(([label, value]) => ({
      label: formatMonthLabel(label),
      value: Number(value.toFixed(2)),
    }));

  const weekRanges = [
    { label: "Week 1", min: 1, max: 7 },
    { label: "Week 2", min: 8, max: 14 },
    { label: "Week 3", min: 15, max: 21 },
    { label: "Week 4+", min: 22, max: 31 },
  ];

  const weeklyBuckets = weekRanges.map((range) => {
    const value = currentMonthExpenses
      .filter((expense) => {
        const day = Number(expense.date.slice(-2));
        return day >= range.min && day <= range.max;
      })
      .reduce((sum, expense) => sum + expense.amount, 0);
    return { label: range.label, value };
  });
  const maxWeeklyValue = Math.max(...weeklyBuckets.map((item) => item.value), 1);

  return {
    currentMonthExpenses,
    averageDailySpend,
    projectedMonthEnd,
    categoryMix,
    monthlyTrend,
    topCategoryShare: categoryMix[0]?.share ?? 0,
    weeklyBuckets: weeklyBuckets.map((item) => ({
      ...item,
      percent: item.value ? (item.value / maxWeeklyValue) * 100 : 0,
    })),
  };
}

function formatMonthLabel(monthKey: string) {
  const [year, month] = monthKey.split("-");
  const label = new Date(Number(year), Number(month) - 1, 1);
  return label.toLocaleString("en-GB", { month: "short" });
}
