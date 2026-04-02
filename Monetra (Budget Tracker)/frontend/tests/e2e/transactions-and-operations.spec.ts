import { expect, test } from "@playwright/test";

import { registerBudgetTrackerApiMock } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await registerBudgetTrackerApiMock(page);
});

test("can add a new transaction", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Date").fill("2026-03-02");
  await page.getByPlaceholder("Housing, Travel, Food").fill("Travel");
  await page.getByPlaceholder("Weekly groceries").fill("Bus");
  await page.getByLabel("Amount (GBP)").fill("4.20");
  await page.getByRole("button", { name: "Add transaction" }).click();

  await expect(page.getByText("Expense #3 added successfully.")).toBeVisible();
});

test("can search and reset transaction records", async ({ page }) => {
  await page.goto("/");

  await page.getByPlaceholder("Search by ID").fill("1");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByText("Showing search result for expense #1.")).toBeVisible();

  await page.getByRole("button", { name: "Show all" }).click();
  await expect(page.getByText("Showing all records.")).toBeVisible();
});

test("can select a transaction row for editing", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Groceries").click();

  await expect(page.getByLabel("Category")).toHaveValue("Food");
  await expect(page.getByLabel("Description")).toHaveValue("Groceries");
});

test("can save the monthly budget and check budget status", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Monthly budget (GBP)").fill("1200");
  await page.getByRole("button", { name: "Save budget" }).click();
  await expect(page.getByText("Monthly budget updated to GBP 1200.00.")).toBeVisible();

  await page.getByRole("button", { name: "Check budget status" }).click();
  await expect(page.getByText(/spent GBP 420.00/)).toBeVisible();
});
