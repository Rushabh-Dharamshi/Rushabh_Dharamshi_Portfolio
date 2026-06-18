import type { Page, Route } from "@playwright/test";

export type MockExpenseRow = {
  id: number;
  date: string;
  category: string;
  description: string;
  amount: number;
  entry_type: "expense" | "income";
};

export type MockRecurringRow = {
  id: number;
  category: string;
  description: string;
  amount: number;
  entry_type: "expense" | "income";
  frequency: "weekly" | "monthly";
  start_date: string;
  active: boolean;
};

type MockApiOptions = {
  expenses?: MockExpenseRow[];
  recurringItems?: MockRecurringRow[];
  monthlyIncome?: number;
};

const defaultExpenses: MockExpenseRow[] = [
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

const defaultRecurringItems: MockRecurringRow[] = [
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

export async function registerBudgetTrackerApiMock(
  page: Page,
  options: MockApiOptions = {},
) {
  const expenses = options.expenses ?? defaultExpenses;
  const recurringItems = options.recurringItems ?? defaultRecurringItems;
  const monthlyIncome = options.monthlyIncome ?? 1500;

  await page.route("**/api/**", async (route) => {
    await fulfillBudgetTrackerRoute(route, expenses, recurringItems, monthlyIncome);
  });
}

async function fulfillBudgetTrackerRoute(
  route: Route,
  expenses: MockExpenseRow[],
  recurringItems: MockRecurringRow[],
  monthlyIncome: number,
) {
  const pathname = new URL(route.request().url()).pathname;
  const method = route.request().method();

  if (pathname === "/api/expenses" && method === "POST") {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          id: 3,
          date: "2026-03-02",
          category: "Travel",
          description: "Bus",
          amount: 4.2,
          entry_type: "expense",
        },
      }),
    });
    return;
  }

  if (pathname === "/api/expenses/1" && method === "PUT") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          id: 1,
          date: "2026-03-02",
          category: "Food",
          description: "Updated groceries",
          amount: 22.0,
          entry_type: "expense",
        },
      }),
    });
    return;
  }

  if (pathname === "/api/expenses/1" && method === "DELETE") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: { message: "Expense deleted successfully." } }),
    });
    return;
  }

  if (pathname === "/api/expenses/import" && method === "POST") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: { imported_rows: 1, skipped_rows: 1 } }),
    });
    return;
  }

  if (pathname === "/api/expenses/export") {
    await route.fulfill({
      status: 200,
      contentType: "text/csv",
      body: "ID,Date,Category,Description,Amount,Type\n1,2026-03-01,Food,Groceries,20.50,expense\n",
    });
    return;
  }

  if (pathname === "/api/reports/monthly") {
    await route.fulfill({
      status: 200,
      contentType: "application/pdf",
      body: "%PDF-1.4",
    });
    return;
  }

  if (pathname === "/api/agents/finance-briefing" && method === "POST") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          headline: "Finance briefing",
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

  if (pathname === "/api/settings/budget" && method === "PUT") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: { monthly_budget: 1200 } }),
    });
    return;
  }

  if (pathname === "/api/settings/income" && method === "PUT") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: { monthly_income: 1500 } }),
    });
    return;
  }

  if (pathname === "/api/recurring-items" && method === "POST") {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          id: 3,
          category: "Subscriptions",
          description: "Gym",
          amount: 30,
          entry_type: "expense",
          frequency: "monthly",
          start_date: "2026-03-28",
          active: true,
        },
      }),
    });
    return;
  }

  if (pathname === "/api/recurring-items/1" && method === "PUT") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          id: 1,
          category: "Housing",
          description: "Updated rent",
          amount: 725,
          entry_type: "expense",
          frequency: "monthly",
          start_date: "2026-03-01",
          active: true,
        },
      }),
    });
    return;
  }

  if (pathname === "/api/recurring-items/1" && method === "DELETE") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: { message: "Recurring item deleted successfully." } }),
    });
    return;
  }

  if (pathname === "/api/agents/workflows") {
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
        ],
      }),
    });
    return;
  }

  if (pathname === "/api/agents/runs") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
    return;
  }

  if (pathname === "/api/agents/workflows/month_end_close/run" && method === "POST") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
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
          task: "Run the month-end close workflow.",
          model: "mistral:latest",
          tools_used: ["generate_monthly_report"],
          report_download_url: "/api/reports/monthly",
          generated_at: "2026-03-21T10:00:00Z",
        },
      }),
    });
    return;
  }

  const payloads: Record<string, unknown> = {
    "/api/health": { status: "ok" },
    "/api/expenses": { data: expenses },
    "/api/expenses/1": { data: expenses[0] },
    "/api/dashboard": {
      data: {
        monthly_budget: 1050,
        current_month_total: 420,
        monthly_expenses: 420,
        monthly_income: monthlyIncome,
        net_cash_flow: monthlyIncome - 420,
        remaining_budget: 630,
        weekly_spending: 84.5,
        percent_spent: 40,
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
        cash_in: monthlyIncome,
        cash_out: 420,
        net_cash_flow: monthlyIncome - 420,
        income_coverage: (monthlyIncome / 420) * 100,
        recent_transactions: expenses,
        recent_expenses: expenses.filter((item) => item.entry_type === "expense"),
      },
    },
    "/api/recurring-items": { data: recurringItems },
    "/api/recurring-items/calendar": {
      data: {
        window_start: "2026-03-21",
        window_end: "2026-04-24",
        occurrences: [
          {
            recurring_item_id: 1,
            date: "2026-04-01",
            category: "Housing",
            description: "Rent",
            amount: 700,
            entry_type: "expense",
            frequency: "monthly",
            days_until_due: 11,
          },
          {
            recurring_item_id: 2,
            date: "2026-03-24",
            category: "Travel",
            description: "Weekly commute",
            amount: 45,
            entry_type: "expense",
            frequency: "weekly",
            days_until_due: 3,
          },
        ],
      },
    },
    "/api/settings": { data: { monthly_budget: 1050, monthly_income: monthlyIncome } },
    "/api/predictions/next-month": {
      data: {
        next_month: "April 2026",
        predicted_spending: 880,
        is_budget_exceeded: false,
        monthly_budget: 1050,
      },
    },
  };

  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(payloads[pathname] ?? { data: { message: "ok" } }),
  });
}
