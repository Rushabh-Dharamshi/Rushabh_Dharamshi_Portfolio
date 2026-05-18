"use client";

import { RagAnswerResponse, RagStatusResponse } from "@/lib/types";
import { formatBackendTimestamp } from "@/lib/date-time";

interface RagQaPanelProps {
  questionDraft: string;
  answer: RagAnswerResponse | null;
  status: RagStatusResponse | null;
  isQuerying: boolean;
  isReindexing: boolean;
  onQuestionDraftChange: (value: string) => void;
  onAsk: () => void;
  onReindex: () => void;
}

export function RagQaPanel({
  questionDraft,
  answer,
  status,
  isQuerying,
  isReindexing,
  onQuestionDraftChange,
  onAsk,
  onReindex,
}: RagQaPanelProps) {
  return (
    <section className="panel rag-qa-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">RAG Knowledge Base</p>
          <h2>Semantic finance Q&amp;A</h2>
          <p className="section-copy">
            Ask questions about historical spending, recurring commitments, reports, and prior agent outputs.
            This panel is retrieval-first. Use the action agent separately for CRUD, workflows, and email dispatch.
          </p>
        </div>
        <div className="trace-list compact-trace-list">
          <div className="agent-action">Documents: {status?.document_count ?? 0}</div>
          <div className="agent-action">Chunks: {status?.chunk_count ?? 0}</div>
          <div className="agent-action">Indexed: {formatIndexedAt(status?.indexed_at)}</div>
        </div>
      </div>

      <div className="agent-prompt">
        <label className="control-stack full-span">
          <span className="control-label">Finance question</span>
          <textarea
            value={questionDraft}
            onChange={(event) => onQuestionDraftChange(event.target.value)}
            rows={4}
            placeholder="Example: Which categories and recurring reminders are putting the most pressure on cash flow this month?"
          />
        </label>
        <div className="hero-pill-row">
          <button className="button button-primary" type="button" onClick={() => onAsk()} disabled={isQuerying}>
            {isQuerying ? "Querying..." : "Ask knowledge base"}
          </button>
          <button className="button button-secondary" type="button" onClick={() => onReindex()} disabled={isReindexing}>
            {isReindexing ? "Reindexing..." : "Reindex knowledge"}
          </button>
        </div>
      </div>

      {answer ? (
        <div className="agent-output-grid">
          <article className="insight-card agent-hero-card">
            <div className="card-header">
              <h3>Answer</h3>
              <span className="muted">Confidence: {normalizeLabel(answer.confidence)}</span>
            </div>
            <div className="agent-prose">
              {normalizeParagraphs(answer.answer).map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
            <div className="agent-meta">
              <span>{answer.sources.length} sources cited</span>
              <span>{formatIndexedAt(answer.generated_at)}</span>
            </div>
          </article>

          <article className="insight-card agent-action-card">
            <div className="card-header">
              <h3>Follow-up questions</h3>
            </div>
            <div className="bar-list agent-action-list">
              {answer.follow_up_questions.length ? (
                answer.follow_up_questions.map((item, index) => (
                  <div key={`${item}-${index}`} className="agent-action sentence-action">
                    <span className="agent-action-index">{index + 1}</span>
                    <p>{normalizeSentence(item)}</p>
                  </div>
                ))
              ) : (
                <p className="muted">No follow-up questions were suggested.</p>
              )}
            </div>
          </article>

          <article className="insight-card trace-card full-span-card">
            <div className="card-header">
              <h3>Retrieved sources</h3>
              <span className="muted">Semantic context used for the answer</span>
            </div>
            <div className="trace-list rag-source-list">
              {answer.sources.map((source, index) => (
                <div key={`${source.document_id}-${index}`} className="trace-step-card">
                  <strong>{source.source_label}</strong>
                  <p>{normalizeSentence(source.doc_type.replace(/_/g, " "))}</p>
                  <p>{source.excerpt}</p>
                  <code>score={source.score.toFixed(4)}</code>
                </div>
              ))}
            </div>
          </article>
        </div>
      ) : (
        <p className="muted">
          Ask natural-language finance questions here. The response is grounded in semantically retrieved budget,
          transaction, recurring, settings, prediction, and workflow data stored in the local Chroma collection.
        </p>
      )}
    </section>
  );
}

function formatIndexedAt(value: string | null | undefined) {
  if (!value) {
    return "Not indexed yet";
  }
  return formatBackendTimestamp(value);
}

function normalizeLabel(value: string) {
  const normalized = value.trim();
  if (!normalized) {
    return "unknown";
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function normalizeParagraphs(value: string) {
  return value
    .replace(/\r/g, "")
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map(normalizeSentence);
}

function normalizeSentence(value: string) {
  const cleaned = value.replace(/\s+/g, " ").trim();
  if (!cleaned) {
    return "";
  }
  const capitalized = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  return /[.!?]$/.test(capitalized) ? capitalized : `${capitalized}.`;
}
