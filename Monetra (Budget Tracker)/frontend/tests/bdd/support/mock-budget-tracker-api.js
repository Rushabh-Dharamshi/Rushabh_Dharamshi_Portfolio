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
      end_date: null,
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
      end_date: null,
      active: true,
    },
  ];
}

function defaultWorkflowRuns() {
  return [];
}

function defaultRagStatus() {
  return {
    available: true,
    collection_name: "monetra-finance-knowledge",
    indexed_at: "2026-03-21T10:00:00Z",
    document_count: 6,
    chunk_count: 12,
    signature: "bdd-signature",
  };
}

function defaultRagAnswer() {
  return {
    question: "What is putting pressure on cash flow?",
    answer: "Housing and groceries are the main pressure points this month, while recurring rent remains the largest fixed outgoing.",
    confidence: "high",
    follow_up_questions: [
      "Which reminders are due next?",
      "How does current spend compare with the monthly budget?",
    ],
    sources: [
      {
        source_label: "Financial pulse",
        doc_type: "financial_pulse",
        document_id: "financial-pulse::2026-03",
        excerpt: "Financial pulse narrative: Healthy but with housing pressure.",
        score: 0.9521,
        metadata: { doc_type: "financial_pulse", source_label: "Financial pulse" },
      },
      {
        source_label: "Recurring #1",
        doc_type: "recurring",
        document_id: "recurring::1",
        excerpt: "Recurring reminder Rent. Category Housing. Amount GBP 700. Frequency monthly.",
        score: 0.9344,
        metadata: { doc_type: "recurring", source_label: "Recurring #1" },
      },
    ],
    generated_at: "2026-03-21T10:05:00Z",
  };
}

function createFinanceBriefingJob() {
  return {
    id: "job-1",
    status: "queued",
    task: "Prepare a finance briefing",
    created_at: "2026-03-21T10:00:00Z",
    started_at: null,
    completed_at: null,
    error: null,
    result: null,
  };
}

function createFinanceBriefingResult() {
  return {
    headline: "Finance briefing",
    summary: "Cash flow remains positive and recurring costs are covered.",
    risk_level: "low",
    recommended_actions: ["Keep monitoring travel costs."],
    email_subject: "Finance briefing",
    email_draft: "Monthly briefing attached.",
    task: "Prepare a finance briefing",
    model: "qwen2.5:7b",
    tools_used: ["get_dashboard_summary", "get_upcoming_recurring_items"],
    report_download_url: "/api/reports/monthly",
    generated_at: "2026-03-21T10:00:00Z",
    trace: {
      memory: [],
      plan: {
        intent: "Prepare a finance briefing",
        success_criteria: ["Summarise cash flow", "Draft a concise email"],
        steps: [
          {
            tool: "get_dashboard_summary",
            reason: "Need the latest KPI baseline",
            arguments: {},
          },
        ],
      },
      execution_results: [
        {
          tool: "get_dashboard_summary",
          reason: "Loaded dashboard metrics",
          arguments: {},
          result: { monthly_budget: 1050, current_month_total: 420 },
        },
      ],
      verification: {
        headline: "Finance briefing ready",
        summary: "The latest monthly metrics and recurring costs were analysed.",
        risk_level: "low",
      },
      repair_attempts: 0,
    },
  };
}

function createWorkflowRun(overrides = {}) {
  return {
    id: overrides.id ?? 1,
    workflow_name: overrides.workflow_name ?? "month_end_close",
    workflow_label: overrides.workflow_label ?? "Month-end close",
    status: "completed",
    headline: overrides.headline ?? "Month-end pack ready",
    summary: overrides.summary ?? "The KPI pack has been refreshed.",
    risk_level: overrides.risk_level ?? "low",
    recommended_actions: overrides.recommended_actions ?? ["Share the pack with stakeholders."],
    automated_actions: overrides.automated_actions ?? ["Generated a fresh monthly PDF report for distribution."],
    email_subject: overrides.email_subject ?? "Month-end pack ready",
    email_draft: overrides.email_draft ?? "The report and summary are ready.",
    task: overrides.task ?? "Run the workflow",
    model: overrides.model ?? "qwen2.5:7b",
    tools_used: overrides.tools_used ?? ["generate_monthly_report"],
    report_download_url: overrides.report_download_url ?? "/api/reports/monthly",
    generated_at: overrides.generated_at ?? "2026-03-21T10:00:00Z",
  };
}

