"use client";

import { AgentWorkflowDefinition, AgentWorkflowRun } from "@/lib/types";

interface AutomationCenterProps {
  workflows: AgentWorkflowDefinition[];
  runs: AgentWorkflowRun[];
  activeWorkflowName: string | null;
  liveStatusMessage: string | null;
  onRunWorkflow: (workflowName: string) => void;
}

export function AutomationCenter({
  workflows,
  activeWorkflowName,
  liveStatusMessage,
  onRunWorkflow,
}: AutomationCenterProps) {
  const activeWorkflow = workflows.find((workflow) => workflow.id === activeWorkflowName) ?? null;

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
          <span>{liveStatusMessage ?? "The workflow is gathering finance context and preparing its automation summary."}</span>
        </div>
      ) : null}

      <div className="workflow-grid">
        {workflows.map((workflow) => {
          const isRunning = activeWorkflowName === workflow.id;
          const isAnyWorkflowRunning = activeWorkflowName !== null;
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
                disabled={isAnyWorkflowRunning}
              >
                {isRunning ? "Running workflow..." : "Run workflow"}
              </button>
            </article>
          );
        })}
      </div>

    </section>
  );
}
