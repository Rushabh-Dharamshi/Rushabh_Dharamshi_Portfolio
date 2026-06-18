import { fireEvent, render, screen } from "@testing-library/react";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { AutomationCenter } from "@/components/automation-center";
import { BudgetTrackerShell } from "@/components/budget-tracker-shell";
import { EmailAutomationPanel } from "@/components/email-automation-panel";
import { LatencyMonitor } from "@/components/latency-monitor";
import { PiggyBankPanel } from "@/components/piggy-bank-panel";
import { RagQaPanel } from "@/components/rag-qa-panel";
import { SavingsGoalsPanel } from "@/components/savings-goals-panel";
import { apiClient } from "@/lib/api-client";

const mockUseBudgetTracker = jest.fn();

jest.mock("@/hooks/use-budget-tracker", () => ({
  useBudgetTracker: () => mockUseBudgetTracker(),
}));

jest.mock("@/components/automation-center", () => ({
  AutomationCenter: jest.requireActual("@/components/automation-center").AutomationCenter,
}));
jest.mock("@/components/dashboard-summary", () => ({ DashboardSummaryCards: () => <div>Summary cards mock</div> }));
jest.mock("@/components/expense-form", () => ({ ExpenseForm: () => <div>Expense form mock</div> }));
jest.mock("@/components/operations-panel", () => ({ OperationsPanel: () => <div>Operations panel mock</div> }));
jest.mock("@/components/recurring-calendar-panel", () => ({ RecurringCalendarPanel: () => <div>Recurring panel mock</div> }));
jest.mock("@/components/rag-qa-panel", () => ({ RagQaPanel: jest.requireActual("@/components/rag-qa-panel").RagQaPanel }));
jest.mock("@/components/kpi-visuals", () => ({ KpiVisuals: () => <div>KPI visuals mock</div> }));
jest.mock("@/components/financial-pulse", () => ({ FinancialPulse: () => <div>Pulse mock</div> }));
jest.mock("@/components/expense-table", () => ({ ExpenseTable: () => <div>Expense table mock</div> }));
jest.mock("@/components/spending-comparison-panel", () => ({ SpendingComparisonPanel: () => <div>Comparison mock</div> }));
jest.mock("@/components/insights-panel", () => ({ InsightsPanel: () => <div>Insights mock</div> }));
jest.mock("@/components/ai-agent-panel", () => ({
  AiAgentPanel: jest.requireActual("@/components/ai-agent-panel").AiAgentPanel,
}));

const baseTracker = {
  allExpenses: [],
  expenses: [],
  selectedExpense: null,
  form: { date: "", category: "", description: "", amount: "", entry_type: "expense" as const },
  dashboard: {
    monthly_budget: 1050,
    current_month_total: 420,
    monthly_expenses: 420,
    monthly_income: 1500,
    net_cash_flow: 1080,
    remaining_budget: 630,
    weekly_spending: 84.5,
    percent_spent: 40,
    status: "within" as const,
    month_label: "March 2026",
    month_key: "2026-03",
    income_month: "2026-03",
  },
  categoryInsights: null,
  wordCloud: null,
  financialPulse: null,
  recurringItems: [],
  recurringCalendar: null,
  prediction: null,
  latencyReport: null,
  ragQuestionDraft: "",
  ragAnswer: null,
  ragStatus: null,
  agentTaskDraft: "",
  agentBriefing: null,
  agentWorkflows: [],
  agentRuns: [],
  isAgentRunning: false,
  isRagQueryRunning: false,
  isRagReindexing: false,
  isBootstrappingAutomation: false,
  activeWorkflowName: null,
  activeEmailDispatchId: null,
  searchId: "",
  budgetDraft: "1050.00",
  incomeDraft: "1500.00",
  incomeMonthDraft: "2026-03",
  statusMessage: null,
  errorMessage: null,
  isLoading: false,
  exportUrl: "/export",
  reportUrl: "/report",
  monthlyIncomeRecords: [],
  savingsGoals: [],
  setForm: jest.fn(),
  setSearchId: jest.fn(),
  setBudgetDraft: jest.fn(),
  setIncomeDraft: jest.fn(),
  setIncomeMonthDraft: jest.fn(),
  setRagQuestionDraft: jest.fn(),
  setAgentTaskDraft: jest.fn(),
  selectExpense: jest.fn(),
  resetForm: jest.fn(),
  createExpense: jest.fn(),
  updateExpense: jest.fn(),
  deleteExpense: jest.fn(),
  searchExpenseById: jest.fn(),
  showAllRecords: jest.fn(),
  importExpenses: jest.fn(),
  predictNextMonth: jest.fn(),
  checkBudgetStatus: jest.fn(),
  saveMonthlyBudget: jest.fn(),
  saveMonthlyIncome: jest.fn(),
  createRecurringItem: jest.fn(),
  updateRecurringItem: jest.fn(),
  deleteRecurringItem: jest.fn(),
  markRecurringOccurrencePaid: jest.fn(),
  markRecurringOccurrenceUnpaid: jest.fn(),
  runRagQuery: jest.fn(),
  reindexRagKnowledge: jest.fn(),
  runFinanceBriefingAgent: jest.fn(),
  runAutomationWorkflow: jest.fn(),
  sendUpcomingBillsEmailNow: jest.fn(),
  sendAllUpcomingBillsEmailNow: jest.fn(),
  sendMonthEndEmailNow: jest.fn(),
  refresh: jest.fn(),
  refreshLatencyReport: jest.fn(),
  createSavingsGoal: jest.fn(),
  updateSavingsGoal: jest.fn(),
  deleteSavingsGoal: jest.fn(),
};

