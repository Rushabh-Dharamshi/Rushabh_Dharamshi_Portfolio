import { fireEvent, render, screen } from "@testing-library/react";

import { RagQaPanel } from "@/components/rag-qa-panel";

describe("RagQaPanel", () => {
  it("renders status, answer, and retrieved sources", () => {
    const onQuestionDraftChange = jest.fn();
    const onAsk = jest.fn();
    const onReindex = jest.fn();

    render(
      <RagQaPanel
        questionDraft="What changed this month?"
        answer={{
          question: "What changed this month?",
          answer: "Spending increased in housing and travel.",
          confidence: "high",
          follow_up_questions: ["Which recurring bills are due next?"],
          sources: [
            {
              source_label: "Dashboard March 2026",
              doc_type: "dashboard",
              document_id: "dashboard::2026-03",
              excerpt: "Monthly budget is GBP 1050.",
              score: 0.94,
              metadata: {},
            },
          ],
          generated_at: "2026-04-15T09:10:00Z",
        }}
        status={{
          available: true,
          collection_name: "monetra-finance-knowledge",
          indexed_at: "2026-04-15T09:00:00Z",
          document_count: 12,
          chunk_count: 36,
          signature: "sig",
        }}
        isQuerying={false}
        isReindexing={false}
        onQuestionDraftChange={onQuestionDraftChange}
        onAsk={onAsk}
        onReindex={onReindex}
      />,
    );

    expect(screen.getByText("Semantic finance Q&A")).toBeInTheDocument();
    expect(screen.getByText("Documents: 12")).toBeInTheDocument();
    expect(screen.getByText("Chunks: 36")).toBeInTheDocument();
    expect(screen.getByText("Confidence: High")).toBeInTheDocument();
    expect(screen.getByText("Dashboard March 2026")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Finance question"), { target: { value: "How is cash flow?" } });
    fireEvent.click(screen.getByText("Ask knowledge base"));
    fireEvent.click(screen.getByText("Reindex knowledge"));

    expect(onQuestionDraftChange).toHaveBeenCalledWith("How is cash flow?");
    expect(onAsk).toHaveBeenCalled();
    expect(onReindex).toHaveBeenCalled();
  });

  it("renders fallback copy and disabled labels while processing", () => {
    render(
      <RagQaPanel
        questionDraft=""
        answer={null}
        status={null}
        isQuerying={true}
        isReindexing={true}
        onQuestionDraftChange={() => undefined}
        onAsk={() => undefined}
        onReindex={() => undefined}
      />,
    );

    expect(screen.getByText("Querying...")).toBeDisabled();
    expect(screen.getByText("Reindexing...")).toBeDisabled();
    expect(screen.getByText(/Ask natural-language finance questions here/i)).toBeInTheDocument();
    expect(screen.getByText("Documents: 0")).toBeInTheDocument();
  });

  it("normalizes blank confidence and blank follow-up content", () => {
    render(
      <RagQaPanel
        questionDraft="What next?"
        answer={{
          question: "What next?",
          answer: "Answer body",
          confidence: "   ",
          follow_up_questions: ["   "],
          sources: [
            {
              source_label: "Workflow run #5",
              doc_type: "agent_run",
              document_id: "agent-run::5",
              excerpt: "Summary excerpt",
              score: 0.8,
              metadata: {},
            },
          ],
          generated_at: "not-a-date",
        }}
        status={{
          available: true,
          collection_name: "monetra-finance-knowledge",
          indexed_at: "not-a-date",
          document_count: 1,
          chunk_count: 1,
          signature: "sig",
        }}
        isQuerying={false}
        isReindexing={false}
        onQuestionDraftChange={() => undefined}
        onAsk={() => undefined}
        onReindex={() => undefined}
      />,
    );

    expect(screen.getByText("Confidence: unknown")).toBeInTheDocument();
    expect(screen.getByText("not-a-date")).toBeInTheDocument();
  });

  it("renders the no-follow-up placeholder when the answer has no follow-up questions", () => {
    render(
      <RagQaPanel
        questionDraft="What next?"
        answer={{
          question: "What next?",
          answer: "Answer body",
          confidence: "medium",
          follow_up_questions: [],
          sources: [
            {
              source_label: "Workflow run #5",
              doc_type: "agent_run",
              document_id: "agent-run::5",
              excerpt: "Summary excerpt",
              score: 0.8,
              metadata: {},
            },
          ],
          generated_at: "2026-04-15T09:10:00Z",
        }}
        status={null}
        isQuerying={false}
        isReindexing={false}
        onQuestionDraftChange={() => undefined}
        onAsk={() => undefined}
        onReindex={() => undefined}
      />,
    );

    expect(screen.getByText("No follow-up questions were suggested.")).toBeInTheDocument();
  });
});
