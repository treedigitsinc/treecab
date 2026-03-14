const { test, expect } = require("@playwright/test");

const sitePassword = process.env.TREECAB_SITE_PASSWORD || "nina@123@321";

test("project setup opens the canvas and uses right-click actions", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Password").fill(sitePassword);
  await page.getByRole("button", { name: "Enter Site" }).click();

  await expect(page.getByRole("heading", { name: "treecab studio" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Start with the project basics." })).toBeVisible();

  await page.getByLabel("Project Name").first().fill("Testing - Template/Export");
  await page.getByLabel("Scope").first().selectOption("Kitchen");
  await page.getByRole("button", { name: "Create Project & Open Canvas" }).click();

  await expect(page.getByRole("heading", { name: "Plan Canvas" })).toBeVisible();
  await expect(page.getByText("Wheel to zoom, middle mouse to pan")).toBeVisible();

  const canvas = page.locator(".konvajs-content canvas").first();
  await expect(canvas).toBeVisible();

  await canvas.click({ button: "right", position: { x: 180, y: 180 } });
  await expect(page.locator(".context-menu-title")).toHaveText("Canvas Actions");
  await expect(page.getByRole("button", { name: "Add Existing Wall" })).toBeVisible();

  await page.getByRole("button", { name: "Add Existing Wall" }).click();
  await expect(page.getByText("Wall added. Save room geometry to persist.")).toBeVisible();
});