describe("last-mile frontend coverage", () => {
  beforeEach(() => {
    mockUseBudgetTracker.mockReset();
    mockUseBudgetTracker.mockReturnValue(baseTracker);
    jest.clearAllMocks();
  });

  it("hits duplicate agent error guard after a prop change", () => {
    const { rerender } = render(
      <AiAgentPanel
        taskDraft="Send report"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={null}
        errorMessage="Request failed"
      />,
    );

    rerender(
      <AiAgentPanel
        taskDraft="Send report please"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={null}
        errorMessage="Request failed"
      />,
    );

    expect(screen.getAllByText("Request failed.")).toHaveLength(1);
  });

  it("suppresses duplicate agent errors and uses the default command label", () => {
    const { rerender } = render(
      <AiAgentPanel
        taskDraft=""
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={null}
        errorMessage="Request failed"
      />,
    );

    rerender(
      <AiAgentPanel
        taskDraft=""
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        result={null}
        errorMessage="Request failed"
      />,
    );

    expect(screen.getByText("Run agent command.")).toBeInTheDocument();
    expect(screen.getAllByText("Request failed.")).toHaveLength(1);
  });

  it("renders an agent email draft without an email subject", () => {
    render(
      <AiAgentPanel
        taskDraft="Send report"
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
        errorMessage={null}
        result={{
          headline: "Email sent",
          summary: "Done",
          risk_level: "low",
          recommended_actions: [],
          email_subject: "",
          email_draft: "Body only",
          task: "Send report",
          model: "qwen",
          tools_used: [],
          report_download_url: null,
          generated_at: "2026-06-18T10:00:00Z",
          action_result: { type: "month_end_email_sent", message: "" },
        }}
      />,
    );

    expect(screen.getByText("Email-ready summary")).toBeInTheDocument();
    expect(screen.getByText("Body only.")).toBeInTheDocument();
  });

  it("renders and triggers the shell delete-account action", () => {
    const onDeleteAccount = jest.fn();

    render(<BudgetTrackerShell username="Owner" onDeleteAccount={onDeleteAccount} />);

    fireEvent.click(screen.getByRole("button", { name: "Delete account" }));

    expect(onDeleteAccount).toHaveBeenCalled();
  });

  it("renders the shell action-lock message with fallback operation label", () => {
    mockUseBudgetTracker.mockReturnValue({
      ...baseTracker,
      isOperationLocked: true,
      activeOperationLabel: null,
    });

    render(<BudgetTrackerShell username="Owner" />);

    expect(screen.getByText("Action lock active.")).toBeInTheDocument();
    expect(screen.getByText(/A finance operation is running/i)).toBeInTheDocument();
  });

  it("renders the shell action-lock message with a named operation label", () => {
    mockUseBudgetTracker.mockReturnValue({
      ...baseTracker,
      isOperationLocked: true,
      activeOperationLabel: "Save monthly budget",
    });

    render(<BudgetTrackerShell username="Owner" />);

    expect(screen.getByText(/Save monthly budget is running/i)).toBeInTheDocument();
  });

  it("renders the piggy-bank defaults when no summary is loaded", () => {
    render(<PiggyBankPanel summary={null} />);

    expect(screen.getByText(/Current month increases the piggy bank by/i)).toBeInTheDocument();
    expect(screen.getByText("Total piggy-bank balance").closest("div")).toHaveTextContent(/£0\.00/);
  });

  it("renders negative piggy-bank cash flow and previous carryover branches", () => {
    render(
      <PiggyBankPanel
        summary={{
          monthly_budget: 600,
          current_month_total: 900,
          monthly_expenses: 900,
          monthly_income: 700,
          net_cash_flow: -200,
          remaining_budget: -300,
          weekly_spending: 100,
          percent_spent: 150,
          status: "over",
          month_label: "June 2026",
          month_key: "2026-06",
          income_month: "2026-06",
        }}
        expenses={[
          { id: 1, date: "2026-05-10", category: "Food", description: "May spend", amount: 100, entry_type: "expense" },
          { id: 4, date: "2026-04-10", category: "Food", description: "Missing amount", amount: undefined as unknown as number, entry_type: "expense" },
          { id: 2, date: "", category: "Food", description: "Ignored", amount: 50, entry_type: "expense" },
          { id: 3, date: "2026-06-01", category: "Food", description: "Current", amount: 20, entry_type: "expense" },
        ]}
        monthlyIncomeRecords={[
          { month_key: "2026-05", monthly_income: 500 },
          { month_key: "", monthly_income: 1000 },
          { month_key: "2026-06", monthly_income: 2000 },
        ]}
      />,
    );

    expect(screen.getByText(/cash flow is negative/i)).toBeInTheDocument();
    expect(screen.getByText("Previous carryover").closest("article")).toHaveTextContent("£400.00");
  });

  it("sorts automation runs by sql timestamp and falls back to id when timestamps are invalid", () => {
    const baseRun = {
      workflow_name: "month_end_close",
      workflow_label: "Month-end close",
      status: "completed",
      headline: "Ignored",
      summary: "Ignored",
      risk_level: "low",
      recommended_actions: [],
      automated_actions: [],
      email_subject: "",
      email_draft: "",
      task: "Run",
      model: "qwen",
      tools_used: [],
      report_download_url: null,
    };
    const { rerender } = render(
      <AutomationCenter
        workflows={[]}
        runs={[
          { ...baseRun, id: 1, headline: "Older SQL", generated_at: "2026-06-17 10:00:00" },
          { ...baseRun, id: 2, headline: "Newest SQL", generated_at: "2026-06-17 10:00:01" },
        ]}
        activeWorkflowName={null}
        liveStatusMessage={null}
        onRunWorkflow={jest.fn()}
      />,
    );
    expect(screen.getByText("Newest SQL")).toBeInTheDocument();

    rerender(
      <AutomationCenter
        workflows={[]}
        runs={[
          { ...baseRun, id: 3, headline: "Lower id", generated_at: "bad" },
          { ...baseRun, id: 9, headline: "Higher id", generated_at: "also bad" },
        ]}
        activeWorkflowName={null}
        liveStatusMessage={null}
        onRunWorkflow={jest.fn()}
      />,
    );
    expect(screen.getByText("Higher id")).toBeInTheDocument();
  });

  it("renders active automation workflow, late reminders, fallback output, and report link", () => {
    const onRunWorkflow = jest.fn();
    render(
      <AutomationCenter
        workflows={[
          { id: "unknown_flow", label: "Unknown flow", description: "Fallback workflow description", automation_focus: "focus", default_task: "run" },
          { id: "month_end_close", label: "Month-end close", description: "Month end", automation_focus: "focus", default_task: "run" },
        ]}
        runs={[
          {
            id: 12,
            workflow_name: "unknown_flow",
            workflow_label: "Unknown flow",
            status: "completed",
            headline: "Unknown flow",
            summary: "",
            risk_level: "medium",
            recommended_actions: ["Review output"],
            automated_actions: [],
            email_subject: "",
            email_draft: "",
            task: "run",
            model: "qwen",
            tools_used: ["tool_a", "tool_b"],
            report_download_url: "/api/reports/monthly",
            generated_at: "18/06/2026, 10:30",
          },
        ]}
        recurringCalendar={{
          window_start: "2026-06-01",
          window_end: "2026-06-30",
          occurrences: [],
          completed_occurrences: [],
          late_occurrences: [
            { recurring_item_id: 3, date: "2026-06-10", category: "Bills", description: "A late bill", amount: 10, entry_type: "expense", frequency: "monthly", days_until_due: -8 },
            { recurring_item_id: 1, date: "2026-06-10", category: "Bills", description: "Late bill", amount: 12.5, entry_type: "expense", frequency: "monthly", days_until_due: -8 },
            { recurring_item_id: 2, date: "2026-06-11", category: "Income", description: "Late income", amount: 12.5, entry_type: "income", frequency: "monthly", days_until_due: -7 },
          ],
        }}
        activeWorkflowName="month_end_close"
        liveStatusMessage={null}
        onRunWorkflow={onRunWorkflow}
      />,
    );

    expect(screen.getByText("Late bill: £12.50 due 2026-06-10")).toBeInTheDocument();
    expect(screen.getByText(/A late bill:/)).toBeInTheDocument();
    expect(screen.queryByText(/Late income/)).not.toBeInTheDocument();
    expect(screen.getByText(/The workflow is gathering finance context/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open report" })).toHaveAttribute("href", "/api/reports/monthly");
    fireEvent.click(screen.getByRole("button", { name: /Unknown flow/i }));
    expect(onRunWorkflow).not.toHaveBeenCalled();
  });

  it("runs a ready automation workflow and renders fallback action text", () => {
    const onRunWorkflow = jest.fn();
    render(
      <AutomationCenter
        workflows={[
          { id: "custom_flow", label: "Custom flow", description: "Custom description", automation_focus: "focus", default_task: "run" },
        ]}
        runs={[
          {
            id: 3,
            workflow_name: "custom_flow",
            workflow_label: "Custom flow",
            status: "completed",
            headline: "Custom headline",
            summary: "Custom summary",
            risk_level: "low",
            recommended_actions: [],
            automated_actions: [],
            email_subject: "",
            email_draft: "",
            task: "run",
            model: "qwen",
            tools_used: [],
            report_download_url: null,
            generated_at: "2026-06-18T10:30:00Z",
          },
        ]}
        activeWorkflowName={null}
        liveStatusMessage={null}
        onRunWorkflow={onRunWorkflow}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Custom flow/i }));

    expect(onRunWorkflow).toHaveBeenCalledWith("custom_flow");
    expect(screen.getByText("Saved workflow response with recommendations.")).toBeInTheDocument();
  });

  it("renders structured automation output recommendations and email draft without a subject", () => {
    render(
      <AutomationCenter
        workflows={[{ id: "month_end_close", label: "Month-end close", description: "Month end", automation_focus: "focus", default_task: "run" }]}
        runs={[
          {
            id: 20,
            workflow_name: "month_end_close",
            workflow_label: "Month-end close",
            status: "completed",
            headline: "Fallback headline",
            summary: JSON.stringify({
              headline: "Structured close",
              cash_flow: "Cash flow is positive.",
              recommended_actions: ["Review report"],
              email_draft: "Monthly close is ready.",
            }),
            risk_level: "high",
            recommended_actions: [],
            automated_actions: [],
            email_subject: "",
            email_draft: "",
            task: "run",
            model: "qwen",
            tools_used: [],
            report_download_url: null,
            generated_at: "2026-06-18T10:30:00Z",
          },
        ]}
        activeWorkflowName={null}
        liveStatusMessage={null}
        onRunWorkflow={jest.fn()}
      />,
    );

    expect(screen.getByText("Structured close")).toBeInTheDocument();
    expect(screen.getByText("Review report.")).toBeInTheDocument();
    expect(screen.getByText("Monthly close is ready.")).toBeInTheDocument();
    expect(screen.getAllByText("completed")[0]).toHaveClass("status-over");
  });

  it("renders automation output with no recommended actions", () => {
    render(
      <AutomationCenter
        workflows={[{ id: "month_end_close", label: "Month-end close", description: "Month end", automation_focus: "focus", default_task: "run" }]}
        runs={[
          {
            id: 21,
            workflow_name: "month_end_close",
            workflow_label: "Month-end close",
            status: "completed",
            headline: "No actions",
            summary: "Only summary",
            risk_level: "low",
            recommended_actions: [],
            automated_actions: [],
            email_subject: "",
            email_draft: "",
            task: "run",
            model: "qwen",
            tools_used: [],
            report_download_url: null,
            generated_at: "2026-06-18T10:30:00Z",
          },
        ]}
        activeWorkflowName={null}
        liveStatusMessage={null}
        onRunWorkflow={jest.fn()}
      />,
    );

    expect(screen.queryByText("Recommended actions")).not.toBeInTheDocument();
  });

  it("covers remaining latency endpoint descriptions", () => {
    render(
      <LatencyMonitor
        report={{
          scope: "current_user",
          record_count: 4,
          failed_count: 0,
          summary: { average_ms: 1, minimum_ms: 1, maximum_ms: 1, p95_ms: 1 },
          latest_failures: [],
          by_endpoint: [
            { method: "GET", path: "/api/expenses/12", request_count: 1, failed_count: 0, average_ms: 1, maximum_ms: 1 },
            { method: "GET", path: "/api/settings/income-records", request_count: 1, failed_count: 0, average_ms: 1, maximum_ms: 1 },
            { method: "GET", path: "/api/auth/session", request_count: 1, failed_count: 0, average_ms: 1, maximum_ms: 1 },
          ],
          latest: [
            { request_id: "settings", timestamp: "2026-06-17T16:58:30Z", method: "GET", path: "/api/settings/income-records", status_code: 200, duration_ms: 1, user_id: 1, username: "Owner", ok: true },
          ],
        }}
        onRefresh={jest.fn()}
      />,
    );

    expect(screen.getByText(/Reads or changes transaction records/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Reads or saves monthly budget and monthly income settings/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Handles sign in, sign out, registration/i)).toBeInTheDocument();
  });

  it("renders multiple email recommended actions", () => {
    render(
      <EmailAutomationPanel
        runs={[
          {
            id: 1,
            workflow_name: "month_end_email",
            workflow_label: "Month-end email",
            status: "completed",
            headline: "Month-end sent",
            summary: "Delivered.",
            risk_level: "low",
            recommended_actions: ["Review the PDF.", "Archive the report."],
            automated_actions: [],
            email_subject: "Month end",
            email_draft: "Report sent.",
            task: "send",
            model: "qwen",
            tools_used: [],
            report_download_url: null,
            generated_at: "2026-04-03T12:00:00Z",
          },
        ]}
        activeDispatchId={null}
        onSendUpcomingBillsEmail={jest.fn()}
        onSendAllUpcomingBillsEmail={jest.fn()}
        onSendMonthEndEmail={jest.fn()}
      />,
    );

    expect(screen.getByText("Review the PDF.")).toBeInTheDocument();
    expect(screen.getByText("Archive the report.")).toBeInTheDocument();
  });

  it("renders fallback email run summary and disabled all-upcoming handler", () => {
    render(
      <EmailAutomationPanel
        runs={[
          {
            id: 2,
            workflow_name: "month_end_email",
            workflow_label: "Month-end email",
            status: "completed",
            headline: "Month-end email",
            summary: "Raw summary only",
            risk_level: "high",
            recommended_actions: [],
            automated_actions: [],
            email_subject: "",
            email_draft: "",
            task: "send",
            model: "qwen",
            tools_used: [],
            report_download_url: "/api/reports/monthly",
            generated_at: "2026-04-03T12:00:00Z",
          },
        ]}
        activeDispatchId={null}
        onSendUpcomingBillsEmail={jest.fn()}
        onSendAllUpcomingBillsEmail={undefined}
        onSendMonthEndEmail={jest.fn()}
      />,
    );

    expect(screen.getByText("Raw summary only.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send all upcoming bills" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "Download report" })).toHaveAttribute("href", "/api/reports/monthly");
    expect(screen.getByText(/high/)).toHaveClass("status-over");
  });

  it("renders active all-upcoming email dispatch state", () => {
    render(
      <EmailAutomationPanel
        runs={[]}
        activeDispatchId="all_upcoming_bills_email"
        onSendUpcomingBillsEmail={jest.fn()}
        onSendAllUpcomingBillsEmail={jest.fn()}
        onSendMonthEndEmail={jest.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Sending all upcoming bills..." })).toBeDisabled();
  });

  it("exercises savings goal disabled branches", () => {
    const onUpdate = jest.fn();
    const onDelete = jest.fn();

    render(<SavingsGoalsPanel goals={undefined} onCreate={jest.fn()} onUpdate={onUpdate} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole("button", { name: "Update goal" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete goal" }));

    expect(onUpdate).not.toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByText("No savings goals created yet.")).toBeInTheDocument();
  });

  it("updates the savings target date input and submits a create payload", () => {
    const onCreate = jest.fn();

    render(<SavingsGoalsPanel goals={[]} onCreate={onCreate} onUpdate={jest.fn()} onDelete={jest.fn()} />);

    fireEvent.change(screen.getByLabelText("Target date"), { target: { value: "2026-12-24" } });
    fireEvent.click(screen.getByRole("button", { name: "Add goal" }));

    expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({ target_date: "2026-12-24" }));
  });

  it("exercises savings goal select, update, delete, and clamped progress branches", () => {
    const onUpdate = jest.fn();
    const onDelete = jest.fn();

    render(
      <SavingsGoalsPanel
        goals={[
          {
            id: 3,
            name: "Emergency fund",
            target_amount: 100,
            current_amount: 150,
            target_date: null,
            progress_percent: 140,
            remaining_amount: 0,
            created_at: "2026-06-01T00:00:00Z",
          },
          {
            id: 4,
            name: "Deposit",
            target_amount: 500,
            current_amount: 10,
            target_date: "2026-12-31",
            progress_percent: -10,
            remaining_amount: 490,
            created_at: "2026-06-01T00:00:00Z",
          },
        ]}
        onCreate={jest.fn()}
        onUpdate={onUpdate}
        onDelete={onDelete}
      />,
    );

    fireEvent.click(screen.getByText("Emergency fund"));
    fireEvent.click(screen.getByRole("button", { name: "Update goal" }));
    expect(onUpdate).toHaveBeenCalledWith(3, expect.objectContaining({ name: "Emergency fund" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete goal" }));
    expect(onDelete).toHaveBeenCalledWith(3);
    expect(screen.getByText("No target date")).toBeInTheDocument();
    expect(screen.getByText("Target 2026-12-31")).toBeInTheDocument();
  });

  it("renders RAG blank answer paragraphs without showing empty text", () => {
    render(
      <RagQaPanel
        questionDraft="Question"
        answer={{
          question: "Question",
          answer: "\n\nUseful answer\n\n",
          confidence: "medium",
          follow_up_questions: [],
          sources: [],
          generated_at: "2026-04-15T09:10:00Z",
        }}
        status={null}
        isQuerying={false}
        isReindexing={false}
        onQuestionDraftChange={jest.fn()}
        onAsk={jest.fn()}
        onReindex={jest.fn()}
      />,
    );

    expect(screen.getByText("Useful answer.")).toBeInTheDocument();
  });

  it("uses the RAG draft when answer question is blank", () => {
    render(
      <RagQaPanel
        questionDraft="What is my cash flow?"
        answer={{
          question: "",
          answer: "Cash flow is positive.",
          confidence: "high",
          follow_up_questions: [],
          sources: [],
          generated_at: "bad-date",
        }}
        status={null}
        isQuerying={false}
        isReindexing={false}
        onQuestionDraftChange={jest.fn()}
        onAsk={jest.fn()}
        onReindex={jest.fn()}
      />,
    );

    expect(screen.getAllByText("What is my cash flow?").length).toBeGreaterThan(1);
  });

  it("covers non-Error network failures and month-specific budget bodies", async () => {
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
    global.fetch = jest
      .fn()
      .mockRejectedValueOnce("offline")
      .mockResolvedValueOnce({
        ok: true,
        headers: { get: () => "application/json" },
        json: async () => ({ data: { monthly_budget: 700, budget_month: "2026-05" } }),
      });

    await expect(apiClient.getDashboard()).rejects.toBe("offline");
    await apiClient.updateMonthlyBudget(700, "2026-05");

    expect((global.fetch as jest.Mock).mock.calls[1][1].body).toBe(JSON.stringify({ monthly_budget: 700, month: "2026-05" }));
    errorSpy.mockRestore();
  });
});
