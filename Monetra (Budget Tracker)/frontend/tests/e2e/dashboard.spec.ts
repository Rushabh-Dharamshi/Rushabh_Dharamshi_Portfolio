import { expect, test } from "@playwright/test";

import { registerBudgetTrackerApiMock } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await registerBudgetTrackerApiMock(page);
});

test("smoke: loads the dashboard shell and primary panels", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Financial pulse")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Expense records" })).toBeVisible();
  await expect(page.getByText("Upcoming bills and frequent purchases")).toBeVisible();
  await expect(page.getByText("Monetra workflow assistant")).toBeVisible();
  await expect(page.getByText("Ollama analysis agent")).toBeVisible();
});

test("shows the month label and budget context", async ({ page }) => {
  await page.goto("/");

  const budgetOverview = page.locator(".summary-panel");
  await expect(budgetOverview.locator("h2", { hasText: "March 2026" })).toBeVisible();
  await expect(page.getByText(/Budget status for March 2026:/)).toBeVisible();
  await expect(page.getByText(/Cash flow this month:/)).toBeVisible();
});

test("loads the category insights and word cloud content", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Top categories")).toBeVisible();
  await expect(page.getByLabel("Description word cloud for Food").getByText("Groceries")).toBeVisible();
});

test("predicts next month spending from the operations panel", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Predict next month" }).click();

  await expect(page.getByText("Prediction refreshed for April 2026.")).toBeVisible();
  await expect(page.getByText("Forecast remains within the budget threshold.")).toBeVisible();
});
