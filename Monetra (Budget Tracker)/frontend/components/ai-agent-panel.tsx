"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AgentBriefingResponse } from "@/lib/types";
import { formatBackendTimestamp } from "@/lib/date-time";
import { formatAgentOutput } from "@/lib/agent-output-format";

const guaranteedPromptGroups = [
  {
    title: "Briefings and reports",
    prompts: [
      "Prepare a CFO-style monthly finance briefing with cash pressure, recurring bill pressure, recommended actions, and an email-ready summary.",
      "Generate the current monthly report and summarise the main budget pressure points.",
      "Send due-soon bills for today plus the next 7 days. This covers 8 calendar dates total and includes late unpaid reminders.",
      "Send all upcoming bills.",
      "Send the month-end email now.",
    ],
  },
  {
    title: "Budget and income",
    prompts: [
      "Set my monthly budget to 1600 pounds.",
      "Set my monthly income to 2400 pounds.",
      "Set my monthly income for 2026-04 to 2400 pounds.",
    ],
  },
  {
    title: "Transactions",
    prompts: [
      "Add an expense for Tube fare of 6.40 pounds today under Travel.",
      "Update the Travel expense called Train pass to 81 pounds on 2026-03-20.",
      "Delete the expense matching Train pass under Travel.",
      "Remove all expenses for June 2026.",
      "Remove all expenses for June 2026 and expenses beyond 18th May 2026.",
    ],
  },
  {
    title: "Recurring reminders",
    prompts: [
      "Set a monthly reminder for university house rent on the 23rd of every month from April 2026 to June 2026 inclusive at 452.74 pounds.",
      "Add a weekly reminder for rent of 850 pounds starting 2026-03-27.",
      "Replace weekly utility bills with monthly utility bills of 24.51 pounds on the 23rd of each month.",
      "Remove the weekly utility bills reminder.",
      "Update the utility bills reminder to 24.51 pounds monthly from 2026-04-23.",
    ],
  },
];

interface AiAgentPanelProps {
  taskDraft: string;
  result: AgentBriefingResponse | null;
  errorMessage?: string | null;
  isRunning: boolean;
  onTaskDraftChange: (value: string) => void;
  onRun: () => void;
}

interface AgentChatEntry {
  id: string;
  command: string;
  status: "success" | "failure";
  title: string;
  body: string[];
  riskLabel: string;
  reportDownloadUrl: string | null;
  recommendedActions: string[];
  emailSubject: string;
  emailDraft: string[];
  generatedAt: string;
}

