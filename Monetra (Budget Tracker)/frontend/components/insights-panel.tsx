import type { CSSProperties } from "react";

import { formatCurrency } from "@/lib/format";
import { CategoryInsightsResponse, WordCloudResponse } from "@/lib/types";

interface InsightsPanelProps {
  categories: CategoryInsightsResponse | null;
  wordCloud: WordCloudResponse | null;
}

function CategoryBars({
  title,
  items,
  tone,
}: {
  title: string;
  items: { category: string; amount: number }[];
  tone: "positive" | "warning";
}) {
  const maxAmount = Math.max(...items.map((item) => item.amount), 1);

  return (
    <div className="insight-card">
      <div className="card-header">
        <h3>{title}</h3>
      </div>
      <div className="bar-list">
        {items.length === 0 ? <p className="muted">No category data for this month.</p> : null}
        {items.map((item) => (
          <div key={`${title}-${item.category}`} className="bar-row">
            <div className="bar-copy">
              <span>{item.category}</span>
              <strong>{formatCurrency(item.amount)}</strong>
            </div>
            <div className="bar-track">
              <div
                className={`bar-fill bar-${tone}`}
                style={{ width: `${(item.amount / maxAmount) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function InsightsPanel({ categories, wordCloud }: InsightsPanelProps) {
  const cloudItems = wordCloud?.frequencies ?? [];
  const cloudCategory = wordCloud?.top_category ?? "top category";
  const cloudCategoryTotal = wordCloud?.top_category_total ?? 0;
  const maxValue = Math.max(...cloudItems.map((item) => item.value), 1);

  return (
    <section className="panel analytics-panel insights-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Monthly insights</p>
          <h2>Category analysis</h2>
          <p className="section-copy">
            Track where money is concentrating and surface the descriptions driving the biggest monthly spend.
          </p>
        </div>
      </div>

      <div className="insights-grid">
        <CategoryBars
          title="Top categories"
          items={categories?.top_categories ?? []}
          tone="positive"
        />
        <CategoryBars
          title="Bottom categories"
          items={categories?.bottom_categories ?? []}
          tone="warning"
        />
      </div>

      <div className="insight-card wordcloud-card">
        <div className="card-header wordcloud-header">
          <div>
            <h3>Word cloud for {cloudCategory}</h3>
            <span className="muted">Highest-spend descriptions inside the leading spend category</span>
          </div>
          {wordCloud?.dominant_label ? (
            <div className="wordcloud-summary-pill">
              <span>Top driver</span>
              <strong>{wordCloud.dominant_label}</strong>
              <small>{formatCurrency(wordCloud.dominant_value ?? 0)}</small>
            </div>
          ) : null}
        </div>

        {cloudItems.length ? (
          <>
            <div className="wordcloud-stats">
              <div className="wordcloud-stat-card">
                <p className="wordcloud-stat-line">
                  <span>Category total: </span>
                  <strong>{formatCurrency(cloudCategoryTotal)}</strong>
                </p>
              </div>
              <div className="wordcloud-stat-card">
                <p className="wordcloud-stat-line">
                  <span>Descriptions surfaced: </span>
                  <strong>{cloudItems.length}</strong>
                </p>
              </div>
            </div>

            <div className="wordcloud-stage" aria-label={`Description word cloud for ${cloudCategory}`}>
              {cloudItems.map((item, index) => {
                const ratio = item.value / maxValue;
                const share = item.share ?? 0;
                const style = {
                  fontSize: `${1 + ratio * 1.45}rem`,
                  opacity: 0.68 + ratio * 0.32,
                  transform: `translateY(${Math.round((1 - ratio) * 8)}px) rotate(${index % 2 === 0 ? -2 : 2}deg)`,
                } satisfies CSSProperties;

                return (
                  <div
                    key={`${item.label}-${index}`}
                    className={`wordcloud-token ${index === 0 ? "wordcloud-token-primary" : ""}`}
                    style={style}
                  >
                    <strong>{item.label}</strong>
                    <span>{formatCurrency(item.value)}</span>
                    <small>{share.toFixed(1)}% of {cloudCategory}</small>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <p className="muted">No expenses found for this month.</p>
        )}
      </div>
    </section>
  );
}
