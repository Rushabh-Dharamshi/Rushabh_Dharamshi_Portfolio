import { expect, test } from "@playwright/test";

import { registerBudgetTrackerApiMock } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await registerBudgetTrackerApiMock(page);
});

test("shows recurring reminders on the calendar and upcoming list", async ({ page }) => {
  await page.goto("/");

  const recurringPanel = page.locator("section").filter({ hasText: "Recurring planner" });
  await expect(recurringPanel.getByRole("heading", { name: "Upcoming reminders due soon" })).toBeVisible();
  await expect(recurringPanel.getByText("1 due today + next 7 days")).toBeVisible();
  await expect(recurringPanel.getByRole("heading", { name: "All reminders" })).toBeVisible();
});

test("can create a recurring reminder", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Add reminder" }).click();
  await expect(page.getByText("Recurring item #3 created successfully.")).toBeVisible();
});

test("can select a recurring item and update it", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: /Rent/ }).click();
  await page.locator("section").filter({ hasText: "Recurring planner" }).getByLabel("Description").fill("Updated rent");
  await page.getByRole("button", { name: "Update reminder" }).click();

  await expect(page.getByText("Recurring item #1 updated successfully.")).toBeVisible();
});

test("can run the finance agent", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Run agent" }).click();

  await expect(page.getByText("Cash flow remains positive and recurring costs are covered.")).toBeVisible();
  await expect(page.getByText("Keep monitoring travel costs.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open monthly report" })).toBeVisible();
  await expect(page.getByText(/AI briefing generated with 2 tool calls/)).toBeVisible();
});
