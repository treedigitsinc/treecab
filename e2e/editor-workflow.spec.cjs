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

  await page.keyboard.press("w");
  await page.keyboard.press("a");
  await expect(page.getByText("Wall tool active.")).toBeVisible();

  await canvas.click({ position: { x: 180, y: 180 } });
  await expect(page.getByText("Wall sketch started.")).toBeVisible();
  await canvas.click({ position: { x: 340, y: 180 } });
  await expect(page.getByText("Wall drafted.")).toBeVisible();

  await page.getByRole("button", { name: "Save Room" }).click();
  await expect(page.getByText("Room geometry saved.")).toBeVisible();

  await page.keyboard.press("d");
  await page.keyboard.press("r");
  await expect(page.getByText("Door tool active.")).toBeVisible();

  await canvas.click({ position: { x: 260, y: 180 } });
  await expect(page.getByText("door added. Save room geometry to persist.")).toBeVisible();

  await page.keyboard.press("Escape");
  await canvas.click({ position: { x: 260, y: 200 } });

  await page.keyboard.press("m");
  await page.keyboard.press("v");
  await expect(page.getByText("Move tool active.")).toBeVisible();

  await canvas.click({ position: { x: 320, y: 180 } });
  await expect(page.getByText("Opening moved. Save room geometry to persist.")).toBeVisible();
});
