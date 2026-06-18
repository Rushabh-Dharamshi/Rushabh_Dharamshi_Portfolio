export interface FormattedAgentOutput {
  headline: string;
  summary: string[];
  recommendedActions: string[];
  emailSubject: string;
  emailDraft: string[];
  structured: boolean;
}

export function formatAgentOutput(source: {
  headline?: unknown;
  summary?: unknown;
  recommended_actions?: unknown;
  email_subject?: unknown;
  email_draft?: unknown;
}): FormattedAgentOutput {
  const parsed = parseStructuredObject(source.summary) ?? parseStructuredObject(source.email_draft);
  const payload = parsed ?? source;
  const structuredSummary = parsed ? buildStructuredSummary(payload) : "";
  const summaryValue = structuredSummary || payload.summary || source.summary;
  const emailDraftValue = (parsed ? buildEmailReadySummary(payload) : "") || payload.email_draft || source.email_draft;

  return {
    headline: normalizeLabel(readString(payload.headline) || readString(source.headline) || "Finance response"),
    summary: normalizeParagraphs(summaryValue),
    recommendedActions: normalizeList(payload.recommended_actions ?? source.recommended_actions),
    emailSubject: normalizeLabel(readString(payload.email_subject) || readString(source.email_subject)),
    emailDraft: normalizeEmailDraft(emailDraftValue),
    structured: parsed !== null,
  };
}

export function normalizeParagraphs(value: unknown): string[] {
  const text = readString(value);
  if (!text) {
    return [];
  }
  return text
    .replace(/\r/g, "")
    .split(/\n+/)
    .map(normalizeSentence)
    .filter(Boolean);
}

export function normalizeSentence(value: unknown): string {
  const text = readString(value)
    .replace(/\*\*/g, "")
    .replace(/^[\s\-â€¢*\d.)]+/, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) {
    return "";
  }
  const capitalized = text.charAt(0).toUpperCase() + text.slice(1);
  return capitalized.endsWith(".") || capitalized.endsWith("!") || capitalized.endsWith("?") || capitalized.endsWith(":") ? capitalized : `${capitalized}.`;
}

function normalizeLabel(value: unknown): string {
  return readString(value)
    .replace(/\*\*/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function buildStructuredSummary(payload: Record<string, unknown>) {
  const sections = [
    ["Cash flow", payload.cash_flow],
    ["Recurring bill pressure", payload.recurring_bills],
    ["Budget pressure", payload.budget_pressure],
    ["Spending pressure", payload.spending_pressure],
    ["Forecast", payload.forecast],
    ["Summary", payload.summary],
  ]
    .map(([label, value]) => {
      const text = readString(value);
      return text ? `${label}: ${text}` : "";
    })
    .filter(Boolean);
  return sections.length ? sections.join("\n") : "";
}

function buildEmailReadySummary(payload: Record<string, unknown>) {
  const explicitDraft = readString(payload.email_draft);
  if (explicitDraft) {
    return explicitDraft;
  }
  const subject = readString(payload.email_subject) || "Monthly finance briefing";
  const lines = [
    subject,
    "",
    readString(payload.cash_flow),
    readString(payload.recurring_bills),
  ].filter((line, index) => index < 2 || Boolean(line));
  const actions = normalizeList(payload.recommended_actions);
  if (actions.length) {
    lines.push("", "Recommended actions:");
    lines.push(...actions.map((action) => `- ${action}`));
  }
  return lines.length > 2 ? lines.join("\n") : "";
}

export function parseStructuredObject(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "string") {
    return isRecord(value) ? value : null;
  }
  const trimmed = value.trim();
  if (!trimmed.includes("{") || !trimmed.includes("}")) {
    return null;
  }
  const candidate = trimmed.slice(trimmed.indexOf("{"), trimmed.lastIndexOf("}") + 1);
  const jsonParsed = parseJsonObject(candidate);
  if (jsonParsed) {
    return jsonParsed;
  }
  return parsePythonLiteralObject(candidate);
}

export function parseJsonObject(candidate: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(candidate);
    return isRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function parsePythonLiteralObject(candidate: string): Record<string, unknown> | null {
  try {
    const jsonCandidate = candidate
      .replace(/\bNone\b/g, "null")
      .replace(/\bTrue\b/g, "true")
      .replace(/\bFalse\b/g, "false")
      .replace(/'([^'\\]*(?:\\.[^'\\]*)*)'/g, (_, value: string) => JSON.stringify(value.replace(/\\'/g, "'")));
    const parsed = JSON.parse(jsonCandidate);
    return isRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function normalizeEmailDraft(value: unknown): string[] {
  const text = readString(value);
  if (!text) {
    return [];
  }
  const normalizedText = text.replace(/\\r/g, "\r").replace(/\\n/g, "\n");
  const withoutExistingSignoff = normalizedText.replace(
    /\n*\s*(best regards|kind regards|regards),?\s*\n+[\s\S]*$/i,
    "",
  );
  const withStandardSignoff = `${withoutExistingSignoff.trim()}\n\nKind Regards,\nMonetra Organisation`;
  return withStandardSignoff
    .replace(/\r/g, "")
    .replace(/\*\*/g, "")
    .replace(/:\s*-\s*/g, ":\n- ")
    .replace(/\s+-\s+/g, "\n- ")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      if (/^dear\s+.+,$/i.test(line)) {
        return line;
      }
      if (line === "Kind Regards," || line === "Monetra Organisation") {
        return line;
      }
      return line.startsWith("-") ? line : normalizeSentence(line);
    });
}

function normalizeList(value: unknown): string[] {
  if (Array.isArray(value)) {
    if (value.every((item) => typeof item === "string" && item.length <= 1)) {
      const joined = value.join("").trim();
      return joined ? [normalizeSentence(joined)] : [];
    }
    return value.map(normalizeSentence).filter(Boolean);
  }
  const paragraph = normalizeSentence(value);
  return paragraph ? [paragraph] : [];
}

function readString(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(readString).filter(Boolean).join("\n");
  }
  if (isRecord(value)) {
    return JSON.stringify(value);
  }
  return String(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
