import { fireEvent, render, screen } from "@testing-library/react";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { AutomationCenter } from "@/components/automation-center";
import { DashboardSummaryCards } from "@/components/dashboard-summary";
import { EmailAutomationPanel } from "@/components/email-automation-panel";
import { ExpenseForm } from "@/components/expense-form";
import { FinancialPulse } from "@/components/financial-pulse";
import { KpiVisuals } from "@/components/kpi-visuals";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";

describe("component branch coverage", () => {
  it("covers null and fallback states across dashboard components", () => {
    const { container } = render(
      <>
        <DashboardSummaryCards summary={null} />
        <FinancialPulse pulse={null} />
        <KpiVisuals expenses={[]} summary={null} />
      </>,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("covers automation, AI, and finance fallback branches", () => {
    render(
      <>
        <AutomationCenter workflows={[{ id: "upcoming_bills_check", label: "Upcoming bills", description: "Review bills", automation_focus: "Focus", default_task: "Run" }]} runs={[]} activeWorkflowName="upcoming_bills_check" onRunWorkflow={jest.fn()} />
        <AiAgentPanel taskDraft="test" result={null} isRunning={true} onTaskDraftChange={jest.fn()} onRun={jest.fn()} />
        <FinancialPulse pulse={{ health_score: 36, average_transaction: 10, transaction_count: 0, spend_velocity: 1.5, top_category_share: 40, runway_days: null, narrative: "Cash outflow ahead of income.", cash_in: 100, cash_out: 120, net_cash_flow: -20, income_coverage: 83.3, recent_transactions: [], recent_expenses: [] }} />
      </>,
    );

    expect(screen.getByText("Upcoming bills is running.")).toBeInTheDocument();
    expect(screen.getByText("Run a workflow to build an automation history.")).toBeInTheDocument();
    expect(screen.getByText("Processing your request.")).toBeInTheDocument();
    expect(screen.getByText("No recent transactions recorded.")).toBeInTheDocument();
    expect(screen.getByText("Stable")).toBeInTheDocument();
  });

  it("normalizes fragmented AI actions and trace fallbacks", () => {
    render(
      <AiAgentPanel
        taskDraft="test"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={{
          headline: "finance summary",
          summary: "line one\n\nline two",
          risk_level: "medium",
          recommended_actions: ["N", ".", " ", "r", "e", "v", "i", "e", "w"],
          email_subject: "subject line",
          email_draft: "draft line",
          task: "task",
          model: "qwen",
          tools_used: [],
          report_download_url: null,
          generated_at: "invalid time",
          trace: {
            memory: [],
            plan: { intent: "plan intent", success_criteria: [], steps: [] },
            execution_results: [],
            verification: { headline: "done", summary: "verified", risk_level: "low" },
            repair_attempts: 1,
          },
        }}
      />,
    );

    expect(screen.getByText("N. review.")).toBeInTheDocument();
    expect(screen.getByText("No plan trace was returned.")).toBeInTheDocument();
    expect(screen.getByText("No tool execution trace was returned.")).toBeInTheDocument();
    expect(screen.getByText((value) => value.includes("invalid time"))).toBeInTheDocument();
    expect(screen.getByText((value) => value.includes("Medium risk"))).toBeInTheDocument();
    expect(screen.queryByText("Download agent report")).not.toBeInTheDocument();
  });

  it("covers expense form disabled state and recurring planner interactions", () => {
    const onCreate = jest.fn();
    const onUpdate = jest.fn();
    const onDelete = jest.fn();
    const onMarkPaid = jest.fn();
    const onMarkUnpaid = jest.fn();

    render(
      <>
        <ExpenseForm
          form={{ date: "2026-04-01", category: "Travel", description: "Tube", amount: "6.40", entry_type: "expense" }}
          selectedExpenseId={null}
          onChange={jest.fn()}
          onCreate={jest.fn()}
          onUpdate={jest.fn()}
          onDelete={jest.fn()}
          onClear={jest.fn()}
        />
        <RecurringCalendarPanel
          items={[
            { id: 1, category: "Rent", description: "University House Rent", amount: 452.74, entry_type: "expense", frequency: "monthly", start_date: "2026-04-23", end_date: "2026-06-23", active: true },
            { id: 2, category: "Salary", description: "Scholarship", amount: 800, entry_type: "income", frequency: "weekly", start_date: "2026-04-01", end_date: "", active: true },
          ]}
          calendar={{
            window_start: "2026-03-31",
            window_end: "2026-05-04",
            occurrences: [
              { recurring_item_id: 1, date: "2026-04-23", category: "Rent", description: "University House Rent", amount: 452.74, entry_type: "expense", frequency: "monthly", days_until_due: 23 },
            ],
            completed_occurrences: [
              { recurring_item_id: 2, date: "2026-04-01", category: "Salary", description: "Scholarship", amount: 800, entry_type: "income", frequency: "weekly", days_until_due: 0, transaction_id: 77 },
            ],
          }}
          onCreate={onCreate}
          onUpdate={onUpdate}
          onDelete={onDelete}
          onMarkPaid={onMarkPaid}
          onMarkUnpaid={onMarkUnpaid}
        />
      </>,
    );

    expect(screen.getByText("Update expense")).toBeDisabled();
    expect(screen.getByText("Delete expense")).toBeDisabled();
    expect(screen.getByText("Reminder schedule by month")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Paid transaction id"), { target: { value: "55" } });
    fireEvent.click(screen.getByText("Verify and mark paid"));
    expect(onMarkPaid).toHaveBeenCalledWith(1, "2026-04-23", 55);

    fireEvent.click(screen.getByText("Restore reminder"));
    expect(onMarkUnpaid).toHaveBeenCalledWith(2, "2026-04-01");

    fireEvent.click(screen.getByText("Add reminder"));
    expect(onCreate).toHaveBeenCalled();

    fireEvent.click(screen.getAllByRole("button", { name: /University House Rent/i })[0]);
    fireEvent.click(screen.getByText("Update reminder"));
    expect(onUpdate).toHaveBeenCalledWith(1, expect.objectContaining({ description: "University House Rent" }));

    fireEvent.click(screen.getByText("Delete reminder"));
    expect(onDelete).toHaveBeenCalledWith(1);
  });

  it("covers empty recurring planner and email panel fallbacks", () => {
    render(
      <>
        <RecurringCalendarPanel
          items={[]}
          calendar={null}
          onCreate={jest.fn()}
          onUpdate={jest.fn()}
          onDelete={jest.fn()}
          onMarkPaid={jest.fn()}
          onMarkUnpaid={jest.fn()}
        />
        <EmailAutomationPanel runs={[]} activeDispatchId="month_end_email" onSendUpcomingBillsEmail={jest.fn()} onSendMonthEndEmail={jest.fn()} />
        <KpiVisuals
          expenses={[]}
          summary={{
            monthly_budget: 1000,
            current_month_total: 0,
            monthly_expenses: 0,
            monthly_income: 1000,
            net_cash_flow: 1000,
            remaining_budget: 1000,
            weekly_spending: 0,
            percent_spent: 0,
            status: "within",
            month_label: "April 2026",
            month_key: new Date().toISOString().slice(0, 7),
            income_month: new Date().toISOString().slice(0, 7),
          }}
        />
      </>,
    );

    expect(screen.getByText("No recurring reminders scheduled yet.")).toBeInTheDocument();
    expect(screen.getByText("No saved recurring reminders are scheduled ahead.")).toBeInTheDocument();
    expect(screen.getByText("Nothing has been marked as paid in this window yet.")).toBeInTheDocument();
    expect(screen.getByText("No recurring purchases or income reminders created yet.")).toBeInTheDocument();
    expect(screen.getByText("Sending month-end report...")).toBeDisabled();
    expect(screen.getByText("No transactions available for the current month.")).toBeInTheDocument();
    expect(screen.getByText("Monthly trend data will appear once transactions are available.")).toBeInTheDocument();
    expect(screen.getByText("Week 1")).toBeInTheDocument();
  });
});