function installBudgetTrackerApiMock(overrides = {}) {
  const originalFetch = global.fetch;
  const state = {
    expenses: [...(overrides.expenses || defaultExpenses())],
    recurringItems: [...(overrides.recurringItems || defaultRecurringItems())],
    monthlyBudget: overrides.monthlyBudget || 1050,
    monthlyIncome: overrides.monthlyIncome || 1500,
    incomeMonth: overrides.incomeMonth || "2026-03",
    workflowRuns: [...(overrides.workflowRuns || defaultWorkflowRuns())],
    ragStatus: { ...(overrides.ragStatus || defaultRagStatus()) },
    ragAnswer: { ...(overrides.ragAnswer || defaultRagAnswer()) },
    financeBriefingJob: createFinanceBriefingJob(),
    financeBriefingResult: createFinanceBriefingResult(),
    workflowJobs: {},
  };

  global.fetch = async (input, init = {}) => {
    const rawUrl = typeof input === "string" ? input : input.url;
    const requestUrl = new URL(rawUrl, "http://localhost");
    const pathname = requestUrl.pathname;
    const method = (init.method || "GET").toUpperCase();
    const payload = parseJsonBody(init.body);

    if (pathname === "/api/auth/session" && method === "GET") {
      return jsonResponse(200, {
        authenticated: true,
        username: "Rushabh",
      });
    }

    if (pathname === "/api/auth/login" && method === "POST") {
      return jsonResponse(200, {
        authenticated: true,
        username: payload.username || "Rushabh",
      });
    }

    if (pathname === "/api/auth/logout" && method === "POST") {
      return jsonResponse(200, { message: "Signed out." });
    }

    if (pathname === "/api/expenses" && method === "GET") {
      return jsonResponse(200, state.expenses);
    }

    if (pathname === "/api/expenses" && method === "POST") {
      const nextExpense = {
        id: state.expenses.reduce((max, item) => Math.max(max, item.id), 0) + 1,
        date: payload.date,
        category: payload.category,
        description: payload.description,
        amount: Number.parseFloat(payload.amount),
        entry_type: payload.entry_type || "expense",
      };
      state.expenses = [...state.expenses, nextExpense];
      return jsonResponse(201, nextExpense);
    }

    if (/^\/api\/expenses\/\d+$/.test(pathname) && method === "GET") {
      const expenseId = Number.parseInt(pathname.split("/").pop(), 10);
      return jsonResponse(200, state.expenses.find((expense) => expense.id === expenseId) || null);
    }

    if (/^\/api\/expenses\/\d+$/.test(pathname) && method === "PUT") {
      const expenseId = Number.parseInt(pathname.split("/").pop(), 10);
      state.expenses = state.expenses.map((expense) =>
        expense.id === expenseId
          ? {
              ...expense,
              ...payload,
              amount: Number.parseFloat(payload.amount),
            }
          : expense,
      );
      return jsonResponse(200, state.expenses.find((expense) => expense.id === expenseId));
    }

    if (/^\/api\/expenses\/\d+$/.test(pathname) && method === "DELETE") {
      const expenseId = Number.parseInt(pathname.split("/").pop(), 10);
      state.expenses = state.expenses.filter((expense) => expense.id !== expenseId);
      return jsonResponse(200, { message: "Expense deleted successfully." });
    }

    if (pathname === "/api/settings" && method === "GET") {
      return jsonResponse(200, {
        monthly_budget: state.monthlyBudget,
        monthly_income: state.monthlyIncome,
        income_month: state.incomeMonth,
      });
    }

    if (pathname === "/api/settings/budget" && method === "PUT") {
      state.monthlyBudget = Number.parseFloat(payload.monthly_budget);
      return jsonResponse(200, {
        monthly_budget: state.monthlyBudget,
        monthly_income: state.monthlyIncome,
        income_month: state.incomeMonth,
      });
    }

    if (pathname === "/api/settings/income" && method === "PUT") {
      state.monthlyIncome = Number.parseFloat(payload.monthly_income);
      state.incomeMonth = payload.month || state.incomeMonth;
      return jsonResponse(200, {
        monthly_budget: state.monthlyBudget,
        monthly_income: state.monthlyIncome,
        income_month: state.incomeMonth,
      });
    }

    if (pathname === "/api/dashboard" && method === "GET") {
      return jsonResponse(200, {
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
        month_key: "2026-03",
        income_month: state.incomeMonth,
      });
    }

    if (pathname === "/api/analytics/categories" && method === "GET") {
      return jsonResponse(200, {
        top_categories: [{ category: "Food", amount: 220 }],
        bottom_categories: [{ category: "Travel", amount: 80 }],
        total_spending: 300,
      });
    }

    if (pathname === "/api/analytics/wordcloud" && method === "GET") {
      return jsonResponse(200, {
        top_category: "Food",
        frequencies: [{ label: "Groceries", value: 220 }],
      });
    }

    if (pathname === "/api/analytics/financial-pulse" && method === "GET") {
      return jsonResponse(200, {
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
      });
    }

    if (pathname === "/api/predictions/next-month" && method === "GET") {
      return jsonResponse(200, {
        next_month: "April 2026",
        predicted_spending: 880,
        is_budget_exceeded: false,
        monthly_budget: state.monthlyBudget,
      });
    }

    if (pathname === "/api/recurring-items" && method === "GET") {
      return jsonResponse(200, state.recurringItems);
    }

    if (pathname === "/api/recurring-items/calendar" && method === "GET") {
      return jsonResponse(200, {
        window_start: "2026-03-21",
        window_end: "2026-04-24",
        occurrences: buildOccurrences(state.recurringItems),
        completed_occurrences: [],
      });
    }

    if (pathname === "/api/recurring-items" && method === "POST") {
      const nextItem = {
        id: state.recurringItems.reduce((max, item) => Math.max(max, item.id), 0) + 1,
        category: payload.category,
        description: payload.description,
        amount: Number.parseFloat(payload.amount),
        entry_type: payload.entry_type || "expense",
        frequency: payload.frequency,
        start_date: payload.start_date,
        end_date: payload.end_date || null,
        active: payload.active !== false,
      };
      state.recurringItems = [...state.recurringItems, nextItem];
      return jsonResponse(201, nextItem);
    }

    if (/^\/api\/recurring-items\/\d+$/.test(pathname) && method === "PUT") {
      const itemId = Number.parseInt(pathname.split("/").pop(), 10);
      state.recurringItems = state.recurringItems.map((item) =>
        item.id === itemId
          ? {
              ...item,
              category: payload.category,
              description: payload.description,
              amount: Number.parseFloat(payload.amount),
              entry_type: payload.entry_type || "expense",
              frequency: payload.frequency,
              start_date: payload.start_date,
              end_date: payload.end_date || null,
              active: payload.active !== false,
            }
          : item,
      );
      return jsonResponse(200, state.recurringItems.find((item) => item.id === itemId));
    }

    if (/^\/api\/recurring-items\/\d+$/.test(pathname) && method === "DELETE") {
      const itemId = Number.parseInt(pathname.split("/").pop(), 10);
      state.recurringItems = state.recurringItems.filter((item) => item.id !== itemId);
      return jsonResponse(200, { message: "Recurring item deleted successfully." });
    }

    if (pathname === "/api/agents/finance-briefing" && method === "POST") {
      state.financeBriefingJob = createFinanceBriefingJob();
      state.financeBriefingJob.task = payload.task || state.financeBriefingJob.task;
      return jsonResponse(200, state.financeBriefingJob);
    }

    if (pathname === "/api/agents/finance-briefing/job-1" && method === "GET") {
      return jsonResponse(200, {
        ...state.financeBriefingJob,
        status: "completed",
        started_at: "2026-03-21T10:00:01Z",
        completed_at: "2026-03-21T10:00:03Z",
        result: state.financeBriefingResult,
      });
    }

    if (pathname === "/api/agents/workflows" && method === "GET") {
      return jsonResponse(200, [
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
      ]);
    }

    if (pathname === "/api/agents/runs" && method === "GET") {
      return jsonResponse(200, state.workflowRuns);
    }

    if (pathname === "/api/agents/bootstrap" && method === "POST") {
      return jsonResponse(200, []);
    }

    if (pathname === "/api/agents/automation/refresh" && method === "POST") {
      return jsonResponse(200, []);
    }

    if (/^\/api\/agents\/workflows\/[a-z_\-]+\/run$/.test(pathname) && method === "POST") {
      const workflowName = pathname.split("/")[4];
      const jobId = `${workflowName}-job-1`;
      const run = createWorkflowRun({
        id: state.workflowRuns.length + 1,
        workflow_name: workflowName,
        workflow_label: workflowName === "month_end_close" ? "Month-end close" : "Upcoming bills check",
        summary:
          workflowName === "month_end_close"
            ? "The KPI pack has been refreshed."
            : "The latest recurring bills were reviewed.",
        email_subject:
          workflowName === "month_end_close"
            ? "Month-end pack ready"
            : "Upcoming bills update",
      });
      state.workflowJobs[jobId] = run;
      return jsonResponse(200, {
        id: jobId,
        status: "queued",
        workflow_name: workflowName,
        task: "Run the workflow",
        created_at: "2026-03-21T10:00:00Z",
        started_at: null,
        completed_at: null,
        error: null,
        result: null,
      });
    }

    if (/^\/api\/agents\/workflow-jobs\//.test(pathname) && method === "GET") {
      const jobId = pathname.split("/").pop();
      const run = state.workflowJobs[jobId];
      state.workflowRuns = [run, ...state.workflowRuns.filter((item) => item.id !== run.id)];
      return jsonResponse(200, {
        id: jobId,
        status: "completed",
        workflow_name: run.workflow_name,
        task: "Run the workflow",
        created_at: "2026-03-21T10:00:00Z",
        started_at: "2026-03-21T10:00:01Z",
        completed_at: "2026-03-21T10:00:03Z",
        error: null,
        result: run,
      });
    }

    if (pathname === "/api/agents/automation/month-end-email" && method === "POST") {
      const run = createWorkflowRun({
        id: state.workflowRuns.length + 1,
        workflow_name: "month_end_email_dispatch",
        workflow_label: "Month-end email manual dispatch",
        headline: "Month-end report emailed manually",
        summary: "Manual month-end PDF report emailed to rushabh@example.com.",
        email_subject: "Month-end pack ready",
        email_draft: "Month-end report sent.",
      });
      state.workflowRuns = [run, ...state.workflowRuns];
      return jsonResponse(200, run);
    }

    if (pathname === "/api/agents/automation/upcoming-bills-email" && method === "POST") {
      const run = createWorkflowRun({
        id: state.workflowRuns.length + 1,
        workflow_name: "upcoming_bills_email_dispatch",
        workflow_label: "Upcoming bills email manual dispatch",
        headline: "Upcoming bills alert emailed",
        summary: "Upcoming bills alert emailed to rushabh@example.com for late unpaid reminders and bills due today plus the next 7 days (8 calendar dates total).",
        email_subject: "Upcoming bills update",
        email_draft: "Upcoming bills email sent.",
        report_download_url: null,
      });
      state.workflowRuns = [run, ...state.workflowRuns];
      return jsonResponse(200, run);
    }

    if (pathname === "/api/rag/status" && method === "GET") {
      return jsonResponse(200, state.ragStatus);
    }

    if (pathname === "/api/rag/reindex" && method === "POST") {
      state.ragStatus = {
        ...state.ragStatus,
        indexed_at: "2026-03-21T10:10:00Z",
        chunk_count: state.ragStatus.chunk_count + 2,
        signature: "bdd-signature-2",
        reindexed: true,
      };
      return jsonResponse(200, state.ragStatus);
    }

    if (pathname === "/api/rag/query" && method === "POST") {
      return jsonResponse(200, {
        ...state.ragAnswer,
        question: payload.question || state.ragAnswer.question,
      });
    }

    return jsonResponse(200, { message: "ok" });
  };

  return {
    state,
    restore() {
      global.fetch = originalFetch;
    },
  };
}

function parseJsonBody(body) {
  if (!body || typeof body !== "string") {
    return {};
  }
  try {
    return JSON.parse(body);
  } catch {
    return {};
  }
}

function jsonResponse(status, data) {
  return new Response(JSON.stringify({ data }), {
    status,
    headers: {
      "Content-Type": "application/json",
    },
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
    end_date: row.end_date === undefined ? defaults.end_date ?? null : row.end_date || null,
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
  buildRowsFromTable,
  installBudgetTrackerApiMock,
};
