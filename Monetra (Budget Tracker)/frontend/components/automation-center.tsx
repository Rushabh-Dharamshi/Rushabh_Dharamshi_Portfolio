"use client";

import { AgentWorkflowDefinition, AgentWorkflowRun, RecurringCalendarResponse } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { formatAgentOutput } from "@/lib/agent-output-format";

interface AutomationCenterProps {
  workflows: AgentWorkflowDefinition[];
  runs: AgentWorkflowRun[];
  recurringCalendar?: RecurringCalendarResponse | null;
  activeWorkflowName: string | null;
  liveStatusMessage: string | null;
  onRunWorkflow: (workflowName: string) => void;
}

export function AutomationCenter({
  workflows,
  runs,
  recurringCalendar,
  activeWorkflowName,
  liveStatusMessage,
  onRunWorkflow,
}: AutomationCenterProps) {
  const activeWorkflow = workflows.find((workflow) => workflow.id === activeWorkflowName) ?? null;
  const workflowOutputs: Record<string, string> = {
    month_end_close: "Month-end report, KPI review, recommendations, and a saved history entry.",
    upcoming_bills_check: "Late unpaid reminders plus bills due from today through the end of the current month. Today is included.",
    cash_flow_recovery_plan: "Overspend or cash-flow recovery plan with practical priorities.",
  };
  const workflowDescriptions: Record<string, string> = {
    upcoming_bills_check: "Reviews the current month only: late unpaid reminders and bills due from today through month end.",
  };
  const sortedRuns = [...runs].sort((left, right) => {
    const rightTime = parseWorkflowTime(right.generated_at);
    const leftTime = parseWorkflowTime(left.generated_at);
    if (!Number.isNaN(rightTime) && !Number.isNaN(leftTime) && rightTime !== leftTime) {
      return rightTime - leftTime;
    }
    return right.id - left.id;
  });
  const latestRunByWorkflow = new Map<string, AgentWorkflowRun>();
  for (const run of sortedRuns) {
    if (!latestRunByWorkflow.has(run.workflow_name)) {
      latestRunByWorkflow.set(run.workflow_name, run);
    }
  }
  const latestRun = sortedRuns[0] ?? null;
  const lateReminders = (recurringCalendar?.late_occurrences ?? [])
    .filter((occurrence) => occurrence.entry_type === "expense")
    .sort((left, right) => left.date.localeCompare(right.date) || left.description.localeCompare(right.description));

  return (
    <section className="panel automation-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Automation Center</p>
          <h2>Monetra workflow assistant</h2>
          <p className="section-copy">
            Use this assistant to run repeatable finance workflows. It reviews your current data and shows the latest workflow response here.
          </p>
          <p className="section-copy">
            Workflows do not replace your saved transactions. The upcoming bills check is not an all-bills scan and not the 7-day email window: it reviews late unpaid reminders plus bills due from today through the end of the current month, with today included. When one is running, saved dashboard values remain safe to read; reports, emails, AI context, and history update when the workflow completes.
          </p>
        </div>
      </div>

      <div className="automation-assistant-shell">
        <div className="automation-assistant-topbar">
          <div className="agent-command-identity">
            <div className="rag-avatar rag-avatar-assistant">MA</div>
            <div>
              <strong>Monetra automation assistant</strong>
              <span><span className="rag-status-dot" />Workflow-backed finance operations</span>
            </div>
          </div>
          <div className="agent-command-pills">
            <span className="rag-chip">Reports</span>
            <span className="rag-chip">Bill checks</span>
            <span className="rag-chip">Recovery plans</span>
          </div>
        </div>

        <div className="automation-thread">
          <article className="rag-message rag-message-assistant">
            <div className="rag-avatar rag-avatar-assistant">MA</div>
            <div className="rag-message-body">
              <div className="rag-message-header">
                <strong>Monetra automation assistant</strong>
                <span>@workflow-tools</span>
              </div>
              <div className="rag-bubble rag-bubble-assistant">
                <p>Choose a workflow below. I will run the finance checks and replace this panel with the latest response.</p>
              </div>
            </div>
          </article>

          {lateReminders.length ? (
            <article className="rag-message rag-message-assistant">
              <div className="rag-avatar rag-avatar-assistant">MA</div>
              <div className="rag-message-body">
                <div className="rag-message-header">
                  <strong>Late reminders</strong>
                  <span>{lateReminders.length} overdue</span>
                </div>
                <div className="rag-bubble rag-bubble-assistant">
                  <div className="rag-answer-toolbar">
                    <span className="rag-chip status-over">Needs attention</span>
                    <span className="rag-chip">Current month</span>
                  </div>
                  <div className="automation-actions-list">
                    <span>Unpaid reminders past their due date</span>
                    <ol>
                      {lateReminders.slice(0, 4).map((reminder) => (
                        <li key={`${reminder.recurring_item_id}-${reminder.date}`}>
                          {reminder.description}: {formatCurrency(reminder.amount)} due {reminder.date}
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              </div>
            </article>
          ) : null}

          {activeWorkflow ? (
            <article className="rag-message rag-message-user">
              <div className="rag-message-body">
                <div className="rag-message-header">
                  <strong>You</strong>
                  <span>@workflow-command</span>
                </div>
                <div className="rag-bubble rag-bubble-user">
                  <p>Run {activeWorkflow.label}.</p>
                </div>
              </div>
            </article>
          ) : null}

          {activeWorkflow ? (
            <article className="rag-message rag-message-assistant">
              <div className="rag-avatar rag-avatar-assistant">MA</div>
              <div className="rag-message-body">
                <div className="rag-message-header">
                  <strong>Monetra automation assistant</strong>
                  <span>running</span>
                </div>
                <div className="rag-bubble rag-bubble-assistant">
                  <div className="rag-answer-toolbar">
                    <span className="rag-chip status-warning">Running</span>
                  </div>
                  <p>{liveStatusMessage ?? "The workflow is gathering finance context and preparing derived outputs. Saved dashboard labels remain safe to read while this runs."}</p>
                </div>
              </div>
            </article>
          ) : null}

          {latestRun ? (
            <div className="automation-chat-exchange" key={latestRun.id}>
              <article className="rag-message rag-message-user">
                <div className="rag-message-body">
                  <div className="rag-message-header">
                    <strong>You</strong>
                    <span>@workflow-command</span>
                  </div>
                  <div className="rag-bubble rag-bubble-user">
                    <p>Run {latestRun.workflow_label}.</p>
                  </div>
                </div>
              </article>
              <article className="rag-message rag-message-assistant">
                <div className="rag-avatar rag-avatar-assistant">MA</div>
                <div className="rag-message-body">
                  <div className="rag-message-header">
                    <strong>Monetra automation assistant</strong>
                    <span>{formatWorkflowDate(latestRun.generated_at)}</span>
                  </div>
                  <div className="rag-bubble rag-bubble-assistant">
                    <div className="rag-answer-toolbar">
                      <span className={`rag-chip ${latestRun.risk_level === "high" ? "status-over" : latestRun.risk_level === "medium" ? "status-warning" : "status-within"}`}>
                        {latestRun.status}
                      </span>
                      <span className="rag-chip">{latestRun.workflow_label}</span>
                      <span className="rag-chip">Latest response</span>
                    </div>
                    <AutomationRunCopy run={latestRun} />
                  </div>
                </div>
              </article>
            </div>
          ) : !activeWorkflow ? (
            <article className="rag-message rag-message-assistant">
              <div className="rag-avatar rag-avatar-assistant">MA</div>
              <div className="rag-message-body">
                <div className="rag-message-header">
                  <strong>Monetra automation assistant</strong>
                  <span>ready</span>
                </div>
                <div className="rag-bubble rag-bubble-assistant">
                  <p>No automation response yet. Run a workflow below and I will show the latest output here.</p>
                </div>
              </div>
            </article>
          ) : null}
        </div>

        <div className="automation-command-strip" aria-label="Workflow commands">
          {workflows.map((workflow) => {
            const isRunning = activeWorkflowName === workflow.id;
            const isAnyWorkflowRunning = activeWorkflowName !== null;
            const latestRun = latestRunByWorkflow.get(workflow.id) ?? null;
            return (
              <button
                key={workflow.id}
                className="automation-command-card"
                type="button"
                onClick={() => onRunWorkflow(workflow.id)}
                disabled={isAnyWorkflowRunning}
              >
                <span className={`workflow-status-pill ${isRunning ? "is-running" : ""}`}>
                  {workflowStatusText(isRunning, latestRun)}
                </span>
                <strong>{workflow.label}</strong>
                <span>{workflowDescriptions[workflow.id] ?? workflow.description}</span>
                <small>{workflowOutputs[workflow.id] ?? "Saved workflow response with recommendations."}</small>
                <em>{isRunning ? "Running workflow..." : "Run workflow"}</em>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function AutomationRunCopy({ run }: { run: AgentWorkflowRun }) {
  const display = buildAutomationRunDisplay(run);
  return (
    <div className="automation-response-copy">
      <h3>{display.headline}</h3>
      {display.summary.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
      {display.recommendedActions.length ? (
        <div className="automation-actions-list">
          <span>Recommended actions</span>
          <ol>
            {display.recommendedActions.slice(0, 3).map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ol>
        </div>
      ) : null}
      {display.emailSubject || display.emailDraft.length ? (
        <div className="automation-actions-list">
          <span>Email draft</span>
          {display.emailSubject ? <p><strong>{display.emailSubject}</strong></p> : null}
          {display.emailDraft.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      ) : null}
      <div className="automation-run-footer">
        <span>{run.tools_used.length} tools used</span>
        {run.report_download_url ? <a href={run.report_download_url}>Open report</a> : null}
      </div>
    </div>
  );
}

export function buildAutomationRunDisplay(run: AgentWorkflowRun): {
  headline: string;
  summary: string[];
  recommendedActions: string[];
  emailSubject: string;
  emailDraft: string[];
} {
  const output = formatAgentOutput(run);
  return {
    headline: output.headline,
    summary: output.summary.length ? output.summary : [run.summary],
    recommendedActions: output.recommendedActions.length ? output.recommendedActions : run.recommended_actions,
    emailSubject: output.emailSubject,
    emailDraft: output.emailDraft,
  };
}

export function workflowStatusText(isRunning: boolean, latestRun: AgentWorkflowRun | null): string {
  if (isRunning) {
    return "Running";
  }
  return latestRun ? latestRun.status : "Ready";
}

export function formatWorkflowDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

export function parseWorkflowTime(value: string): number {
  const parsed = Date.parse(value);
  if (!Number.isNaN(parsed)) {
    return parsed;
  }

  const ukDateTime = value.match(
    /^(\d{2})\/(\d{2})\/(\d{4}),?\s+(\d{2}):(\d{2})(?::(\d{2}))?$/,
  );
  if (ukDateTime) {
    const [, day, month, year, hour, minute, second = "0"] = ukDateTime;
    return new Date(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute),
      Number(second),
    ).getTime();
  }

  const sqlDateTime = value.match(
    /^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?$/,
  );
  if (sqlDateTime) {
    const [, year, month, day, hour, minute, second = "0"] = sqlDateTime;
    return new Date(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute),
      Number(second),
    ).getTime();
  }

  return Number.NaN;
}
