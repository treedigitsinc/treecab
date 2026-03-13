const assert = require("node:assert/strict");
const { chromium, request } = require("playwright");

const targetUrl = process.env.TEST_URL || "https://cab.treedigits.ca";
const sitePassword = process.env.TREECAB_SITE_PASSWORD || "nina@123@321";

async function main() {
  const apiContext = await request.newContext({ baseURL: targetUrl });
  const unauthorized = await apiContext.get("/api/status");
  assert.equal(unauthorized.status(), 401, "Expected /api/status to be blocked before login");
  await apiContext.dispose();

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(targetUrl, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "treecab" }).waitFor();
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Enter Site" }).click();
  await page.getByText("Incorrect password").waitFor();

  await page.getByLabel("Password").fill(sitePassword);
  await page.getByRole("button", { name: "Enter Site" }).click();
  await page.getByRole("heading", { name: "treecab studio" }).waitFor();
  await page.getByRole("button", { name: "Lock Site" }).waitFor();
  await page.getByText(/^Backend:/).waitFor();

  console.log(`Playwright smoke passed for ${targetUrl}`);
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
