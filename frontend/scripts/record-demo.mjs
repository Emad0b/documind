import { chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: {
    dir: "../docs/recordings",
    size: { width: 1440, height: 900 },
  },
});
const page = await context.newPage();
await page.goto(process.env.PREVIEW_URL || "http://127.0.0.1:5174");
await page
  .getByRole("button", { name: /Try an isolated guest workspace/ })
  .click();
await page.getByRole("heading", { name: /Your documents/ }).waitFor();
await page.screenshot({ path: "../docs/welcome.png" });
await page.waitForTimeout(2000);
await page
  .locator("input[type=file]")
  .setInputFiles(path.resolve("tests/fixtures/solar.pdf"));
await page.getByText("1 pages · Ready").waitFor({ timeout: 90000 });
await page.waitForTimeout(1800);
const box = page.getByRole("textbox", { name: "Ask about your documents" });
await box.pressSequentially("How much solar electricity was generated?", {
  delay: 45,
});
await page.getByRole("button", { name: "Send question" }).click();
await page.locator(".sources button").first().waitFor();
await page.waitForTimeout(2000);
await page.locator(".sources button").first().click();
await page.waitForTimeout(2000);
await page.screenshot({ path: "../docs/workspace.png" });
await page.waitForTimeout(2000);
await page.getByRole("button", { name: "Close source" }).click();
await page.getByRole("button", { name: "Retrieval evaluation" }).click();
await page.getByLabel("Question", { exact: true }).fill("solar electricity");
await page.getByRole("button", { name: "Add test case" }).click();
await page
  .getByRole("button", { name: "Run three retrieval baselines" })
  .click();
await page.locator(".eval-baselines article").first().waitFor();
await page.waitForTimeout(2500);
await page.screenshot({ path: "../docs/evaluation.png" });
await context.close();
const videoPath = await page.video().path();
await fs.rename(videoPath, "../docs/demo.webm");
await browser.close();
console.log("Recorded docs/demo.webm and three screenshots.");
