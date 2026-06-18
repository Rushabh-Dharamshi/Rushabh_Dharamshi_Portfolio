"use client";

import { AgentWorkflowRun } from "@/lib/types";
import { formatBackendTimestamp } from "@/lib/date-time";
import { formatAgentOutput } from "@/lib/agent-output-format";

interface EmailAutomationPanelProps {
  runs: AgentWorkflowRun[];
  activeDispatchId: string | null;
  onSendUpcomingBillsEmail: () => void;
  onSendAllUpcomingBillsEmail?: () => void;
  onSendMonthEndEmail: () => void;
}

export function EmailAutomationPanel({
  runs,
  activeDispatchId,
  onSendUpcomingBillsEmail,
  onSendAllUpcomingBillsEmail,
  onSendMonthEndEmail,
}: EmailAutomationPanelProps) {
  const emailRuns = runs.filter((run) => run.workflow_name.includes("email")).slice(0, 4);

  return (
    <section className="panel email-automation-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Email Automation</p>
          <h2>Trigger finance emails on demand</h2>
          <p className="section-copy">
            Send the latest upcoming-bills alert or the current month-end report immediately. The scheduled AI automation still runs in the background.
          </p>
        </div>
      </div>

      <div className="email-automation-grid">
        <article className="email-action-card email-action-card-warning">
          <div className="email-action-copy">
            <p className="eyebrow">Due Soon</p>
            <h3>Send due-soon bills</h3>
            <p>
              Emails late unpaid reminders plus bills due today and the next 7 days. This covers 8 calendar dates total.
            </p>
          </div>
          <button
            className="button email-action-button"
            type="button"
            onClick={onSendUpcomingBillsEmail}
            disabled={activeDispatchId === "upcoming_bills_email"}
          >
            {activeDispatchId === "upcoming_bills_email" ? "Sending due-soon bills..." : "Send due-soon bills"}
          </button>
        </article>

        <article className="email-action-card email-action-card-warning">
          <div className="email-action-copy">
            <p className="eyebrow">All Upcoming</p>
            <h3>Send all upcoming bills</h3>
            <p>
              Emails late unpaid reminders and all projected active recurring bills, so you can review the full upcoming schedule.
            </p>
          </div>
          <button
            className="button email-action-button"
            type="button"
            onClick={onSendAllUpcomingBillsEmail}
            disabled={!onSendAllUpcomingBillsEmail || activeDispatchId === "all_upcoming_bills_email"}
          >
            {activeDispatchId === "all_upcoming_bills_email" ? "Sending all upcoming bills..." : "Send all upcoming bills"}
          </button>
        </article>

        <article className="email-action-card email-action-card-primary">
          <div className="email-action-copy">
            <p className="eyebrow">Month End</p>
            <h3>Send month-end report now</h3>
            <p>
              Generate the PDF report, run the close summary, and email the current month-end pack without waiting for the last calendar day.
            </p>
          </div>
          <button
            className="button email-action-button"
            type="button"
            onClick={onSendMonthEndEmail}
            disabled={activeDispatchId === "month_end_email"}
          >
            {activeDispatchId === "month_end_email" ? "Sending month-end report..." : "Send month-end report"}
          </button>
        </article>
      </div>

      {activeDispatchId ? (
        <div className="message info processing-banner email-processing-banner">
          <strong>Email automation is running.</strong>
          <span>The backend is preparing the latest email payload and sending it through the configured SMTP provider.</span>
        </div>
      ) : null}

      <div className="email-run-history">
        <div className="card-header">
          <h3>Recent email dispatches</h3>
          <span className="muted">{emailRuns.length} logged</span>
        </div>
        {emailRuns.length ? (
          emailRuns.map((run) => {
            const output = formatAgentOutput(run);
            return (
            <article key={run.id} className="email-run-card">
              <div className="card-header">
                <div>
                  <h3>{run.workflow_label}</h3>
                  <p className="muted">{formatBackendTimestamp(run.generated_at)}</p>
                </div>
                <span className={`status-pill status-${mapRiskStatus(run.risk_level)}`}>{run.risk_level} risk</span>
              </div>
              {output.headline && output.headline !== run.workflow_label ? <p><strong>{output.headline}</strong></p> : null}
              {emailRunSummary(output.summary, run.summary).map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
              {output.recommendedActions.length ? (
                <div className="automation-actions-list">
                  <span>Recommended actions</span>
                  <ol>
                    {output.recommendedActions.slice(0, 3).map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ol>
                </div>
              ) : null}
              <div className="workflow-meta">
                <span>{run.email_subject}</span>
                <span>{run.model}</span>
                {run.report_download_url ? (
                  <a href={run.report_download_url} download>
                    Download report
                  </a>
                ) : null}
              </div>
            </article>
            );
          })
        ) : (
          <p className="muted">Manual and scheduled email dispatches will appear here once they run.</p>
        )}
      </div>
    </section>
  );
}

export function mapRiskStatus(riskLevel: string) {
  if (riskLevel === "high") {
    return "over";
  }
  if (riskLevel === "medium") {
    return "warning";
  }
  return "within";
}

export function emailRunSummary(outputSummary: string[], runSummary: string): string[] {
  return outputSummary.length ? outputSummary : [runSummary];
}
