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
            Reindex once before first use, then reindex again after data, imports, reports, or workflow outputs change.
            This panel is retrieval-first. Use the action agent separately for CRUD, workflows, and email dispatch.
          </p>
        </div>
        <div className="trace-list compact-trace-list">
          <div className="agent-action">Documents: {status?.document_count ?? 0}</div>
          <div className="agent-action">Chunks: {status?.chunk_count ?? 0}</div>
          <div className="agent-action">Indexed: {formatIndexedAt(status?.indexed_at)}</div>
        </div>
      </div>

      <div className="rag-chat-window" aria-live="polite">
        <div className="rag-chat-topbar">
          <div className="rag-chat-identity">
            <div className="rag-avatar rag-avatar-assistant">MA</div>
            <div>
              <strong>Monetra RAG Assistant</strong>
              <span><span className="rag-status-dot" />Knowledge-grounded finance chat</span>
            </div>
          </div>
          <span className="rag-topbar-pill">RAG</span>
        </div>

        <div className="rag-conversation">
          {answer ? (
            <article className="rag-message rag-message-user">
              <div className="rag-avatar rag-avatar-user">You</div>
              <div className="rag-message-body">
                <div className="rag-message-header">
                  <strong>Your question</strong>
                  <span>{formatIndexedAt(answer.generated_at)}</span>
                </div>
                <div className="rag-bubble rag-bubble-user">
                  <p>{normalizeSentence(answer.question || questionDraft)}</p>
                </div>
              </div>
            </article>
          ) : null}

          {answer ? (
            <article className="rag-message rag-message-assistant">
              <div className="rag-avatar rag-avatar-assistant">MA</div>
              <div className="rag-message-body">
                <div className="rag-message-header">
                  <strong>Monetra RAG Assistant</strong>
                  <span>@knowledge-base</span>
                </div>
                <div className="rag-bubble rag-bubble-assistant">
                  <div className="rag-answer-toolbar">
                    <span className={`rag-chip rag-confidence-${normalizeLabel(answer.confidence).toLowerCase()}`}>
                      Confidence: {normalizeLabel(answer.confidence)}
                    </span>
                    <span className="rag-chip">Grounded answer</span>
                    <span className="rag-chip">{formatIndexedAt(answer.generated_at)}</span>
                  </div>
                  <div className="agent-prose rag-answer-copy">
                    {normalizeParagraphs(answer.answer).map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                  </div>
                </div>
              </div>
            </article>
          ) : (
            <article className="rag-message rag-message-assistant">
              <div className="rag-avatar rag-avatar-assistant">MA</div>
              <div className="rag-message-body">
                <div className="rag-message-header">
                  <strong>Monetra RAG Assistant</strong>
                  <span>@knowledge-base</span>
                </div>
                <div className="rag-bubble rag-bubble-assistant">
                  <div className="agent-prose rag-answer-copy">
                    <p>Ask me about your spending, income, recurring commitments, budgets, reports, or previous finance workflows.</p>
                  </div>
                </div>
              </div>
            </article>
          )}
        </div>

        <div className="rag-chat-composer">
          <label className="rag-composer-input">
            <span className="rag-composer-eyebrow">Ask Monetra</span>
            <textarea
              aria-label="Finance question"
              value={questionDraft}
              onChange={(event) => onQuestionDraftChange(event.target.value)}
              rows={2}
              placeholder="Ask a finance question..."
            />
          </label>
          <div className="rag-composer-actions">
            <button className="button button-primary" type="button" onClick={() => onAsk()} disabled={isQuerying}>
              {isQuerying ? "Asking..." : "Send"}
            </button>
            <button className="button button-secondary" type="button" onClick={() => onReindex()} disabled={isReindexing}>
              {isReindexing ? "Reindexing..." : "Reindex"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

export function formatIndexedAt(value: string | null | undefined) {
  if (!value) {
    return "Not indexed yet";
  }
  return formatBackendTimestamp(value);
}

export function normalizeLabel(value: string) {
  const normalized = value.trim();
  if (!normalized) {
    return "unknown";
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

export function normalizeParagraphs(value: string) {
  return value
    .replace(/\r/g, "")
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map(normalizeSentence);
}

export function normalizeSentence(value: string) {
  const cleaned = value.replace(/\s+/g, " ").trim();
  if (!cleaned) {
    return "";
  }
  const capitalized = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  return /[.!?]$/.test(capitalized) ? capitalized : `${capitalized}.`;
}
