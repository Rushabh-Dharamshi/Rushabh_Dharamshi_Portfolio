import { expect, test } from "@playwright/test";

import { registerBudgetTrackerApiMock } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await registerBudgetTrackerApiMock(page);
});

test("shows recurring reminders on the calendar and upcoming list", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Weekly commute")).toBeVisible();
  await expect(page.getByText("Rent")).toBeVisible();
  await expect(page.getByText(/reminders in range/)).toBeVisible();
});

test("can create a recurring reminder", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Add reminder" }).click();
  await expect(page.getByText("Recurring item #3 created successfully.")).toBeVisible();
});

test("can select a recurring item and update it", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: /Rent/ }).click();
  await page.getByLabel("Description").fill("Updated rent");
  await page.getByRole("button", { name: "Update reminder" }).click();

  await expect(page.getByText("Recurring item #1 updated successfully.")).toBeVisible();
});

test("can run the local finance agent", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Run local agent" }).click();

  await expect(page.getByText("Local finance briefing")).toBeVisible();
  await expect(page.getByText("Email draft")).toBeVisible();
  await expect(page.getByText(/AI briefing generated with 2 tool calls/)).toBeVisible();
});
