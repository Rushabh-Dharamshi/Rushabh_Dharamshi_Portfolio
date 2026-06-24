import { expect, test } from "@playwright/test";

import { registerBudgetTrackerApiMock } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await registerBudgetTrackerApiMock(page);
});

test("can add a new transaction", async ({ page }) => {
  await page.goto("/");

  const expensePanel = page.locator("section").filter({ hasText: "Expense management" });
  await page.getByRole("textbox", { name: "Date", exact: true }).fill("2026-03-02");
  await page.getByPlaceholder("Housing, Travel, Food").fill("Travel");
  await page.getByPlaceholder("Weekly groceries").fill("Bus");
  await expensePanel.getByLabel("Amount (GBP)").fill("4.20");
  await page.getByRole("button", { name: "Add expense" }).click();

  await expect(page.getByText("Expense #3 added successfully.")).toBeVisible();
});

test("can search and reset transaction records", async ({ page }) => {
  await page.goto("/");

  await page.getByPlaceholder("Search by expense #").fill("1");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByText("Showing search result for expense #1.")).toBeVisible();

  await page.getByRole("button", { name: "Show all" }).click();
  await expect(page.getByText("Showing all records.")).toBeVisible();
});

test("can select a transaction row for editing", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("row", { name: /#1 2026-03-01 Food Groceries/ }).click();

  await expect(page.getByPlaceholder("Housing, Travel, Food")).toHaveValue("Food");
  await expect(page.getByPlaceholder("Weekly groceries")).toHaveValue("Groceries");
});

test("can save the monthly budget and check budget status", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel(/Monthly budget for selected month/).fill("1200");
  await page.getByRole("button", { name: "Save budget for month" }).click();
  await expect(page.getByText(/Monthly budget updated to GBP 1200.00/)).toBeVisible();

  await page.getByRole("button", { name: "Check budget status" }).click();
  await expect(page.getByText(/spent GBP 420.00/)).toBeVisible();
});
