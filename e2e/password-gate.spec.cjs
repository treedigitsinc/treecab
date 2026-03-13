const { test, expect } = require("@playwright/test");

const sitePassword = process.env.TREECAB_SITE_PASSWORD || "nina@123@321";

test("password gate blocks access until login succeeds", async ({ page, request }) => {
  const apiBeforeLogin = await request.get("/api/status");
  expect(apiBeforeLogin.status()).toBe(401);

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "treecab" })).toBeVisible();
  await expect(page.getByText("unlock API access")).toBeVisible();

  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Enter Site" }).click();
  await expect(page.getByText("Incorrect password")).toBeVisible();

  await page.getByLabel("Password").fill(sitePassword);
  await page.getByRole("button", { name: "Enter Site" }).click();

  await expect(page.getByRole("heading", { name: "treecab studio" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Lock Site" })).toBeVisible();
  await expect(page.getByText(/^Backend:/)).toBeVisible();
});
