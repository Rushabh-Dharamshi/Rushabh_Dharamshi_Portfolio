import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { AuthenticatedApp } from "@/components/authenticated-app";
import { EmailAutomationPanel } from "@/components/email-automation-panel";
import { InsightsPanel } from "@/components/insights-panel";
import { KpiVisuals } from "@/components/kpi-visuals";
import { OperationsPanel } from "@/components/operations-panel";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";
import { SpendingComparisonPanel } from "@/components/spending-comparison-panel";
import { apiClient } from "@/lib/api-client";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    getAuthSession: jest.fn(),
    login: jest.fn(),
    logout: jest.fn(),
  },
}));

jest.mock("@/components/budget-tracker-shell", () => ({
  BudgetTrackerShell: ({ username, onLogout }: { username: string; onLogout?: () => void }) => (
    <div>
      <span>Shell for {username}</span>
      <button type="button" onClick={() => onLogout?.()}>
        Trigger logout
      </button>
    </div>
  ),
}));

describe("final component coverage branches", () => {
  afterEach(() => {
    jest.useRealTimers();
    jest.resetAllMocks();
  });

  it("falls back to the default username for authenticated sessions", async () => {
    (apiClient.getAuthSession as jest.Mock).mockResolvedValue({ authenticated: true, username: null });

    render(<AuthenticatedApp />);

    await waitFor(() => {
      expect(screen.getByText("Shell for Rushabh")).toBeInTheDocument();
    });
  });

  it("covers remaining AI agent normalization branches", () => {
    const { rerender } = render(
      <AiAgentPanel
        taskDraft="review"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={{
          headline: "summary",
          summary: "   ",
          risk_level: "low",
          recommended_actions: ["call landlord"],
          email_subject: "subject",
          email_draft: "\n\n",
          task: "review",
          model: "qwen",
          tools_used: [],
          report_download_url: null,
          generated_at: "2026-04-03T20:00:00Z",
        }}
      />,
    );

    expect(screen.getByText("Call landlord.")).toBeInTheDocument();
    expect(screen.getByText(/low risk/i)).toHaveClass("status-pill", "status-within");

    rerender(
      <AiAgentPanel
        taskDraft="review"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={{
          headline: "summary",
          summary: "done",
          risk_level: "low",
          recommended_actions: "   " as unknown as string[],
          email_subject: "subject",
          email_draft: "done",
          task: "review",
          model: "qwen",
          tools_used: [],
          report_download_url: null,
          generated_at: "2026-04-03T20:00:00Z",
        }}
      />,
    );

    expect(screen.getByText("The agent did not propose any actions.")).toBeInTheDocument();

    rerender(
      <AiAgentPanel
        taskDraft="review"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={{
          headline: "summary",
          summary: "done",
          risk_level: "low",
          recommended_actions: [" ", " "],
          email_subject: "subject",
          email_draft: "done",
          task: "review",
          model: "qwen",
          tools_used: [],
          report_download_url: null,
          generated_at: "2026-04-03T20:00:00Z",
        }}
      />,
    );

    expect(screen.getByText("The agent did not propose any actions.")).toBeInTheDocument();
  });

  it("fills the agent task draft from a known-safe prompt", () => {
    const onTaskDraftChange = jest.fn();

    render(
      <AiAgentPanel
        taskDraft=""
        isRunning={false}
        onTaskDraftChange={onTaskDraftChange}
        onRun={jest.fn()}
        result={null}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Set my monthly budget to 1600 pounds/i }));

    expect(onTaskDraftChange).toHaveBeenCalledWith("Set my monthly budget to 1600 pounds.");
  });

  it("deduplicates repeated AI errors and renders fallback summary values", () => {
    const { rerender, unmount } = render(
      <AiAgentPanel
        taskDraft="Send the month-end email now."
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={null}
        errorMessage="Request failed."
      />,
    );

    expect(screen.getAllByText("Request failed.")).toHaveLength(1);

    rerender(
      <AiAgentPanel
        taskDraft="Send the month-end email now."
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={null}
        errorMessage="Request failed."
      />,
    );
    expect(screen.getAllByText("Request failed.")).toHaveLength(1);

    unmount();

    render(
      <AiAgentPanel
        taskDraft="Review"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={{
          headline: "fallback",
          summary: 0 as unknown as string,
          risk_level: "high",
          recommended_actions: [],
          email_subject: "",
          email_draft: "",
          task: "Review",
          model: "qwen",
          tools_used: [],
          report_download_url: null,
          generated_at: "2026-04-03T20:00:00Z",
        }}
      />,
    );

    expect(screen.getByText(/high risk/i)).toHaveClass("status-pill", "status-over");
  });

  it("covers low-risk email runs and richer insight rendering", () => {
    render(
      <>
        <EmailAutomationPanel
          runs={[
            {
              id: 1,
              workflow_name: "month_end_email",
              workflow_label: "Month-end email",
              status: "completed",
              headline: "Month-end email",
              summary: "Sent.",
              risk_level: "low",
              recommended_actions: [],
              automated_actions: [],
              email_subject: "Subject",
              email_draft: "Draft",
              task: "run",
              model: "qwen",
              tools_used: [],
              report_download_url: "/api/reports/monthly",
              generated_at: "2026-04-03T20:00:00Z",
            },
          ]}
          activeDispatchId={null}
          onSendUpcomingBillsEmail={jest.fn()}
          onSendMonthEndEmail={jest.fn()}
        />
        <InsightsPanel
          categories={{
            top_categories: [{ category: "Food", amount: 220 }],
            bottom_categories: [{ category: "Travel", amount: 30 }],
            total_spending: 250,
          }}
          wordCloud={{
            top_category: "Food",
            top_category_total: 250,
            dominant_label: "Groceries",
            dominant_value: 180,
            frequencies: [
              { label: "Groceries", value: 180 },
              { label: "Cafe", value: 70, share: 28 },
            ],
          }}
        />
      </>,
    );

    expect(screen.getByText(/low risk/i)).toHaveClass("status-pill", "status-within");
    expect(screen.getAllByText("Groceries").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Description word cloud for Food")).toBeInTheDocument();
    expect(screen.getByText("28.0% of Food")).toBeInTheDocument();
    expect(screen.getByText("Download report")).toBeInTheDocument();
  });

  it("covers populated KPI visuals, file import, recurring schedule iteration, and comparison controls", () => {
    jest.useFakeTimers().setSystemTime(new Date("2026-04-18T12:00:00Z"));
    const onImport = jest.fn();
    const comparisonExpenses = [
      { id: 1, date: "2026-04-02", category: "Food", description: "Groceries", amount: 80, entry_type: "expense" as const },
      { id: 2, date: "2026-03-15", category: "Travel", description: "Train", amount: 45, entry_type: "expense" as const },
      { id: 3, date: "2026-02-10", category: "Travel", description: "Flight", amount: 60, entry_type: "expense" as const },
    ];

    render(
      <>
        <KpiVisuals
          expenses={comparisonExpenses}
          summary={{
            monthly_budget: 1000,
            current_month_total: 80,
            monthly_expenses: 80,
            monthly_income: 1500,
            net_cash_flow: 1420,
            remaining_budget: 920,
            weekly_spending: 20,
            percent_spent: 8,
            status: "within",
            month_label: "April 2026",
            month_key: "2026-04",
            income_month: "2026-04",
          }}
        />
        <OperationsPanel
          summary={null}
          prediction={null}
          exportUrl="/export"
          reportUrl="/report"
          budgetDraft="1000"
          incomeDraft="1500"
          incomeMonthDraft="2026-04"
          onImport={onImport}
          onPredict={jest.fn()}
          onCheckBudget={jest.fn()}
          onBudgetDraftChange={jest.fn()}
          onIncomeDraftChange={jest.fn()}
          onIncomeMonthChange={jest.fn()}
          onSaveBudget={jest.fn()}
          onSaveIncome={jest.fn()}
        />
        <RecurringCalendarPanel
          items={[
            { id: 1, category: "Bills", description: "Gym", amount: 30, entry_type: "expense", frequency: "weekly", start_date: "2026-04-01", end_date: null, active: true },
          ]}
          calendar={{
            window_start: "2026-04-15",
            window_end: "2026-05-20",
            occurrences: [],
            completed_occurrences: [],
          }}
          onCreate={jest.fn()}
          onUpdate={jest.fn()}
          onDelete={jest.fn()}
          onMarkPaid={jest.fn()}
          onMarkUnpaid={jest.fn()}
        />
        <SpendingComparisonPanel expenses={comparisonExpenses} referenceDate={new Date("2026-04-18T12:00:00Z")} />
      </>,
    );

    fireEvent.change(screen.getByLabelText(/Import CSV/i), { target: { files: [new File(["a,b"], "expenses.csv", { type: "text/csv" })] } });
    expect(onImport).toHaveBeenCalled();

    expect(screen.getAllByText("Week 1").length).toBeGreaterThan(0);
    expect(screen.getByText("Food")).toBeInTheDocument();
    expect(screen.getByText("scheduled", { exact: false })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Weekly" }));
    fireEvent.click(screen.getByRole("button", { name: "Monthly" }));
    fireEvent.click(screen.getByRole("button", { name: "Category" }));
    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "Travel" } });
    fireEvent.click(screen.getByRole("button", { name: "Overall" }));

    expect(screen.getByLabelText("Overlay spending comparison chart")).toBeInTheDocument();
  });
});







