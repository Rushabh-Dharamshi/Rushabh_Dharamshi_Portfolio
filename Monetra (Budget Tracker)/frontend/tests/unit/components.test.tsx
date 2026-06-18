import { fireEvent, render, screen } from "@testing-library/react";

import { AiAgentPanel } from "@/components/ai-agent-panel";
import { AutomationCenter } from "@/components/automation-center";
import { DashboardSummaryCards } from "@/components/dashboard-summary";
import { ExpenseForm } from "@/components/expense-form";
import { ExpenseTable } from "@/components/expense-table";
import { FinancialPulse } from "@/components/financial-pulse";
import { InsightsPanel } from "@/components/insights-panel";
import { KpiVisuals } from "@/components/kpi-visuals";
import { LatencyMonitor } from "@/components/latency-monitor";
import { OperationsPanel } from "@/components/operations-panel";
import { PiggyBankPanel } from "@/components/piggy-bank-panel";
import { RecurringCalendarPanel } from "@/components/recurring-calendar-panel";
import { SavingsGoalsPanel } from "@/components/savings-goals-panel";
import { SpendingComparisonPanel } from "@/components/spending-comparison-panel";

const dashboard = {
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
};

describe("presentational components", () => {
  it("renders latency failures separately with endpoint explanations", () => {
    render(
      <LatencyMonitor
        report={{
          scope: "current_user",
          record_count: 12,
          failed_count: 2,
          summary: { average_ms: 136.8, minimum_ms: 0.9, maximum_ms: 27410.4, p95_ms: 63.5 },
          by_endpoint: [
            {
              method: "GET",
              path: "/api/observability/latency",
              request_count: 924,
              failed_count: 0,
              average_ms: 254.4,
              maximum_ms: 25643.8,
            },
          ],
          latest_failures: [
            {
              request_id: "client-test-failure",
              timestamp: "2026-06-17T16:58:26Z",
              method: "CLIENT",
              path: "/api/client-operations/ai-agent-request",
              status_code: 599,
              duration_ms: 27410.4,
              user_id: 7,
              username: "Demo",
              ok: false,
            },
          ],
          latest: [
            {
              request_id: "ok-latency",
              timestamp: "2026-06-17T16:58:30Z",
              method: "GET",
              path: "/api/observability/latency",
              status_code: 200,
              duration_ms: 30.9,
              user_id: 7,
              username: "Demo",
              ok: true,
            },
          ],
        }}
        onRefresh={jest.fn()}
      />,
    );

    expect(screen.getByText("Recent failures")).toBeInTheDocument();
    expect(screen.getByText("Endpoint summary")).toBeInTheDocument();
    expect(screen.getByText("Latest requests")).toBeInTheDocument();
    expect(screen.getByText("CLIENT /api/client-operations/ai-agent-request")).toBeInTheDocument();
    expect(screen.getByText(/User-visible operation failure recorded by the app: ai agent request/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Refreshes this latency monitor/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Status 599 means the operation failed from the user's point of view/i)).toBeInTheDocument();
  });

  it("covers latency monitor empty, failure-window, and endpoint purpose branches", () => {
    const onRefresh = jest.fn();
    const { rerender } = render(<LatencyMonitor report={null} onRefresh={onRefresh} />);

    expect(screen.getByText("Use the app and recent API timings will appear here.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(onRefresh).toHaveBeenCalledTimes(1);

    rerender(
      <LatencyMonitor
        report={{
          scope: "current_user",
          record_count: 3,
          failed_count: 1,
          summary: { average_ms: 12, minimum_ms: 2, maximum_ms: 22, p95_ms: 20 },
          latest_failures: [],
          by_endpoint: [
            { method: "POST", path: "/api/agents/finance-briefing", request_count: 1, failed_count: 0, average_ms: 10, maximum_ms: 10 },
            { method: "GET", path: "/api/agents/finance-briefing/job-1", request_count: 1, failed_count: 0, average_ms: 3, maximum_ms: 3 },
            { method: "GET", path: "/api/agents/workflow-jobs/job-1", request_count: 1, failed_count: 1, average_ms: 22, maximum_ms: 22 },
            { method: "GET", path: "/api/rag/query", request_count: 1, failed_count: 0, average_ms: 4, maximum_ms: 4 },
            { method: "GET", path: "/api/dashboard", request_count: 1, failed_count: 0, average_ms: 5, maximum_ms: 5 },
            { method: "GET", path: "/api/analytics/category-insights", request_count: 1, failed_count: 0, average_ms: 6, maximum_ms: 6 },
            { method: "GET", path: "/api/expenses", request_count: 1, failed_count: 0, average_ms: 7, maximum_ms: 7 },
            { method: "GET", path: "/api/agents/workflows", request_count: 1, failed_count: 0, average_ms: 8, maximum_ms: 8 },
            { method: "GET", path: "/api/agents/runs", request_count: 1, failed_count: 0, average_ms: 9, maximum_ms: 9 },
          ],
          latest: [
            { request_id: "bad-request", timestamp: "2026-06-17T16:58:30Z", method: "POST", path: "/api/settings", status_code: 400, duration_ms: 8, user_id: 7, username: "Demo", ok: false },
            { request_id: "server-error", timestamp: "2026-06-17T16:58:31Z", method: "GET", path: "/api/reports/monthly", status_code: 500, duration_ms: 14, user_id: 7, username: "Demo", ok: false },
            { request_id: "auth-call", timestamp: "2026-06-17T16:58:32Z", method: "POST", path: "/api/auth/login", status_code: 401, duration_ms: 9, user_id: 7, username: "Demo", ok: false },
            { request_id: "recurring", timestamp: "2026-06-17T16:58:33Z", method: "GET", path: "/api/recurring-items", status_code: 200, duration_ms: 11, user_id: 7, username: "Demo", ok: true },
            { request_id: "report", timestamp: "2026-06-17T16:58:34Z", method: "GET", path: "/api/reports/monthly", status_code: 200, duration_ms: 12, user_id: 7, username: "Demo", ok: true },
            { request_id: "workflows", timestamp: "2026-06-17T16:58:35Z", method: "GET", path: "/api/agents/workflows", status_code: 200, duration_ms: 13, user_id: 7, username: "Demo", ok: true },
            { request_id: "runs", timestamp: "2026-06-17T16:58:36Z", method: "GET", path: "/api/agents/runs", status_code: 200, duration_ms: 14, user_id: 7, username: "Demo", ok: true },
            { request_id: "unknown", timestamp: "2026-06-17T16:58:34Z", method: "GET", path: "/api/unknown", status_code: 302, duration_ms: 12, user_id: 7, username: "Demo", ok: false },
          ],
        }}
        onRefresh={onRefresh}
      />,
    );

    expect(screen.getByText(/Failures exist in this user scope/i)).toBeInTheDocument();
    expect(screen.getByText(/Starts an Ollama operations-agent briefing/i)).toBeInTheDocument();
    expect(screen.getByText(/Polls an Ollama operations-agent job/i)).toBeInTheDocument();
    expect(screen.getByText(/Polls an Automation Center workflow job/i)).toBeInTheDocument();
    expect(screen.getByText(/Loads the Automation Center workflow definitions/i)).toBeInTheDocument();
    expect(screen.getByText(/Loads saved automation history/i)).toBeInTheDocument();
    expect(screen.getByText(/Runs or monitors the RAG assistant/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Generates or downloads the monthly PDF finance report/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Request was rejected or invalid/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Backend\/server-side failure/i)).toBeInTheDocument();
    expect(screen.getByText(/Backend API call used by the current Monetra screen/i)).toBeInTheDocument();
  });

  it("renders dashboard summary cards", () => {
    render(<DashboardSummaryCards summary={dashboard} />);

    expect(screen.getByText("March 2026")).toBeInTheDocument();
    expect(screen.getByText("Monthly income")).toBeInTheDocument();
    expect(screen.getByText("Net cash flow")).toBeInTheDocument();
  });

  it("renders the transaction form and forwards actions", () => {
    const onChange = jest.fn();
    const onCreate = jest.fn();
    const onUpdate = jest.fn();
    const onDelete = jest.fn();
    const onClear = jest.fn();

    render(
      <ExpenseForm
        form={{
          date: "2026-03-01",
          category: "Food",
          description: "Groceries",
          amount: "12.50",
          entry_type: "expense",
        }}
        selectedExpenseId={1}
        onChange={onChange}
        onCreate={onCreate}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onClear={onClear}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("Food"), { target: { value: "Travel" } });
    fireEvent.click(screen.getByText("Add expense"));
    fireEvent.click(screen.getByText("Update expense"));
    fireEvent.click(screen.getByText("Delete expense"));
    fireEvent.click(screen.getByText("Clear inputs"));

    expect(screen.getByDisplayValue("2026-03-01")).toHaveAttribute("max", new Date().toISOString().slice(0, 10));
    expect(onChange).toHaveBeenCalled();
    expect(onCreate).toHaveBeenCalled();
    expect(onUpdate).toHaveBeenCalled();
    expect(onDelete).toHaveBeenCalled();
    expect(onClear).toHaveBeenCalled();
  });

  it("renders the expense table and selection/search controls", () => {
    const onSearchIdChange = jest.fn();
    const onSearch = jest.fn();
    const onShowAll = jest.fn();
    const onSelect = jest.fn();
    const expenses: Array<{
      id: number;
      date: string;
      category: string;
      description: string;
      amount: number;
      entry_type: "expense" | "income";
    }> = Array.from({ length: 11 }, (_, index) => ({
      id: index + 1,
      date: "2026-03-01",
      category: "Food",
      description: index === 0 ? "Groceries" : `Groceries ${index + 1}`,
      amount: 20.5 + index,
      entry_type: "expense" as const,
    }));
    expenses.push({
      id: 12,
      date: "2026-03-09",
      category: "Income",
      description: "Part-time work",
      amount: 125,
      entry_type: "income" as const,
    });

    render(
      <ExpenseTable
        expenses={expenses}
        selectedExpenseId={1}
        searchId="1"
        onSearchIdChange={onSearchIdChange}
        onSearch={onSearch}
        onShowAll={onShowAll}
        onSelect={onSelect}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("1"), { target: { value: "2" } });
    fireEvent.click(screen.getByText("Search"));
    fireEvent.click(screen.getByText("Show all"));
    fireEvent.click(screen.getByText("Groceries"));
    fireEvent.change(screen.getByPlaceholderText("Filter description or category"), { target: { value: "part-time" } });
    expect(screen.getByText("1 visible")).toBeInTheDocument();
    expect(screen.getByText("Part-time work")).toBeInTheDocument();
    expect(screen.getByText("+£125.00")).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("part-time"), { target: { value: "" } });
    fireEvent.change(screen.getByDisplayValue("All categories"), { target: { value: "Food" } });
    fireEvent.change(screen.getByLabelText("Filter start date"), { target: { value: "2026-03-02" } });
    fireEvent.change(screen.getByLabelText("Filter end date"), { target: { value: "2026-03-08" } });
    expect(screen.getByText("No expense records found.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Clear filters"));
    expect(screen.getByText("12 visible")).toBeInTheDocument();

    expect(onSearchIdChange).toHaveBeenCalled();
    expect(onSearch).toHaveBeenCalled();
    expect(onShowAll).toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalled();
    expect(screen.getByText("Visible outflow")).toBeInTheDocument();
    expect(screen.getByText("Categories")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("Groceries").closest(".expense-table-wrapper")).toHaveClass("expense-table-wrapper");
  });

  it("renders insights and word cloud data", () => {
    render(
      <InsightsPanel
        categories={{
          top_categories: [{ category: "Food", amount: 220 }],
          bottom_categories: [{ category: "Travel", amount: 80 }],
          total_spending: 300,
        }}
        wordCloud={{
          top_category: "Food",
          top_category_total: 220,
          frequencies: [{ label: "Groceries", value: 220 }],
        }}
      />,
    );

    expect(screen.getByText("Top categories")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Category total: £220.00");
    expect(document.body.textContent).toContain("Descriptions surfaced: 1");
  });

  it("renders operations, budget, and prediction controls", () => {
    const onImport = jest.fn();
    const onPredict = jest.fn();
    const onCheckBudget = jest.fn();
    const onBudgetDraftChange = jest.fn();
    const onIncomeDraftChange = jest.fn();
    const onIncomeMonthChange = jest.fn();
    const onSaveBudget = jest.fn();
    const onSaveIncome = jest.fn();

    render(
      <OperationsPanel
        summary={dashboard}
        prediction={{
          next_month: "April 2026",
          predicted_spending: 880,
          is_budget_exceeded: false,
          monthly_budget: 1050,
        }}
        exportUrl="/export"
        reportUrl="/report"
        budgetDraft="1050.00"
        incomeDraft="1500.00"
        incomeMonthDraft="2026-03"
        onImport={onImport}
        onPredict={onPredict}
        onCheckBudget={onCheckBudget}
        onBudgetDraftChange={onBudgetDraftChange}
        onIncomeDraftChange={onIncomeDraftChange}
        onIncomeMonthChange={onIncomeMonthChange}
        onSaveBudget={onSaveBudget}
        onSaveIncome={onSaveIncome}
      />,
    );

    const file = new File(["csv"], "import.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("Import CSV"), {
      target: { files: [file] },
    });
    fireEvent.change(screen.getByDisplayValue("1050.00"), { target: { value: "1200" } });
    fireEvent.change(screen.getByDisplayValue("2026-03"), { target: { value: "2026-04" } });
    fireEvent.change(screen.getByDisplayValue("1500.00"), { target: { value: "2400" } });
    fireEvent.click(screen.getByText("Save budget for month"));
    fireEvent.click(screen.getByText("Save income for month"));
    fireEvent.click(screen.getByText("Predict next month"));
    fireEvent.click(screen.getByText("Check budget status"));

    expect(onImport).toHaveBeenCalledWith(file);
    expect(screen.getByText("Choose CSV file")).toBeInTheDocument();
    expect(onBudgetDraftChange).toHaveBeenCalled();
    expect(onIncomeDraftChange).toHaveBeenCalled();
    expect(onIncomeMonthChange).toHaveBeenCalled();
    expect(onSaveBudget).toHaveBeenCalled();
    expect(onSaveIncome).toHaveBeenCalled();
    expect(onPredict).toHaveBeenCalled();
    expect(onCheckBudget).toHaveBeenCalled();
  });

  it("renders financial pulse insights and recent activity", () => {
    render(
      <FinancialPulse
        pulse={{
          health_score: 81,
          average_transaction: 32.25,
          transaction_count: 12,
          spend_velocity: 18.1,
          top_category_share: 44.5,
          runway_days: 16.5,
          narrative: "Steady spending rhythm.",
          cash_in: 1500,
          cash_out: 420,
          net_cash_flow: 1080,
          income_coverage: 357.14,
          recent_transactions: [
            {
              id: 1,
              date: "2026-03-01",
              category: "Food",
              description: "Groceries",
              amount: 20.5,
              entry_type: "expense",
            },
          ],
          recent_expenses: [],
        }}
      />,
    );

    expect(screen.getByText("Financial pulse")).toBeInTheDocument();
    expect(screen.getByText("Monthly income divided by monthly expenses. Very high values usually mean expenses are still low.")).toBeInTheDocument();
    expect(screen.getByText("Estimated days your remaining budget lasts at the current daily spend rate.")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("16.5 days")).toBeInTheDocument();
  });

  it("renders savings goals with clear saved, remaining, and goal metrics", () => {
    render(
      <SavingsGoalsPanel
        goals={[
          {
            id: 1,
            name: "Save £350",
            target_amount: 350,
            current_amount: 200,
            remaining_amount: 150,
            target_date: "2026-06-12",
            progress_percent: 57.1,
            created_at: "2026-06-09T10:00:00Z",
          },
        ]}
        onCreate={jest.fn()}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
      />,
    );

    expect(screen.getByText("Save £350")).toBeInTheDocument();
    expect(screen.getByText("Saved")).toBeInTheDocument();
    expect(screen.getByText("Remaining")).toBeInTheDocument();
    expect(screen.getByText("Goal")).toBeInTheDocument();
    expect(screen.getByText("Target 2026-06-12")).toBeInTheDocument();
    expect(screen.queryByText(/saved of/i)).not.toBeInTheDocument();
    expect(screen.queryByText("57.1%")).not.toBeInTheDocument();
  });

  it("creates, selects, updates, and deletes savings goals", () => {
    const onCreate = jest.fn();
    const onUpdate = jest.fn();
    const onDelete = jest.fn();

    render(
      <SavingsGoalsPanel
        goals={[
          {
            id: 2,
            name: "Emergency fund",
            target_amount: 1000,
            current_amount: 250,
            remaining_amount: 750,
            target_date: "2026-12-31",
            progress_percent: 25,
            created_at: "2026-06-09T10:00:00Z",
          },
        ]}
        onCreate={onCreate}
        onUpdate={onUpdate}
        onDelete={onDelete}
      />,
    );

    fireEvent.change(screen.getByLabelText("Goal name"), { target: { value: "Holiday" } });
    fireEvent.change(screen.getByLabelText("Target amount (GBP)"), { target: { value: "500" } });
    fireEvent.change(screen.getByLabelText("Current amount (GBP)"), { target: { value: "50" } });
    fireEvent.change(screen.getByLabelText("Target date"), { target: { value: "2026-10-15" } });
    fireEvent.click(screen.getByRole("button", { name: "Add goal" }));
    expect(onCreate).toHaveBeenCalledWith({
      name: "Holiday",
      target_amount: "500",
      current_amount: "50",
      target_date: "2026-10-15",
    });

    fireEvent.click(screen.getByRole("button", { name: /Emergency fund/i }));
    fireEvent.click(screen.getByRole("button", { name: "Update goal" }));
    expect(onUpdate).toHaveBeenCalledWith(2, {
      name: "Emergency fund",
      target_amount: "1000",
      current_amount: "250",
      target_date: "2026-12-31",
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete goal" }));
    expect(onDelete).toHaveBeenCalledWith(2);
  });

  it("renders savings goal empty state and clamps no-date progress", () => {
    const { rerender } = render(
      <SavingsGoalsPanel goals={[]} onCreate={jest.fn()} onUpdate={jest.fn()} onDelete={jest.fn()} />,
    );
    expect(screen.getByText("No savings goals created yet.")).toBeInTheDocument();

    rerender(
      <SavingsGoalsPanel
        goals={[
          {
            id: 3,
            name: "Buffer",
            target_amount: 500,
            current_amount: 800,
            remaining_amount: 0,
            target_date: null,
            progress_percent: 140,
            created_at: "2026-06-09T10:00:00Z",
          },
        ]}
        onCreate={jest.fn()}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
      />,
    );
    expect(screen.getByText("No target date")).toBeInTheDocument();
    expect(screen.getByLabelText("Buffer savings progress").querySelector("span")).toHaveStyle({ width: "100%" });
  });

  it("renders KPI charts, comparison panel, and recurring calendar", () => {
    const expenses = [
      { id: 1, date: "2026-03-01", category: "Food", description: "Groceries", amount: 20.5, entry_type: "expense" as const },
      { id: 2, date: "2026-03-05", category: "Travel", description: "Train", amount: 35.0, entry_type: "expense" as const },
      { id: 3, date: "2026-02-05", category: "Bills", description: "Utilities", amount: 65.0, entry_type: "expense" as const },
      { id: 4, date: "2026-03-08", category: "Salary", description: "Payroll", amount: 1200, entry_type: "income" as const },
    ];

    const onCreate = jest.fn();
    const onUpdate = jest.fn();
    const onDelete = jest.fn();

    render(
      <>
        <KpiVisuals expenses={expenses} summary={dashboard} />
        <SpendingComparisonPanel expenses={expenses} referenceDate={new Date(2026, 2, 20)} />
        <RecurringCalendarPanel
          items={[
            {
              id: 1,
              category: "Housing",
              description: "Rent",
              amount: 700,
              entry_type: "expense",
              frequency: "monthly",
              start_date: "2026-03-01",
              active: true,
            },
          ]}
          calendar={{
            window_start: "2026-03-01",
            window_end: "2026-04-04",
            occurrences: [
              {
                recurring_item_id: 1,
                date: "2026-03-01",
                category: "Housing",
                description: "Rent",
                amount: 700,
                entry_type: "expense",
                frequency: "monthly",
                days_until_due: 0,
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

    fireEvent.click(screen.getByRole("button", { name: "Category" }));
    fireEvent.click(screen.getByText("Add reminder"));

    expect(screen.getByText("Charts and performance signals")).toBeInTheDocument();
    expect(screen.getByText("Estimated month-end spend if the current daily spending pace continues.")).toBeInTheDocument();
    expect(screen.getByText("Current-month expenses divided by the number of days elapsed this month.")).toBeInTheDocument();
    expect(screen.getByText("Overlay spending comparison")).toBeInTheDocument();
    expect(screen.getByText("Average spend across the visible comparison periods.")).toBeInTheDocument();
    expect(screen.getByText("How the current period changed compared with the immediately previous period.")).toBeInTheDocument();
    expect(screen.getByText("Upcoming bills and frequent purchases")).toBeInTheDocument();
    expect(screen.getByText("How transaction ID verification works.")).toBeInTheDocument();
    expect(screen.getByText(/waiting for you to link a matching paid transaction ID/i)).toBeInTheDocument();
    expect(screen.getByText(/same type, amount, and category/i)).toBeInTheDocument();
    expect(screen.getByText(/Ticked means this reminder appears in upcoming schedules/i)).toBeInTheDocument();
    expect(onCreate).toHaveBeenCalled();
  });

  it("renders the piggy bank from cash-flow surplus and carryover", () => {
    const { rerender } = render(
      <PiggyBankPanel
        summary={dashboard}
        monthlyIncomeRecords={[
          { month_key: "2026-02", monthly_income: 1000 },
          { month_key: "2026-03", monthly_income: 9999 },
          { month_key: "", monthly_income: 9999 },
        ]}
        expenses={[
          { id: 21, date: "2026-02-03", category: "Food", description: "Groceries", amount: 200, entry_type: "expense" },
          { id: 22, date: "2026-03-03", category: "Food", description: "Current groceries", amount: 999, entry_type: "expense" },
          { id: 23, date: "", category: "Food", description: "Undated groceries", amount: 999, entry_type: "expense" },
        ]}
      />,
    );

    expect(screen.getByText("Piggy bank")).toBeInTheDocument();
    expect(screen.getByText("Cash-flow surplus carried forward")).toBeInTheDocument();
    expect(screen.getByText("Total piggy-bank balance")).toBeInTheDocument();
    expect(screen.getByText(/March 2026 increases the piggy bank/i)).toBeInTheDocument();
    expect(screen.getByText("Previous carryover")).toBeInTheDocument();
    expect(screen.getByText("Living-cost budget")).toBeInTheDocument();
    expect(screen.getByText("Income flowing into piggy bank")).toBeInTheDocument();

    rerender(<PiggyBankPanel summary={null} monthlyIncomeRecords={[]} expenses={[]} />);
    expect(screen.getByText(/Current month increases the piggy bank by £0.00/i)).toBeInTheDocument();
  });

  it("renders the Ollama agent panel and forwards actions", () => {
    const onTaskDraftChange = jest.fn();
    const onRun = jest.fn();

    render(
      <AiAgentPanel
        taskDraft="Prepare a finance briefing"
        result={{
          headline: "Finance briefing",
          summary: "Cash flow remains positive.",
          risk_level: "low",
          recommended_actions: ["Keep monitoring recurring bills."],
          email_subject: "Finance briefing",
          email_draft: "Monthly briefing attached.",
          task: "Prepare a finance briefing",
          model: "qwen3:4b",
          tools_used: ["get_dashboard_summary"],
          report_download_url: "/api/reports/monthly",
          generated_at: "2026-03-21T10:00:00Z",
          action_result: {
            type: "monthly_income_updated",
            message: "Monthly income updated.",
          },
        }}
        isRunning={false}
        onTaskDraftChange={onTaskDraftChange}
        onRun={onRun}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("Prepare a finance briefing"), {
      target: { value: "Update the briefing" },
    });
    fireEvent.click(screen.getByText("Run agent"));

    expect(screen.getByText("Ollama analysis agent")).toBeInTheDocument();
    expect(screen.getAllByText("Ollama operations agent").length).toBeGreaterThan(1);
    expect(screen.getByText("Prompt library")).toBeInTheDocument();
    expect(screen.getByText("Email workflow prompts")).toBeInTheDocument();
    expect(screen.getByText(/Manual sends do not turn off scheduled automation/i)).toBeInTheDocument();
    expect(screen.getByText("Monthly income update completed.")).toBeInTheDocument();
    expect(screen.getByText("Successful")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open monthly report" })).toHaveAttribute("href", "/api/reports/monthly");
    expect(screen.queryByText("Email draft")).not.toBeInTheDocument();
    expect(screen.queryByText("qwen3:4b")).not.toBeInTheDocument();
    expect(onTaskDraftChange).toHaveBeenCalled();
    expect(onRun).toHaveBeenCalled();
  });

  it("renders Ollama agent failures and remaining completion guidance states", () => {
    const baseResult = {
      headline: "Done",
      summary: "Done",
      risk_level: "medium",
      recommended_actions: [],
      email_subject: "Done",
      email_draft: "Done",
      task: "Run command",
      model: "qwen3:4b",
      tools_used: [],
      report_download_url: null,
      generated_at: "2026-03-21T10:00:00Z",
    };

    const { rerender } = render(
      <AiAgentPanel
        taskDraft="Send report"
        result={null}
        errorMessage="Backend unavailable."
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
      />,
    );
    expect(screen.getByText("Task did not complete.")).toBeInTheDocument();
    expect(screen.getByText("Backend unavailable.")).toBeInTheDocument();
    expect(screen.getByText(/No further finance changes were confirmed/i)).toBeInTheDocument();

    rerender(
      <AiAgentPanel
        taskDraft="Set budget"
        result={{
          ...baseResult,
          generated_at: "2026-03-21T10:01:00Z",
          action_result: { type: "monthly_budget_updated", message: "Budget updated." },
        }}
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
      />,
    );
    expect(screen.getByText("Monthly budget update completed.")).toBeInTheDocument();
    expect(screen.getByText("Medium risk.")).toHaveClass("status-warning");

    rerender(
      <AiAgentPanel
        taskDraft="Send month-end email"
        result={{
          ...baseResult,
          generated_at: "2026-03-21T10:02:00Z",
          risk_level: "high",
          action_result: { type: "month_end_email_sent", message: "Email sent." },
        }}
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
      />,
    );
    expect(screen.getByText("Month-end email sent.")).toBeInTheDocument();
    expect(screen.getByText("High risk.")).toHaveClass("status-over");

    rerender(
      <AiAgentPanel
        taskDraft="Generate report"
        result={{
          ...baseResult,
          generated_at: "2026-03-21T10:03:00Z",
          risk_level: "",
          action_result: { type: "monthly_report_generated", message: "Report generated." },
        }}
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
      />,
    );
    expect(screen.getByText("Report workflow completed.")).toBeInTheDocument();

    rerender(
      <AiAgentPanel
        taskDraft="Send bills"
        result={{
          ...baseResult,
          generated_at: "2026-03-21T10:04:00Z",
          action_result: { type: "upcoming_bills_email_skipped", message: "No eligible bills." },
        }}
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
      />,
    );
    expect(screen.getByText("Upcoming bills email not sent.")).toBeInTheDocument();
  });

  it("explains manual email workflow prompts in the Ollama agent reply", () => {
    render(
      <AiAgentPanel
        taskDraft="Send the upcoming bills email now."
        result={{
          headline: "Upcoming bills email sent",
          summary: "Upcoming bills reminder email sent.",
          risk_level: "low",
          recommended_actions: [],
          email_subject: "Upcoming bills",
          email_draft: "Upcoming bills reminder.",
          task: "Send the upcoming bills email now.",
          model: "qwen3:4b",
          tools_used: ["send_upcoming_bills_email_now"],
          report_download_url: null,
          generated_at: "2026-03-21T10:00:00Z",
          action_result: {
            type: "upcoming_bills_email_sent",
            message: "Upcoming bills reminder email sent.",
          },
        }}
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
      />,
    );

    expect(screen.getByText("Upcoming bills email sent.")).toBeInTheDocument();
    expect(screen.getAllByText(/8 calendar dates total/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/signed-in user's report email address/i)).toBeInTheDocument();
    expect(screen.getByText(/does not disable the scheduled upcoming-bills workflow/i)).toBeInTheDocument();
    expect(screen.getByText("Kind Regards,")).toBeInTheDocument();
    expect(screen.getByText("Monetra Organisation")).toBeInTheDocument();
  });

  it("formats structured finance briefing dictionaries without raw braces", () => {
    render(
      <AiAgentPanel
        taskDraft="Prepare a CFO-style monthly finance briefing"
        result={{
          headline: "Finance briefing generated",
          summary: "{'cash_flow': 'Cash flow is currently strong with a net cash flow of £2388.35, well within the budget.', 'recurring_bills': 'There are upcoming recurring bills, such as Test Late Deposit due on July 10th for £12.50.', 'recommended_actions': ['Monitor spending closely in high-cost categories like Food and Travel.', 'Review the predicted spending forecast for July.']}",
          risk_level: "low",
          recommended_actions: [],
          email_subject: "Monthly finance briefing",
          email_draft: "",
          task: "Prepare a CFO-style monthly finance briefing",
          model: "qwen3:4b",
          tools_used: ["get_dashboard_summary"],
          report_download_url: "/api/reports/monthly",
          generated_at: "2026-03-21T10:00:00Z",
        }}
        isRunning={false}
        onTaskDraftChange={jest.fn()}
        onRun={jest.fn()}
      />,
    );

    expect(screen.getByText(/Cash flow: Cash flow is currently strong/i)).toBeInTheDocument();
    expect(screen.getByText(/Recurring bill pressure: There are upcoming recurring bills/i)).toBeInTheDocument();
    expect(screen.getByText("Email-ready summary")).toBeInTheDocument();
    expect(screen.getByText("Monthly finance briefing")).toBeInTheDocument();
    expect(screen.getByText("Kind Regards,")).toBeInTheDocument();
    expect(screen.getByText("Monetra Organisation")).toBeInTheDocument();
    expect(screen.queryByText(/\{'cash_flow'/i)).not.toBeInTheDocument();
  });

  it("renders the automation center and forwards workflow actions", () => {
    const onRunWorkflow = jest.fn();

    render(
      <AutomationCenter
        workflows={[
          {
            id: "month_end_close",
            label: "Month-end close",
            description: "Generate the monthly report and review KPIs.",
            automation_focus: "Automates month-end reporting.",
            default_task: "Run the workflow.",
          },
        ]}
        runs={[
          {
            id: 1,
            workflow_name: "month_end_close",
            workflow_label: "Month-end close",
            status: "completed",
            headline: "Month-end pack ready",
            summary: "The KPI pack has been refreshed.",
            risk_level: "low",
            recommended_actions: ["Share the pack with stakeholders."],
            automated_actions: ["Generated a fresh monthly PDF report for distribution."],
            email_subject: "Month-end pack ready",
            email_draft: "The report and summary are ready.",
            task: "Run the workflow.",
            model: "mistral:latest",
            tools_used: ["generate_monthly_report"],
            report_download_url: "/api/reports/monthly",
            generated_at: "2026-03-21T10:00:00Z",
          },
          {
            id: 2,
            workflow_name: "upcoming_bills_check",
            workflow_label: "Upcoming bills check",
            status: "completed",
            headline: "Current month bills checked",
            summary: "Late and due-soon reminders were reviewed.",
            risk_level: "medium",
            recommended_actions: ["Clear overdue reminders."],
            automated_actions: ["Scanned current-month recurring items."],
            email_subject: "Bills checked",
            email_draft: "Bills checked.",
            task: "Run the workflow.",
            model: "mistral:latest",
            tools_used: ["get_upcoming_recurring_items"],
            report_download_url: null,
            generated_at: "22/03/2026, 10:00",
          },
        ]}
        recurringCalendar={{
          window_start: "2026-03-22",
          window_end: "2026-04-25",
          occurrences: [],
          late_occurrences: [
            {
              recurring_item_id: 9,
              date: "2026-03-10",
              category: "Subscription",
              description: "Chat GPT Plus",
              amount: 29.99,
              entry_type: "expense",
              frequency: "monthly",
              days_until_due: -12,
            },
          ],
          completed_occurrences: [],
        }}
        activeWorkflowName={null}
        liveStatusMessage={null}
        onRunWorkflow={onRunWorkflow}
      />,
    );

    fireEvent.click(screen.getByText("Run workflow"));

    expect(screen.getByText("Monetra workflow assistant")).toBeInTheDocument();
    expect(screen.getByText("Workflow-backed finance operations")).toBeInTheDocument();
    expect(screen.getByText(/Choose a workflow below/i)).toBeInTheDocument();
    expect(screen.getByText("Late reminders")).toBeInTheDocument();
    expect(screen.getByText("Chat GPT Plus: £29.99 due 2026-03-10")).toBeInTheDocument();
    expect(screen.getByText("Current month bills checked")).toBeInTheDocument();
    expect(screen.getByText("Latest response")).toBeInTheDocument();
    expect(screen.queryByText("Month-end pack ready")).not.toBeInTheDocument();
    expect(screen.queryByText("The KPI pack has been refreshed.")).not.toBeInTheDocument();
    expect(screen.queryByText("Share the pack with stakeholders.")).not.toBeInTheDocument();
    expect(screen.queryByText("Open report")).not.toBeInTheDocument();
    expect(onRunWorkflow).toHaveBeenCalledWith("month_end_close");
  });

  it("shows a fallback live message while an automation workflow is running", () => {
    render(
      <AutomationCenter
        workflows={[
          {
            id: "month_end_close",
            label: "Month-end close",
            description: "Generate the monthly report and review KPIs.",
            automation_focus: "Automates month-end reporting.",
            default_task: "Run the workflow.",
          },
        ]}
        runs={[]}
        activeWorkflowName="month_end_close"
        liveStatusMessage={null}
        onRunWorkflow={jest.fn()}
      />,
    );

    expect(screen.getByText("Run Month-end close.")).toBeInTheDocument();
    expect(screen.getByText("The workflow is gathering finance context and preparing derived outputs. Saved dashboard labels remain safe to read while this runs.")).toBeInTheDocument();
    expect(screen.getByText("Running workflow...").closest("button")).toBeDisabled();
  });
});


