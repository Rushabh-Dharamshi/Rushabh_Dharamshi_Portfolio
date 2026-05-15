"use client";

import { AgentBriefingResponse } from "@/lib/types";
import { formatBackendTimestamp } from "@/lib/date-time";

interface AiAgentPanelProps {
  taskDraft: string;
  result: AgentBriefingResponse | null;
  isRunning: boolean;
  onTaskDraftChange: (value: string) => void;
  onRun: () => void;
}

export function AiAgentPanel({
  taskDraft,
  result,
  isRunning,
  onTaskDraftChange,
  onRun,
}: AiAgentPanelProps) {
  const summaryParagraphs = normalizeParagraphs(result?.summary);
  const emailParagraphs = normalizeParagraphs(result?.email_draft);
  const recommendedActions = normalizeStringList(result?.recommended_actions).map(normalizeSentence);

  return (
    <section className="panel ai-agent-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">AI Agent</p>
          <h2>Local Ollama analysis agent</h2>
          <p className="section-copy">
            Run an ad hoc local analyst that inspects the dashboard, recurring commitments, predictions, and recent transactions before drafting a briefing.
          </p>
          <p className="section-copy">
            The automation workflows below handle repetitive finance tasks. You can also use this panel as a command bar for budget updates, income updates, transaction CRUD, and recurring reminder CRUD.
          </p>
          <p className="section-copy">
            Good prompts are explicit. Examples: "Set my monthly budget to 1600 pounds", "Add an expense for Tube fare of 6.40 pounds today under travel", or "Set a monthly reminder for university house rent on the 23rd of every month from April 2026 to June 2026 inclusive at 452.74 pounds." Start dates are always inclusive, and bounded reminder end dates can be inclusive or exclusive based on your wording.
          </p>
        </div>
        {result ? <span className={`status-pill status-${mapRiskStatus(result.risk_level)}`}>{normalizeSentence(result.risk_level).replace(/[.!?]$/, "")} risk</span> : null}
      </div>

      <div className="agent-prompt">
        <label className="control-stack full-span">
          <span className="control-label">Agent task</span>
          <textarea
            value={taskDraft}
            onChange={(event) => onTaskDraftChange(event.target.value)}
            rows={4}
            placeholder="Ask for a finance briefing, or use a direct command like: replace weekly utility bills with monthly utility bills of 24.51 pounds on the 23rd of each month."
          />
        </label>
        <button className="button button-primary" type="button" onClick={onRun} disabled={isRunning}>
          {isRunning ? "Running agent..." : "Run local agent"}
        </button>
      </div>

      {isRunning ? (
        <div className="message info processing-banner">
          <strong>Processing your request.</strong>
          <span>Ollama is working through your command and this can take a while on local models.</span>
        </div>
      ) : null}

      {result ? (
        <div className="agent-output-grid">
          <article className="insight-card agent-hero-card">
            <div className="card-header">
              <h3>{normalizeSentence(result.headline).replace(/[.!?]$/, "")}</h3>
              <span className="muted">{result.model}</span>
            </div>
            <div className="agent-prose">
              {summaryParagraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
            <div className="agent-meta">
              <span>Generated {formatBackendTimestamp(result.generated_at)}</span>
              <span>{result.tools_used.length} tools used</span>
            </div>
          </article>

          <article className="insight-card agent-action-card">
            <div className="card-header">
              <h3>Recommended actions</h3>
            </div>
            <div className="bar-list agent-action-list">
              {recommendedActions.length ? (
                recommendedActions.map((item, index) => (
                  <div key={item} className="agent-action sentence-action">
                    <span className="agent-action-index">{index + 1}</span>
                    <p>{item}</p>
                  </div>
                ))
              ) : (
                <p className="muted">The agent did not propose any actions.</p>
              )}
            </div>
          </article>

          <article className="insight-card agent-email-card">
            <div className="card-header">
              <h3>Email draft</h3>
              <span className="muted">{normalizeSentence(result.email_subject).replace(/[.!?]$/, "")}</span>
            </div>
            <div className="agent-prose agent-email">
              {emailParagraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
            {result.report_download_url ? (
              <a className="button button-secondary" href={result.report_download_url} download>
                Download agent report
              </a>
            ) : null}
          </article>
        </div>
      ) : (
        <p className="muted">
          Run the agent to generate a local AI briefing, or issue direct commands for budget, income, transactions, and recurring reminders. If Ollama is slow locally, use a smaller model or increase <code>OLLAMA_TIMEOUT_SECONDS</code>.
        </p>
      )}
    </section>
  );
}

function mapRiskStatus(riskLevel: string) {
  if (riskLevel === "high") {
    return "over";
  }
  if (riskLevel === "medium") {
    return "warning";
  }
  return "within";
}

function normalizeStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    const rawItems = value.map((item) => String(item));
    if (rawItems.length && rawItems.every((item) => item.length <= 1)) {
      const joined = rawItems.join("").replace(/\s+/g, " ").trim();
      return joined ? [joined] : [];
    }
    return rawItems
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? [trimmed] : [];
  }
  return [];
}

function normalizeParagraphs(value: unknown): string[] {
  const normalizedSource = typeof value === "string" ? value : String(value ?? "");
  const rawParagraphs = normalizedSource
    .replace(/\r/g, "")
    .split(/\n+/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  if (!rawParagraphs.length) {
    const fallback = normalizeSentence(normalizedSource);
    return fallback ? [fallback] : [];
  }

  return rawParagraphs
    .map((paragraph) => normalizeSentence(paragraph))
    .filter(Boolean);
}

function normalizeSentence(value: string) {
  const cleaned = value
    .replace(/^[\s\-•*\d.)]+/, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!cleaned) {
    return "";
  }
  const capitalized = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  return /[.!?]$/.test(capitalized) ? capitalized : `${capitalized}.`;
}
