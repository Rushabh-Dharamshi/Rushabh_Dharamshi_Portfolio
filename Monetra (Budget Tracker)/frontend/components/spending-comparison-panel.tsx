"use client";

import { useDeferredValue, useMemo, useState } from "react";

import {
  buildSpendingComparison,
  ComparisonGranularity,
  ComparisonMode,
  ComparisonSeries,
} from "@/lib/spending-comparison";
import { formatCurrency } from "@/lib/format";
import { Expense } from "@/lib/types";

interface SpendingComparisonPanelProps {
  expenses: Expense[];
  referenceDate?: Date;
}

export function SpendingComparisonPanel({
  expenses,
  referenceDate,
}: SpendingComparisonPanelProps) {
  const [granularity, setGranularity] = useState<ComparisonGranularity>("monthly");
  const [mode, setMode] = useState<ComparisonMode>("overall");
  const [periodCount, setPeriodCount] = useState(4);
  const [category, setCategory] = useState("");
  const deferredExpenses = useDeferredValue(expenses);

  const bounds =
    granularity === "weekly"
      ? { min: 2, max: 8, label: "weeks" }
      : { min: 2, max: 6, label: "months" };
  const effectivePeriodCount = Math.min(Math.max(periodCount, bounds.min), bounds.max);

  const model = useMemo(
    () =>
      buildSpendingComparison(deferredExpenses, {
        granularity,
        mode,
        periodCount: effectivePeriodCount,
        category,
        referenceDate,
      }),
    [category, deferredExpenses, effectivePeriodCount, granularity, mode, referenceDate],
  );

  return (
    <section className="panel comparison-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Comparison lab</p>
          <h2>Overlay spending comparison</h2>
          <p className="section-copy">
            Drag the comparison window across recent weeks or months and overlay either overall spending or category-level movement.
          </p>
        </div>
      </div>

      <div className="comparison-controls">
        <div className="control-stack">
          <span className="control-label">Time period</span>
          <div className="segmented-control" role="group" aria-label="Time period">
            <button
              className={granularity === "weekly" ? "button is-active" : "button"}
              type="button"
              onClick={() => setGranularity("weekly")}
            >
              Weekly
            </button>
            <button
              className={granularity === "monthly" ? "button is-active" : "button"}
              type="button"
              onClick={() => setGranularity("monthly")}
            >
              Monthly
            </button>
          </div>
        </div>

        <div className="control-stack">
          <span className="control-label">Metric</span>
          <div className="segmented-control" role="group" aria-label="Metric type">
            <button
              className={mode === "overall" ? "button is-active" : "button"}
              type="button"
              onClick={() => setMode("overall")}
            >
              Overall
            </button>
            <button
              className={mode === "category" ? "button is-active" : "button"}
              type="button"
              onClick={() => setMode("category")}
            >
              Category
            </button>
          </div>
        </div>

        <label className="control-stack">
          <span className="control-label">Comparison window</span>
          <div className="range-header">
            <span>Drag to compare {effectivePeriodCount} {bounds.label}</span>
            <strong>{effectivePeriodCount}</strong>
          </div>
          <input
            className="range-slider"
            type="range"
            min={bounds.min}
            max={bounds.max}
            value={effectivePeriodCount}
            onChange={(event) => setPeriodCount(Number(event.target.value))}
          />
        </label>

        {mode === "category" ? (
          <label className="control-stack">
            <span className="control-label">Category</span>
            <select
              value={model.selectedCategory ?? ""}
              onChange={(event) => setCategory(event.target.value)}
            >
              {model.categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <div className="comparison-summary-grid">
        <article className="metric-card">
          <span>Current period</span>
          <strong>{model.currentPeriodLabel ?? "No data"}</strong>
        </article>
        <article className="metric-card">
          <span>Average spend</span>
          <strong>{formatCurrency(model.averagePeriodSpend)}</strong>
        </article>
        <article className="metric-card">
          <span>Strongest period</span>
          <strong>
            {model.strongestPeriodLabel
              ? `${model.strongestPeriodLabel} | ${formatCurrency(model.strongestPeriodValue)}`
              : "No data"}
          </strong>
        </article>
        <article className="metric-card">
          <span>Change vs previous</span>
          <strong>{formatDelta(model.currentPeriodChange)}</strong>
        </article>
      </div>

      {mode === "category" && !model.selectedCategory ? (
        <p className="muted">Add expense transactions before switching to category comparisons.</p>
      ) : !model.series.length ? (
        <p className="muted">Comparison lines will appear once spending transactions are available.</p>
      ) : (
        <div className="comparison-chart-shell">
          <OverlayChart series={model.series} labels={model.xLabels} />
          <div className="comparison-legend">
            {model.series.map((series) => (
              <article key={series.label} className="legend-chip">
                <div className="legend-chip-title">
                  <span className="legend-swatch" style={{ backgroundColor: series.color }} />
                  <strong>{series.shortLabel}</strong>
                </div>
                <span>{formatCurrency(series.total)}</span>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function OverlayChart({
  labels,
  series,
}: {
  labels: string[];
  series: ComparisonSeries[];
}) {
  const width = 620;
  const height = 270;
  const padding = { top: 16, right: 18, bottom: 42, left: 42 };
  const maxValue = Math.max(
    1,
    ...series.flatMap((item) => item.points.map((point) => point.value)),
  );

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="overlay-chart"
      aria-label="Overlay spending comparison chart"
    >
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const y = padding.top + (height - padding.top - padding.bottom) * ratio;
        const valueLabel = formatCurrency((1 - ratio) * maxValue);
        return (
          <g key={ratio}>
            <line
              x1={padding.left}
              y1={y}
              x2={width - padding.right}
              y2={y}
              className="chart-grid-line"
            />
            <text x={10} y={y + 4} className="chart-axis-label">
              {valueLabel}
            </text>
          </g>
        );
      })}

      {series.map((item) => {
        const points = item.points.map((point, index) => {
          const x =
            padding.left +
            (index * (width - padding.left - padding.right)) /
              Math.max(labels.length - 1, 1);
          const y =
            height -
            padding.bottom -
            (point.value / maxValue) * (height - padding.top - padding.bottom);
          return { x, y };
        });

        return (
          <g key={item.label}>
            <polyline
              fill="none"
              points={points.map((point) => `${point.x},${point.y}`).join(" ")}
              stroke={item.color}
              strokeWidth={item.isCurrent ? 3.8 : 2.3}
              strokeOpacity={item.isCurrent ? 1 : 0.52}
              strokeDasharray={item.isCurrent ? undefined : "8 6"}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {points.map((point, index) => (
              <circle
                key={`${item.label}-${labels[index]}`}
                cx={point.x}
                cy={point.y}
                r={item.isCurrent ? 4.2 : 3.1}
                fill={item.color}
                fillOpacity={item.isCurrent ? 1 : 0.7}
              />
            ))}
          </g>
        );
      })}

      {labels.map((label, index) => {
        const x =
          padding.left +
          (index * (width - padding.left - padding.right)) /
            Math.max(labels.length - 1, 1);
        return (
          <text
            key={label}
            x={x}
            y={height - 14}
            textAnchor="middle"
            className="chart-axis-label"
          >
            {label}
          </text>
        );
      })}
    </svg>
  );
}

function formatDelta(value: number | null) {
  if (value === null) {
    return "No baseline";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}
