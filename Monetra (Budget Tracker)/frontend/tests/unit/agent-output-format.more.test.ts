import { formatAgentOutput, normalizeParagraphs, normalizeSentence } from "@/lib/agent-output-format";

describe("agent output formatting edge cases", () => {
  it("normalizes empty paragraphs and bare sentences", () => {
    expect(normalizeParagraphs("   ")).toEqual([]);
    expect(normalizeSentence("already done?")).toBe("Already done?");
    expect(normalizeSentence("")).toBe("");
  });

  it("parses structured JSON and builds an email-ready summary when no draft exists", () => {
    const output = formatAgentOutput({
      summary: JSON.stringify({
        headline: "monthly briefing",
        cash_flow: "cash flow is strong",
        recurring_bills: "one recurring bill is due",
        recommended_actions: ["review the bill"],
        email_subject: "June finance briefing",
      }),
    });

    expect(output.structured).toBe(true);
    expect(output.headline).toBe("monthly briefing");
    expect(output.summary).toContain("Cash flow: cash flow is strong.");
    expect(output.emailDraft).toContain("June finance briefing.");
    expect(output.emailDraft).toContain("- Review the bill.");
  });

  it("parses python-style structured output and strips repeated signoffs", () => {
    const output = formatAgentOutput({
      summary: "{'headline': 'briefing', 'cash_flow': 'stable', 'recommended_actions': 'check subscriptions', 'email_draft': 'Dear Rushabh,\\n\\nAll set.\\n\\nBest regards,\\nOld signoff'}",
    });

    expect(output.structured).toBe(true);
    expect(output.recommendedActions).toEqual(["Check subscriptions."]);
    expect(output.emailDraft).toEqual(["Dear Rushabh,", "All set.", "Kind Regards,", "Monetra Organisation"]);
  });

  it("falls back cleanly for invalid structured-looking text and object values", () => {
    const invalid = formatAgentOutput({
      headline: { label: "bad" },
      summary: "{not valid",
      recommended_actions: ["O", "K"],
      email_draft: ["line one", "line two"],
    });

    expect(invalid.structured).toBe(false);
    expect(invalid.headline).toBe('{"label":"bad"}');
    expect(invalid.recommendedActions).toEqual(["OK."]);
    expect(invalid.emailDraft).toContain("Line one.");
    expect(invalid.emailDraft).toContain("Line two.");

    const objectSummary = formatAgentOutput({
      summary: { headline: "object summary", summary: "nested fact", email_draft: null },
    });
    expect(objectSummary.structured).toBe(true);
    expect(objectSummary.summary).toContain("Summary: nested fact.");
  });
});
