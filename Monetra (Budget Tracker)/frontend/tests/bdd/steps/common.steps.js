const { After, Before, Given, Then, When, setDefaultTimeout } = require("@cucumber/cucumber");
const { chromium, expect } = require("@playwright/test");

const {
  buildRowsFromTable,
  registerBudgetTrackerApiMock,
} = require("../support/mock-budget-tracker-api");

setDefaultTimeout(60 * 1000);

Before(async function () {
  this.browser = await chromium.launch();
  this.page = await this.browser.newPage();
  this.mockOverrides = {};
});

After(async function () {
  await this.browser.close();
});

Given("the budget tracker API is mocked", async function () {
  await registerBudgetTrackerApiMock(this.page);
});

Given("the budget tracker API is mocked with sample expense rows", async function (dataTable) {
  this.mockOverrides.expenses = buildRowsFromTable(dataTable, { entry_type: "expense" });
  await registerBudgetTrackerApiMock(this.page, this.mockOverrides);
});

Given("the budget tracker API is mocked with sample recurring rows", async function (dataTable) {
  this.mockOverrides.recurringItems = buildRowsFromTable(dataTable, {
    entry_type: "expense",
    frequency: "monthly",
    active: true,
  });
  await registerBudgetTrackerApiMock(this.page, this.mockOverrides);
});

When("I open the budget tracker homepage", async function () {
  await this.page.goto("http://127.0.0.1:3000");
});

When("I click the button {string}", async function (label) {
  await this.page.getByRole("button", { name: label }).click();
});

When("I click the link {string}", async function (label) {
  await this.page.getByRole("link", { name: label }).click();
});

When("I click the text {string}", async function (text) {
  await this.page.getByText(text, { exact: false }).click();
});

When("I fill the field {string} with {string}", async function (label, value) {
  await this.page.getByLabel(label).fill(value);
});

When("I fill the placeholder {string} with {string}", async function (placeholder, value) {
  await this.page.getByPlaceholder(placeholder).fill(value);
});

Then("I should see the text {string}", async function (text) {
  await expect(this.page.getByText(text, { exact: false })).toBeVisible();
});

Then("I should see the value {string}", async function (value) {
  await expect(this.page.getByDisplayValue(value)).toBeVisible();
});

Then("I should not see the text {string}", async function (text) {
  await expect(this.page.getByText(text, { exact: false })).toHaveCount(0);
});
