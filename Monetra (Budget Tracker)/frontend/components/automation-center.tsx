"use client";

import { AgentWorkflowDefinition, AgentWorkflowRun } from "@/lib/types";

interface AutomationCenterProps {
  workflows: AgentWorkflowDefinition[];
  runs: AgentWorkflowRun[];
  activeWorkflowName: string | null;
  onRunWorkflow: (workflowName: string) => void;
}

export function AutomationCenter({
  workflows,
  runs,
  activeWorkflowName,
  onRunWorkflow,
}: AutomationCenterProps) {
  const activeWorkflow = workflows.find((workflow) => workflow.id === activeWorkflowName) ?? null;
  const latestRuns = runs.slice(0, 3);

  return (
    <section className="panel automation-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Automation Center</p>
          <h2>Agent workflows for repetitive finance tasks</h2>
          <p className="section-copy">
            Use the local Ollama automation layer to run repeatable workflows such as month-end close, upcoming bill review, and cash-flow recovery planning.
          </p>
        </div>
      </div>

      {activeWorkflow ? (
        <div className="message info processing-banner">
          <strong>{activeWorkflow.label} is running.</strong>
          <span>The workflow is gathering finance context and preparing its automation summary.</span>
        </div>
      ) : null}

      <div className="workflow-grid">
        {workflows.map((workflow) => {
          const isRunning = activeWorkflowName === workflow.id;
          return (
            <article key={workflow.id} className="workflow-card">
              <div className="card-header">
                <h3>{workflow.label}</h3>
                <span className="muted">{workflow.id.replaceAll("_", " ")}</span>
              </div>
              <p>{workflow.description}</p>
              <p className="muted">{workflow.automation_focus}</p>
              <button
                className="button button-primary"
                type="button"
                onClick={() => onRunWorkflow(workflow.id)}
                disabled={isRunning}
              >
                {isRunning ? "Running workflow..." : "Run workflow"}
              </button>
            </article>
          );
        })}
      </div>

      <div className="workflow-run-list">
        <div className="card-header">
          <h3>Recent workflow runs</h3>
          <span className="muted">{latestRuns.length} most recent</span>
        </div>

        {latestRuns.length ? (
          latestRuns.map((run) => (
            <article key={run.id} className="workflow-run-card">
              <div className="card-header">
                <div>
                  <h3>{run.workflow_label}</h3>
                  <p className="muted">
                    {formatTimestamp(run.generated_at)} | {run.model}
                  </p>
                </div>
                <span className={`status-pill status-${mapRiskStatus(run.risk_level)}`}>{run.risk_level} risk</span>
              </div>
              <p>{run.summary}</p>
              <div className="workflow-action-columns">
                <div>
                  <strong>Automated actions</strong>
                  <div className="bar-list">
                    {run.automated_actions.map((item) => (
                      <div key={item} className="agent-action">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <strong>Recommended next actions</strong>
                  <div className="bar-list">
                    {run.recommended_actions.length ? (
                      run.recommended_actions.map((item) => (
                        <div key={item} className="agent-action">
                          {item}
                        </div>
                      ))
                    ) : (
                      <p className="muted">No extra follow-up actions were suggested.</p>
                    )}
                  </div>
                </div>
              </div>
              <div className="workflow-meta">
                <span>{run.tools_used.length} tools used</span>
                <span>{run.email_subject}</span>
                {run.report_download_url ? (
                  <a href={run.report_download_url} download>
                    Download report
                  </a>
                ) : null}
              </div>
            </article>
          ))
        ) : (
          <p className="muted">Run a workflow to build an automation history.</p>
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

function formatTimestamp(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("en-GB");
}
