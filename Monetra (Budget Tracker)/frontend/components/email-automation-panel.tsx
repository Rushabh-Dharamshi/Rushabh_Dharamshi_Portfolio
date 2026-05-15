"use client";

import { AgentWorkflowRun } from "@/lib/types";
import { formatBackendTimestamp } from "@/lib/date-time";

interface EmailAutomationPanelProps {
  runs: AgentWorkflowRun[];
  activeDispatchId: string | null;
  onSendUpcomingBillsEmail: () => void;
  onSendMonthEndEmail: () => void;
}

export function EmailAutomationPanel({
  runs,
  activeDispatchId,
  onSendUpcomingBillsEmail,
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
            <h3>Send upcoming bills email now</h3>
            <p>
              Push a fresh 7-day bills update straight to your inbox. If the due list changed after payments or cancellations, this sends the latest state.
            </p>
          </div>
          <button
            className="button email-action-button"
            type="button"
            onClick={onSendUpcomingBillsEmail}
            disabled={activeDispatchId === "upcoming_bills_email"}
          >
            {activeDispatchId === "upcoming_bills_email" ? "Sending upcoming bills email..." : "Send upcoming bills email"}
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
          emailRuns.map((run) => (
            <article key={run.id} className="email-run-card">
              <div className="card-header">
                <div>
                  <h3>{run.workflow_label}</h3>
                  <p className="muted">{formatBackendTimestamp(run.generated_at)}</p>
                </div>
                <span className={`status-pill status-${mapRiskStatus(run.risk_level)}`}>{run.risk_level} risk</span>
              </div>
              <p>{run.summary}</p>
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
          ))
        ) : (
          <p className="muted">Manual and scheduled email dispatches will appear here once they run.</p>
        )}
      </div>
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

