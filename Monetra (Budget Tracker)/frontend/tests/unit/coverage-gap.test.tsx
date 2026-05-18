import { fireEvent, render, screen } from "@testing-library/react";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { AutomationCenter } from "@/components/automation-center";
import { ExpenseForm } from "@/components/expense-form";
import { KpiVisuals } from "@/components/kpi-visuals";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";

describe("frontend coverage gaps", () => {
  it("hides AI trace details while preserving high risk status and string normalization branches", () => {
    const cyclic: { self?: unknown } = {};
    cyclic.self = cyclic;

    render(
      <AiAgentPanel
        taskDraft="Run review"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={{
          headline: "critical finance review",
          summary: ["first finding", "second finding"] as unknown as string,
          risk_level: "high",
          recommended_actions: "review the deficit immediately" as unknown as string[],
          email_subject: "finance warning",
          email_draft: { body: "structured draft" } as unknown as string,
          task: "Run review",
          model: "qwen",
          tools_used: ["get_dashboard_summary", "generate_monthly_report"],
          report_download_url: "/api/reports/monthly",
          generated_at: "2026-04-03T12:30:00Z",
          trace: {
            memory: [],
            plan: {
              intent: "review finance health",
              success_criteria: "identify the main risk" as unknown as string[],
              steps: [
                { tool: "get_dashboard_summary", reason: "inspect totals", arguments: { month: "2026-04" } },
                {},
              ],
            },
            execution_results: [
              { tool: "get_dashboard_summary", reason: "loaded summary", arguments: { month: "2026-04" }, result: { ok: true } },
              { tool: "broken_tool", reason: "cyclic output", arguments: { raw: true }, result: cyclic },
            ],
            verification: {
              headline: "verification complete",
              summary: ["all checks finished"] as unknown as string,
              risk_level: "high",
            },
            repair_attempts: 2,
          },
        }}
      />,
    );

    expect(screen.getByText("High risk")).toBeInTheDocument();
    expect(screen.queryByText("Agent trace")).not.toBeInTheDocument();
    expect(screen.queryByText("Identify the main risk.")).not.toBeInTheDocument();
    expect(screen.queryByText("1. get_dashboard_summary")).not.toBeInTheDocument();
    expect(screen.queryByText("broken_tool")).not.toBeInTheDocument();
    expect(screen.getByText("[object Object].")).toBeInTheDocument();
    expect(screen.getByText("Review the deficit immediately.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download agent report" })).toHaveAttribute("href", "/api/reports/monthly");
  });

  it("covers automation workflow buttons without rendering run history", () => {
    render(
      <AutomationCenter
        workflows={[
          {
            id: "cash_flow_recovery_plan",
            label: "Cash-flow recovery",
            description: "Recover cash flow.",
            automation_focus: "Risk remediation.",
            default_task: "Run.",
          },
        ]}
        runs={[
          {
            id: 7,
            workflow_name: "cash_flow_recovery_plan",
            workflow_label: "Cash-flow recovery",
            status: "completed",
            headline: "Recovery plan ready",
            summary: "A recovery plan was generated.",
            risk_level: "medium",
            recommended_actions: [],
            automated_actions: ["Generated recovery analysis."],
            email_subject: "Recovery plan",
            email_draft: "Review the plan.",
            task: "Run.",
            model: "mistral",
            tools_used: [],
            report_download_url: null,
            generated_at: "invalid timestamp",
          },
        ]}
        activeWorkflowName={null}
        liveStatusMessage={null}
        onRunWorkflow={jest.fn()}
      />,
    );

    expect(screen.getByText("Cash-flow recovery")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run workflow" })).toBeInTheDocument();
    expect(screen.queryByText("medium risk")).not.toBeInTheDocument();
  });

  it("covers expense form input branches and recurring planner form interactions", () => {
    const onChange = jest.fn();
    const onCreate = jest.fn();
    const onUpdate = jest.fn();
    const onDelete = jest.fn();

    const { container } = render(
      <>
        <ExpenseForm
          form={{ date: "2026-04-01", category: "Travel", description: "Bus", amount: "4.50", entry_type: "expense" }}
          selectedExpenseId={null}
          onChange={onChange}
          onCreate={jest.fn()}
          onUpdate={jest.fn()}
          onDelete={jest.fn()}
          onClear={jest.fn()}
        />
        <RecurringCalendarPanel
          items={[
            {
              id: 11,
              category: "Housing",
              description: "Long-term rent",
              amount: 452.74,
              entry_type: "expense",
              frequency: "monthly",
              start_date: "2026-04-23",
              end_date: "2026-06-23",
              active: true,
            },
            {
              id: 12,
              category: "Income",
              description: "Weekly pay",
              amount: 250,
              entry_type: "income",
              frequency: "weekly",
              start_date: "2026-04-05",
              end_date: "",
              active: true,
            },
            {
              id: 13,
              category: "Dormant",
              description: "Paused item",
              amount: 10,
              entry_type: "expense",
              frequency: "monthly",
              start_date: "2026-04-01",
              end_date: "",
              active: false,
            },
          ]}
          calendar={{
            window_start: "2026-03-31",
            window_end: "2026-05-04",
            occurrences: [
              {
                recurring_item_id: 11,
                date: "2026-04-23",
                category: "Housing",
                description: "Long-term rent",
                amount: 452.74,
                entry_type: "expense",
                frequency: "monthly",
                days_until_due: 23,
              },
              {
                recurring_item_id: 12,
                date: "2026-04-05",
                category: "Income",
                description: "Weekly pay",
                amount: 250,
                entry_type: "income",
                frequency: "weekly",
                days_until_due: 5,
              },
            ],
            completed_occurrences: [],
          }}
          onCreate={onCreate}
          onUpdate={onUpdate}
          onDelete={onDelete}
          onMarkPaid={jest.fn()}
          onMarkUnpaid={jest.fn()}
        />
      </>,
    );

    fireEvent.change(screen.getByDisplayValue("2026-04-01"), { target: { value: "2026-04-02" } });
    fireEvent.change(screen.getByDisplayValue("Travel"), { target: { value: "Housing" } });
    fireEvent.change(screen.getByDisplayValue("Bus"), { target: { value: "Coach" } });
    fireEvent.change(screen.getByDisplayValue("4.50"), { target: { value: "5.50" } });

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ date: "2026-04-02", entry_type: "expense" }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ category: "Housing", entry_type: "expense" }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ description: "Coach", entry_type: "expense" }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ amount: "5.50", entry_type: "expense" }));

    fireEvent.click(screen.getByRole("button", { name: /Long-term rent/i }));
    fireEvent.change(screen.getByDisplayValue("Housing"), { target: { value: "Student housing" } });
    fireEvent.change(screen.getByDisplayValue("Long-term rent"), { target: { value: "Updated rent" } });
    fireEvent.change(screen.getByDisplayValue("452.74"), { target: { value: "460.00" } });
    fireEvent.change(screen.getByDisplayValue("2026-04-23"), { target: { value: "2026-04-24" } });
    fireEvent.change(screen.getByDisplayValue("2026-06-23"), { target: { value: "2026-07-24" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "income" } });
    fireEvent.change(screen.getAllByRole("combobox")[1], { target: { value: "weekly" } });

    fireEvent.click(screen.getByText("Update reminder"));
    expect(onUpdate).toHaveBeenCalledWith(
      11,
      expect.objectContaining({
        category: "Student housing",
        description: "Updated rent",
        amount: "460.00",
        start_date: "2026-04-24",
        end_date: "2026-07-24",
        frequency: "weekly",
        entry_type: "income",
        active: false,
      }),
    );

    fireEvent.click(screen.getByText("Delete reminder"));
    expect(onDelete).toHaveBeenCalledWith(11);

    fireEvent.click(screen.getByText("Clear"));
    fireEvent.click(screen.getByText("Add reminder"));
    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        category: "",
        description: "",
        amount: "",
        start_date: "",
        end_date: "",
        active: true,
      }),
    );

    const allReminderRows = Array.from(container.querySelectorAll(".month-breakdown-row")).map((node) => node.textContent ?? "");
    expect(allReminderRows.some((value) => value.includes("April 2026") && value.includes("Long-term rent"))).toBe(true);
    expect(allReminderRows.some((value) => value.includes("June 2026") && value.includes("Long-term rent"))).toBe(true);
    expect(allReminderRows.some((value) => value.includes("February 2027") && value.includes("Weekly pay"))).toBe(true);
    expect(screen.getAllByText((_, element) => !!element?.textContent && element.textContent.includes("250.00") && element.className.includes("amount-positive")).length).toBeGreaterThan(0);
  });

  it("covers KPI legends, donut segments, trend lines, and weekly percentages", () => {
    const currentMonth = new Date().toISOString().slice(0, 7);
    const expenses = [
      { id: 1, date: `${currentMonth}-02`, category: "Food", description: "Groceries", amount: 30, entry_type: "expense" as const },
      { id: 2, date: `${currentMonth}-10`, category: "Travel", description: "Tube", amount: 10, entry_type: "expense" as const },
      { id: 3, date: `${currentMonth}-18`, category: "Bills", description: "Energy", amount: 5, entry_type: "expense" as const },
      { id: 4, date: `${currentMonth}-25`, category: "Food", description: "Cafe", amount: 15, entry_type: "expense" as const },
      { id: 5, date: "2026-01-03", category: "Bills", description: "Rent", amount: 100, entry_type: "expense" as const },
      { id: 6, date: "2026-02-03", category: "Bills", description: "Rent", amount: 200, entry_type: "expense" as const },
      { id: 7, date: "2026-03-03", category: "Bills", description: "Rent", amount: 300, entry_type: "expense" as const },
    ];

    render(
      <KpiVisuals
        expenses={expenses}
        summary={{
          monthly_budget: 1000,
          current_month_total: 60,
          monthly_expenses: 60,
          monthly_income: 1500,
          net_cash_flow: 1440,
          remaining_budget: 940,
          weekly_spending: 15,
          percent_spent: 6,
          status: "within",
          month_label: "April 2026",
          month_key: currentMonth,
          income_month: currentMonth,
        }}
      />,
    );

    expect(screen.getByText("Food")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.tagName === "P" && !!element.textContent && element.textContent.includes("45.00") && element.textContent.includes("75.0%"))).toBeInTheDocument();
    expect(screen.getByLabelText("Category mix donut chart")).toBeInTheDocument();
    expect(screen.getByLabelText("Monthly spending trend chart")).toBeInTheDocument();
    expect(screen.getByText("Jan")).toBeInTheDocument();
    expect(screen.getByText("Feb")).toBeInTheDocument();
    expect(screen.getByText("Mar")).toBeInTheDocument();
    expect(screen.getByText("Week 4+")).toBeInTheDocument();
  });
});