export function AiAgentPanel({
  taskDraft,
  result,
  errorMessage,
  isRunning,
  onTaskDraftChange,
  onRun,
}: AiAgentPanelProps) {
  const initialResultKey = result ? buildResultKey(result) : "";
  const [chatHistory, setChatHistory] = useState<AgentChatEntry[]>(() =>
    result ? [buildResultEntry(result)] : [],
  );
  const [pendingCommand, setPendingCommand] = useState("");
  const lastResultKeyRef = useRef(initialResultKey);
  const lastErrorKeyRef = useRef("");
  const runningCommand = isRunning ? normalizeSentence(pendingCommand || taskDraft) : "";
  const latestStatus = useMemo(() => {
    const latest = chatHistory.at(-1);
    return latest?.status ?? null;
  }, [chatHistory]);

  useEffect(() => {
    if (!result) {
      return;
    }
    const resultKey = buildResultKey(result);
    if (lastResultKeyRef.current === resultKey) {
      return;
    }
    lastResultKeyRef.current = resultKey;
    setPendingCommand("");
    setChatHistory((items) => [...items, buildResultEntry(result)]);
  }, [result]);

  useEffect(() => {
    if (!errorMessage || isRunning) {
      return;
    }
    const errorKey = `${pendingCommand}|${errorMessage}`;
    if (lastErrorKeyRef.current === errorKey) {
      return;
    }
    lastErrorKeyRef.current = errorKey;
    setChatHistory((items) => [
      ...items,
      {
        id: `failure-${Date.now()}`,
        command: normalizeSentence(pendingCommand || taskDraft || "Run agent command"),
        status: "failure",
        title: "Task did not complete.",
        body: [
          normalizeSentence(errorMessage),
          "No further finance changes were confirmed by the operations agent for this request.",
        ],
        riskLabel: "",
        reportDownloadUrl: null,
        recommendedActions: [],
        emailSubject: "",
        emailDraft: [],
        generatedAt: new Date().toISOString(),
      },
    ]);
    setPendingCommand("");
  }, [errorMessage, isRunning, pendingCommand, taskDraft]);

  function handleRun() {
    setPendingCommand(taskDraft.trim());
    onRun();
  }

  return (
    <section className="panel ai-agent-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">AI Agent</p>
          <h2>Ollama analysis agent</h2>
          <p className="section-copy">
            Run an ad hoc analyst that inspects the dashboard, recurring commitments, predictions, and recent transactions before drafting a briefing.
          </p>
          <p className="section-copy">
            The automation workflows below handle repetitive finance tasks. You can also use this panel as a command bar for budget updates, income updates, transaction CRUD, and recurring reminder CRUD.
          </p>
          <p className="section-copy">
            Direct updates such as monthly income or monthly budget refresh the saved dashboard labels after the action completes. Background workflows may continue after data changes to keep reports, emails, AI context, and automation history current.
          </p>
          <p className="section-copy">
            Use the known-safe prompt structures below when you want predictable model behaviour.
          </p>
        </div>
        {latestStatus ? (
          <span className={`status-pill status-${latestStatus === "success" ? "within" : "over"}`}>
            {latestStatus === "success" ? "Last task completed" : "Last task failed"}
          </span>
        ) : null}
      </div>

      <div className="agent-command-center">
        <div className="agent-command-topbar">
          <div className="agent-command-identity">
            <div className="rag-avatar rag-avatar-assistant">OA</div>
            <div>
              <strong>Ollama operations agent</strong>
              <span><span className="rag-status-dot" />Tool-backed finance automation</span>
            </div>
          </div>
          <div className="agent-command-pills">
            <span className="rag-chip">LangGraph</span>
            <span className="rag-chip">MCP tools</span>
            <span className="rag-chip">Guarded actions</span>
          </div>
        </div>

        <div className="agent-command-layout">
          <aside className="agent-prompt-library" aria-label="Known-safe agent prompt examples">
            <div className="agent-library-header">
              <strong>Prompt library</strong>
              <span>Click a prompt to load it into the command box.</span>
            </div>
            <div className="agent-email-help">
              <strong>Email workflow prompts</strong>
              <p>
                <span>Send due-soon bills</span> runs a one-off email for late unpaid reminders plus bills due today plus the next 7 days. This covers 8 calendar dates total.
                <span>Send all upcoming bills</span> emails late unpaid reminders and the projected upcoming bill schedule.
                <span>Send the month-end email now</span> runs a one-off monthly report email with budget, spending, cash-flow, and category context.
              </p>
              <p>Manual sends do not turn off scheduled automation. If the scheduler is enabled and the normal due conditions are met later, the scheduled workflow can still run.</p>
            </div>
            <div className="agent-prompt-examples">
              {guaranteedPromptGroups.map((group) => (
                <article className="prompt-example-card" key={group.title}>
                  <h3>{group.title}</h3>
                  <div className="prompt-chip-list">
                    {group.prompts.map((prompt) => (
                      <button
                        className="prompt-chip"
                        key={prompt}
                        type="button"
                        onClick={() => onTaskDraftChange(prompt)}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </aside>

          <div className="agent-command-panel">
            <div className="agent-command-thread">
              <article className="rag-message rag-message-assistant">
                <div className="rag-avatar rag-avatar-assistant">OA</div>
                <div className="rag-message-body">
                  <div className="rag-message-header">
                    <strong>Ollama operations agent</strong>
                    <span>@finance-tools</span>
                  </div>
                  <div className="rag-bubble rag-bubble-assistant">
                    <div className="agent-prose rag-answer-copy">
                      <p>Send a finance command, choose a known-safe prompt, or ask for a briefing. Conflicting actions stay locked until the current job completes.</p>
                    </div>
                  </div>
                </div>
              </article>

              {chatHistory.map((entry, entryIndex) => (
                <div className="agent-chat-exchange" key={entry.id}>
                  <article className="rag-message rag-message-user">
                    <div className="rag-message-body">
                      <div className="rag-message-header">
                        <strong>You</strong>
                        <span>@command</span>
                      </div>
                      <div className="rag-bubble rag-bubble-user">
                        <p>{entry.command}</p>
                      </div>
                    </div>
                  </article>

                  <article className="rag-message rag-message-assistant">
                    <div className="rag-avatar rag-avatar-assistant">OA</div>
                    <div className="rag-message-body">
                      <div className="rag-message-header">
                        <strong>Ollama operations agent</strong>
                        <span>{formatBackendTimestamp(entry.generatedAt)}</span>
                      </div>
                      <div className="rag-bubble rag-bubble-assistant">
                        <div className="rag-answer-toolbar">
                          <span className={`rag-chip status-${entry.status === "success" ? "within" : "over"}`}>
                            {entry.status === "success" ? "Successful" : "Failed"}
                          </span>
                          {entry.riskLabel ? (
                            <span className={`status-pill ${riskStatusClass(entry.riskLabel)}`}>
                              {entry.riskLabel}
                            </span>
                          ) : null}
                        </div>
                        <div className="agent-prose rag-answer-copy">
                          <p><strong>{entry.title}</strong></p>
                          {entry.body.map((paragraph) => (
                            <p key={paragraph}>{paragraph}</p>
                          ))}
                          {entry.reportDownloadUrl ? (
                            <p>
                              <a className="agent-report-link" href={entry.reportDownloadUrl}>
                                Open monthly report
                              </a>
                            </p>
                          ) : null}
                          {entry.recommendedActions.length ? (
                            <div className="automation-actions-list">
                              <span>Recommended actions</span>
                              <ol>
                                {entry.recommendedActions.map((action, index) => (
                                  <li key={`${index}-${action}`}>{action}</li>
                                ))}
                              </ol>
                            </div>
                          ) : entry.status === "success" && entryIndex === chatHistory.length - 1 ? (
                            <p>The agent did not propose any actions.</p>
                          ) : null}
                          {entry.emailSubject || entry.emailDraft.length ? (
                            <div className="automation-actions-list">
                              <span>Email-ready summary</span>
                              {entry.emailSubject ? <p><strong>{entry.emailSubject}</strong></p> : null}
                              {entry.emailDraft.map((line, index) => (
                                <p key={`${index}-${line}`}>{line}</p>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </article>
                </div>
              ))}

              {runningCommand ? (
                <article className="rag-message rag-message-user">
                  <div className="rag-message-body">
                    <div className="rag-message-header">
                      <strong>You</strong>
                      <span>@command</span>
                    </div>
                    <div className="rag-bubble rag-bubble-user">
                      <p>{runningCommand}</p>
                    </div>
                  </div>
                </article>
              ) : null}

              {isRunning ? (
                <article className="rag-message rag-message-assistant">
                  <div className="rag-avatar rag-avatar-assistant">OA</div>
                  <div className="rag-message-body">
                    <div className="rag-message-header">
                      <strong>Ollama operations agent</strong>
                      <span>Running</span>
                    </div>
                    <div className="rag-bubble rag-bubble-assistant">
                      <div className="agent-prose rag-answer-copy">
                        <p>Processing your request. Ollama is working through your command and this can take a while. Saved dashboard labels are safe to read after the action completes; workflow-derived reports, emails, AI summaries, and automation history update when their background run completes.</p>
                      </div>
                    </div>
                  </div>
                </article>
              ) : null}

            </div>

            <div className="agent-command-composer">
              <label className="rag-composer-input">
                <span className="rag-composer-eyebrow">Command</span>
                <textarea
                  aria-label="Agent command"
                  value={taskDraft}
                  onChange={(event) => onTaskDraftChange(event.target.value)}
                  rows={3}
                  placeholder="Ask for a finance briefing, update income, generate a report, or manage recurring reminders..."
                />
              </label>
              <button className="button button-primary" type="button" onClick={handleRun} disabled={isRunning}>
                {isRunning ? "Running..." : "Run agent"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {!chatHistory.length && !isRunning ? (
        <p className="muted">
          Run the agent to generate an AI briefing, or issue direct commands for budget, income, transactions, and recurring reminders. If Ollama is slow, use a smaller model or increase <code>OLLAMA_TIMEOUT_SECONDS</code>.
        </p>
      ) : null}
    </section>
  );
}

export function buildResultKey(result: AgentBriefingResponse) {
  return [
    result.generated_at,
    result.task,
    result.headline,
    stableKeyPart(result.summary),
    stableKeyPart(result.recommended_actions),
    stableKeyPart(result.email_draft),
    result.action_result?.type,
    result.action_result?.message,
  ].join("|");
}

export function stableKeyPart(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function buildResultEntry(result: AgentBriefingResponse): AgentChatEntry {
  return {
    id: `success-${buildResultKey(result)}`,
    command: normalizeSentence(result.task),
    status: "success",
    title: getCompletionGuidance(result)?.title ?? "Task completed successfully.",
    riskLabel: normalizeRiskLabel(result.risk_level),
    ...buildSuccessReply(result),
    generatedAt: result.generated_at,
  };
}

export function normalizeRiskLabel(value: unknown) {
  const raw = typeof value === "string" ? value.trim() : "";
  if (!raw) {
    return "";
  }
  const label = raw.toLowerCase().endsWith("risk") ? raw : `${raw} risk`;
  return normalizeSentence(label);
}

export function riskStatusClass(label: string) {
  const lowered = label.toLowerCase();
  if (lowered.includes("high")) {
    return "status-over";
  }
  if (lowered.includes("medium")) {
    return "status-warning";
  }
  return "status-within";
}

export function getCompletionGuidance(result: AgentBriefingResponse | null) {
  const actionType = result?.action_result?.type;
  if (actionType === "monthly_income_updated") {
    return {
      title: "Monthly income update completed.",
      body: "The dashboard has been reloaded for the updated income month. The income label and monthly totals are safe to read or refresh now, while background workflows may continue updating reports and AI context.",
    };
  }
  if (actionType === "monthly_budget_updated") {
    return {
      title: "Monthly budget update completed.",
      body: "The dashboard has been reloaded with the new budget. The budget label and utilisation values are safe to read or refresh now, while background workflows may continue updating reports and AI context.",
    };
  }
  if (actionType === "upcoming_bills_email_sent") {
    return {
      title: "Upcoming bills email sent.",
      body: "This manually runs the upcoming-bills workflow now. The due-soon command checks late unpaid reminders plus bills due today and the next 7 days, so it covers 8 calendar dates total. The all-upcoming command checks the projected upcoming bill schedule. It sends the email to the signed-in user's report email address if email delivery is enabled. This does not disable the scheduled upcoming-bills workflow; if the scheduler is enabled and the normal due conditions are met later, it can still run.",
    };
  }
  if (actionType === "upcoming_bills_email_skipped") {
    return {
      title: "Upcoming bills email not sent.",
      body: "This manually checked the upcoming-bills workflow, but no reminder email was sent because the system did not find eligible upcoming bills for the current send rules.",
    };
  }
  if (actionType === "month_end_email_sent") {
    return {
      title: "Month-end email sent.",
      body: "This manually runs the month-end reporting workflow now. It generates the monthly finance summary/report, includes budget, spending, cash-flow, and category context, and sends the report email to the signed-in user's report email address if email delivery is enabled. This does not disable the scheduled month-end workflow; if the scheduler is enabled and the normal send time is reached later, it can still run.",
    };
  }
  if (actionType === "monthly_report_generated") {
    return {
      title: "Report workflow completed.",
      body: "The report action has finished. You can now check the report link, email delivery status, refreshed dashboard values, and automation history.",
    };
  }
  return null;
}

export function buildSuccessReply(result: AgentBriefingResponse): Pick<AgentChatEntry, "body" | "reportDownloadUrl" | "recommendedActions" | "emailSubject" | "emailDraft"> {
  const completionGuidance = getCompletionGuidance(result);
  const actionType = result.action_result?.type ?? "";
  const actionMessage = normalizeSentence(result.action_result?.message ?? "");
  const formatted = formatAgentOutput(result);
  const showEmailDraft =
    formatted.structured ||
    ["upcoming_bills_email_sent", "month_end_email_sent", "monthly_report_generated"].includes(actionType);
  const paragraphs = [
    completionGuidance?.body,
    actionMessage,
    ...formatted.summary,
  ]
    .map((paragraph) => normalizeSentence(paragraph ?? ""))
    .filter(Boolean);

  return {
    body: Array.from(new Set(paragraphs)).slice(0, 3),
    reportDownloadUrl: result.report_download_url || null,
    recommendedActions: formatted.recommendedActions,
    emailSubject: showEmailDraft ? formatted.emailSubject : "",
    emailDraft: showEmailDraft ? formatted.emailDraft : [],
  };
}

export function normalizeSentence(value: string) {
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
