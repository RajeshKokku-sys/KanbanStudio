import { test, expect } from "@playwright/test";

/**
 * End‑to‑end test that verifies the Kanban board renders with the expected
 * number of columns and that a card can be added and removed.
 */
test.describe("Kanban board UI", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the root of the dev server (configured in playwright.config.ts)
    await page.goto("/");
  });

  test("renders five columns", async ({ page }) => {
    const columns = await page.getByTestId(/column-/i).all();
    await expect(columns).toHaveLength(5);
  });

  test("add and delete a card", async ({ page }) => {
    const firstColumn = page.getByTestId(/column-/i).first();

    // Click the "Add a card" button inside the first column
    await firstColumn.getByRole("button", { name: /add a card/i }).click();

    // Fill in the card form (Locator uses `getByPlaceholder` instead of `getByPlaceholderText`)
    await firstColumn.getByPlaceholder(/card title/i).fill("E2E Card");
    await firstColumn.getByPlaceholder(/details/i).fill("Details");
    await firstColumn.getByRole("button", { name: /add card/i }).click();

    // Verify the card appears
    await expect(firstColumn.getByText("E2E Card")).toBeVisible();

    // Delete the card
    await firstColumn.getByRole("button", { name: /delete e2e card/i }).click();

    // Ensure it is gone
    await expect(firstColumn.getByText("E2E Card")).not.toBeVisible();
  });
});
