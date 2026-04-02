function defaultExpenses() {
  return [
    {
      id: 1,
      date: "2026-03-01",
      category: "Food",
      description: "Groceries",
      amount: 20.5,
      entry_type: "expense",
    },
    {
      id: 2,
      date: "2026-03-02",
      category: "Salary",
      description: "Payroll",
      amount: 920,
      entry_type: "income",
    },
  ];
}

function defaultRecurringItems() {
  return [
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
    {
      id: 2,
      category: "Travel",
      description: "Weekly commute",
      amount: 45,
      entry_type: "expense",
      frequency: "weekly",
      start_date: "2026-03-24",
      active: true,
    },
  ];
}

async function registerBudgetTrackerApiMock(page, overrides = {}) {
  const state = {
    expenses: [...(overrides.expenses || defaultExpenses())],
    recurringItems: [...(overrides.recurringItems || defaultRecurringItems())],
    monthlyBudget: overrides.monthlyBudget || 1050,
    monthlyIncome: overrides.monthlyIncome || 1500,
    workflowRuns: [],
  };

  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const method = route.request().method();

    if (pathname === "/api/expenses" && method === "POST") {
      const payload = JSON.parse(route.request().postData() || "{}");
      const nextExpense = {
        id: state.expenses.reduce((max, item) => Math.max(max, item.id), 0) + 1,
        date: payload.date,
        category: payload.category,
        description: payload.description,
        amount: Number.parseFloat(payload.amount),
        entry_type: payload.entry_type || "expense",
      };
      state.expenses = [...state.expenses, nextExpense];
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ data: nextExpense }),
      });
      return;
    }

    if (pathname === "/api/expenses/1" && method === "DELETE") {
      state.expenses = state.expenses.filter((expense) => expense.id !== 1);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { message: "Expense deleted successfully." } }),
      });
      return;
    }

    if (pathname === "/api/settings/budget" && method === "PUT") {
      const payload = JSON.parse(route.request().postData() || "{}");
      state.monthlyBudget = Number.parseFloat(payload.monthly_budget);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { monthly_budget: state.monthlyBudget } }),
      });
      return;
    }

    if (pathname === "/api/settings/income" && method === "PUT") {
      const payload = JSON.parse(route.request().postData() || "{}");
      state.monthlyIncome = Number.parseFloat(payload.monthly_income);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { monthly_income: state.monthlyIncome } }),
      });
      return;
    }

    if (pathname === "/api/recurring-items" && method === "POST") {
      const payload = JSON.parse(route.request().postData() || "{}");
      const nextItem = {
        id: state.recurringItems.reduce((max, item) => Math.max(max, item.id), 0) + 1,
        category: payload.category,
        description: payload.description,
        amount: Number.parseFloat(payload.amount),
        entry_type: payload.entry_type || "expense",
        frequency: payload.frequency,
        start_date: payload.start_date,
        active: payload.active !== false,
      };
      state.recurringItems = [...state.recurringItems, nextItem];
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ data: nextItem }),
      });
      return;
    }

    if (pathname === "/api/recurring-items/1" && method === "PUT") {
      const payload = JSON.parse(route.request().postData() || "{}");
      state.recurringItems = state.recurringItems.map((item) =>
        item.id === 1
          ? {
              ...item,
              category: payload.category,
              description: payload.description,
              amount: Number.parseFloat(payload.amount),
              entry_type: payload.entry_type || "expense",
              frequency: payload.frequency,
              start_date: payload.start_date,
              active: payload.active !== false,
            }
          : item,
      );
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: state.recurringItems.find((item) => item.id === 1),
        }),
      });
      return;
    }

    if (pathname === "/api/recurring-items/1" && method === "DELETE") {
      state.recurringItems = state.recurringItems.filter((item) => item.id !== 1);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { message: "Recurring item deleted successfully." } }),
      });
      return;
    }

    if (pathname === "/api/agents/finance-briefing" && method === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            headline: "Local finance briefing",
            summary: "Cash flow remains positive and recurring costs are covered.",
            risk_level: "low",
            recommended_actions: ["Keep monitoring travel costs."],
            email_subject: "Finance briefing",
            email_draft: "Monthly briefing attached.",
            task: "Prepare a finance briefing",
            model: "mistral:latest",
            tools_used: ["get_dashboard_summary", "get_upcoming_recurring_items"],
            report_download_url: "/api/reports/monthly",
            generated_at: "2026-03-21T10:00:00Z",
          },
        }),
      });
      return;
    }

    if (pathname === "/api/agents/workflows" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              id: "month_end_close",
              label: "Month-end close",
              description: "Generate the monthly report and review KPIs.",
              automation_focus: "Automates month-end reporting.",
              default_task: "Run the month-end close workflow.",
            },
            {
              id: "upcoming_bills_check",
              label: "Upcoming bills check",
              description: "Review due-soon recurring costs.",
              automation_focus: "Automates reminder preparation.",
              default_task: "Run the upcoming bills workflow.",
            },
          ],
        }),
      });
      return;
    }

    if (pathname === "/api/agents/runs" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: state.workflowRuns }),
      });
      return;
    }

    if (pathname === "/api/agents/workflows/month_end_close/run" && method === "POST") {
      const run = {
        id: state.workflowRuns.length + 1,
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
        task: "Run the month-end close workflow.",
        model: "mistral:latest",
        tools_used: ["generate_monthly_report"],
        report_download_url: "/api/reports/monthly",
        generated_at: "2026-03-21T10:00:00Z",
      };
      state.workflowRuns = [run, ...state.workflowRuns];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: run }),
      });
      return;
    }

    const responses = {
      "/api/health": { status: "ok" },
      "/api/expenses": { data: state.expenses },
      "/api/expenses/1": { data: state.expenses.find((expense) => expense.id === 1) || null },
      "/api/dashboard": {
        data: {
          monthly_budget: state.monthlyBudget,
          current_month_total: 420,
          monthly_expenses: 420,
          monthly_income: state.monthlyIncome,
          net_cash_flow: state.monthlyIncome - 420,
          remaining_budget: state.monthlyBudget - 420,
          weekly_spending: 84.5,
          percent_spent: (420 / state.monthlyBudget) * 100,
          status: "within",
          month_label: "March 2026",
        },
      },
      "/api/analytics/categories": {
        data: {
          top_categories: [{ category: "Food", amount: 220 }],
          bottom_categories: [{ category: "Travel", amount: 80 }],
          total_spending: 300,
        },
      },
      "/api/analytics/wordcloud": {
        data: {
          top_category: "Food",
          frequencies: [{ label: "Groceries", value: 220 }],
        },
      },
      "/api/analytics/financial-pulse": {
        data: {
          health_score: 80,
          average_transaction: 32.5,
          transaction_count: 8,
          spend_velocity: 15,
          top_category_share: 43,
          runway_days: 18,
          narrative: "Steady spending rhythm.",
          cash_in: state.monthlyIncome,
          cash_out: 420,
          net_cash_flow: state.monthlyIncome - 420,
          income_coverage: (state.monthlyIncome / 420) * 100,
          recent_transactions: state.expenses,
          recent_expenses: state.expenses.filter((item) => item.entry_type === "expense"),
        },
      },
      "/api/recurring-items": { data: state.recurringItems },
      "/api/recurring-items/calendar": {
        data: {
          window_start: "2026-03-21",
          window_end: "2026-04-24",
          occurrences: buildOccurrences(state.recurringItems),
        },
      },
      "/api/settings": { data: { monthly_budget: state.monthlyBudget, monthly_income: state.monthlyIncome } },
      "/api/predictions/next-month": {
        data: {
          next_month: "April 2026",
          predicted_spending: 880,
          is_budget_exceeded: false,
          monthly_budget: state.monthlyBudget,
        },
      },
    };

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(responses[pathname] || { data: { message: "ok" } }),
    });
  });
}

function parseBoolean(value) {
  return String(value).toLowerCase() === "true";
}

function parseNumber(value) {
  return Number.parseFloat(value);
}

function buildRowsFromTable(dataTable, defaults = {}) {
  return dataTable.hashes().map((row) => ({
    ...defaults,
    ...row,
    id: Number.parseInt(row.id, 10),
    amount: parseNumber(row.amount),
    active: row.active === undefined ? defaults.active : parseBoolean(row.active),
  }));
}

function buildOccurrences(recurringItems) {
  return recurringItems
    .filter((item) => item.active)
    .map((item, index) => ({
      recurring_item_id: item.id,
      date: item.frequency === "weekly" ? "2026-03-24" : "2026-04-01",
      category: item.category,
      description: item.description,
      amount: item.amount,
      entry_type: item.entry_type,
      frequency: item.frequency,
      days_until_due: item.frequency === "weekly" ? 3 + index : 11 + index,
    }));
}

module.exports = {
  registerBudgetTrackerApiMock,
  buildRowsFromTable,
};
