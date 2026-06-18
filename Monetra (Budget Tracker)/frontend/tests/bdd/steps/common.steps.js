const { After, Before, Given, Then, When, setDefaultTimeout } = require("@cucumber/cucumber");
const assert = require("node:assert/strict");

const {
  buildRowsFromTable,
  installBudgetTrackerApiMock,
} = require("../support/mock-budget-tracker-api");

setDefaultTimeout(30 * 1000);

Before(function () {
  this.mockOverrides = {};
  this.mockController = null;
  this.latestResult = null;
  this.latestCollection = null;
});

After(function () {
  if (this.mockController) {
    this.mockController.restore();
    this.mockController = null;
  }
});

const client = {
  getDashboard: () => request("/api/dashboard"),
  getFinancialPulse: () => request("/api/analytics/financial-pulse"),
  getWordCloud: () => request("/api/analytics/wordcloud"),
  getPrediction: () => request("/api/predictions/next-month"),
  updateMonthlyBudget: (monthlyBudget) =>
    request("/api/settings/budget", {
      method: "PUT",
      body: JSON.stringify({ monthly_budget: monthlyBudget }),
    }),
  updateMonthlyIncome: (monthlyIncome, month) =>
    request("/api/settings/income", {
      method: "PUT",
      body: JSON.stringify({ monthly_income: monthlyIncome, month }),
    }),
  listExpenses: () => request("/api/expenses"),
  searchExpenseById: (expenseId) => request(`/api/expenses/${expenseId}`),
  createExpense: (payload) =>
    request("/api/expenses", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listRecurringItems: () => request("/api/recurring-items"),
  getRecurringCalendar: () => request("/api/recurring-items/calendar?days=35"),
  createRecurringItem: (payload) =>
    request("/api/recurring-items", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateRecurringItem: (itemId, payload) =>
    request(`/api/recurring-items/${itemId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  startFinanceBriefingAgent: (task) =>
    request("/api/agents/finance-briefing", {
      method: "POST",
      body: JSON.stringify({ task }),
    }),
  getFinanceBriefingJob: (jobId) => request(`/api/agents/finance-briefing/${jobId}`),
  startAgentWorkflow: (workflowName) =>
    request(`/api/agents/workflows/${workflowName}/run`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  getAgentWorkflowJob: (jobId) => request(`/api/agents/workflow-jobs/${jobId}`),
  listAgentRuns: () => request("/api/agents/runs?limit=8"),
  queryRag: (question) =>
    request("/api/rag/query", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  reindexRag: () =>
    request("/api/rag/reindex", {
      method: "POST",
      body: JSON.stringify({ force: true }),
    }),
};

Given("the budget tracker API is mocked", function () {
  this.mockController = installBudgetTrackerApiMock(this.mockOverrides);
});

Given("the budget tracker API is mocked with sample expense rows", function (dataTable) {
  this.mockOverrides.expenses = buildRowsFromTable(dataTable, { entry_type: "expense" });
  this.mockController = installBudgetTrackerApiMock(this.mockOverrides);
});

Given("the budget tracker API is mocked with sample recurring rows", function (dataTable) {
  this.mockOverrides.recurringItems = buildRowsFromTable(dataTable, {
    entry_type: "expense",
    frequency: "monthly",
    active: true,
  });
  this.mockController = installBudgetTrackerApiMock(this.mockOverrides);
});

When("I request the dashboard summary", async function () {
  this.latestResult = await client.getDashboard();
});

When("I request the financial pulse", async function () {
  this.latestResult = await client.getFinancialPulse();
});

When("I request the category word cloud", async function () {
  this.latestResult = await client.getWordCloud();
});

When("I request the next month prediction", async function () {
  this.latestResult = await client.getPrediction();
});

When("I save the monthly budget {string}", async function (value) {
  this.latestResult = await client.updateMonthlyBudget(Number.parseFloat(value));
});

When("I save the monthly income {string} for month {string}", async function (value, month) {
  this.latestResult = await client.updateMonthlyIncome(Number.parseFloat(value), month);
});

When("I request all expenses", async function () {
  this.latestCollection = await client.listExpenses();
  this.latestResult = this.latestCollection;
});

When("I search for expense id {string}", async function (expenseId) {
  this.latestResult = await client.searchExpenseById(Number.parseInt(expenseId, 10));
});

When(
  "I create an expense dated {string} in category {string} with description {string} and amount {string}",
  async function (date, category, description, amount) {
    this.latestResult = await client.createExpense({
      date,
      category,
      description,
      amount,
      entry_type: "expense",
    });
  },
);

When("I request all recurring reminders", async function () {
  this.latestCollection = await client.listRecurringItems();
  this.latestResult = this.latestCollection;
});

When("I request the recurring calendar", async function () {
  this.latestResult = await client.getRecurringCalendar();
});

When(
  "I create a recurring reminder in category {string} described as {string} amount {string} frequency {string} starting {string}",
  async function (category, description, amount, frequency, startDate) {
    this.latestResult = await client.createRecurringItem({
      category,
      description,
      amount,
      frequency,
      start_date: startDate,
      entry_type: "expense",
      end_date: null,
      active: true,
    });
  },
);

When(
  "I update recurring reminder {string} to category {string} description {string} amount {string} frequency {string} start date {string}",
  async function (itemId, category, description, amount, frequency, startDate) {
    this.latestResult = await client.updateRecurringItem(Number.parseInt(itemId, 10), {
      category,
      description,
      amount,
      frequency,
      start_date: startDate,
      entry_type: "expense",
      end_date: null,
      active: true,
    });
  },
);

When("I run a finance briefing for {string}", async function (task) {
  const job = await client.startFinanceBriefingAgent(task);
  this.latestResult = await client.getFinanceBriefingJob(job.id);
});

When("I run the workflow {string}", async function (workflowName) {
  const job = await client.startAgentWorkflow(workflowName);
  this.latestResult = await client.getAgentWorkflowJob(job.id);
});

When("I request recent workflow runs", async function () {
  this.latestCollection = await client.listAgentRuns();
  this.latestResult = this.latestCollection;
});

When("I ask the finance knowledge base {string}", async function (question) {
  this.latestResult = await client.queryRag(question);
});

When("I reindex the finance knowledge base", async function () {
  this.latestResult = await client.reindexRag();
});

Then("the latest result should contain the text {string}", function (expectedText) {
  assert.ok(this.latestResult !== null, "Expected a latest result but none was captured.");
  assert.match(JSON.stringify(this.latestResult), new RegExp(escapeRegExp(expectedText), "i"));
});

Then("the latest collection should contain the text {string}", function (expectedText) {
  assert.ok(this.latestCollection !== null, "Expected a latest collection but none was captured.");
  assert.match(JSON.stringify(this.latestCollection), new RegExp(escapeRegExp(expectedText), "i"));
});

Then("the latest result should have status {string}", function (status) {
  assert.equal(this.latestResult.status, status);
});

Then("the latest result should contain {int} sources", function (count) {
  assert.equal(Array.isArray(this.latestResult.sources) ? this.latestResult.sources.length : 0, count);
});

async function request(path, options) {
  const response = await fetch(path, {
    method: options?.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    body: options?.body,
  });
  const payload = await response.json();
  return payload.data;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
