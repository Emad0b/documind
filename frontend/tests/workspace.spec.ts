import { test, expect } from "@playwright/test";
import path from "node:path";
test("guest workspace, evaluation navigation, and sign out", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Try an isolated guest workspace/ })
    .click();
  await expect(
    page.getByRole("heading", { name: /Your documents/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retrieval evaluation" }).click();
  await expect(
    page.getByRole("heading", { name: "Evidence under the microscope." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run three retrieval baselines" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
});
test("upload, cited answer, saved history, evaluation, and mobile layout", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.goto("/");
  await page
    .getByRole("button", { name: /Try an isolated guest workspace/ })
    .click();
  await page
    .locator("input[type=file]")
    .setInputFiles(path.resolve("tests/fixtures/solar.pdf"));
  await expect(page.getByText("1 pages · Ready")).toBeVisible({
    timeout: 90000,
  });
  await page
    .getByRole("textbox", { name: "Ask about your documents" })
    .fill("How much solar electricity was generated?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.locator(".answer").last()).toContainText("42 units", {
    timeout: 30000,
  });
  await page.locator(".sources button").first().click();
  await expect
    .poll(() =>
      page
        .locator(".pdf-preview")
        .evaluate(
          (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
        ),
    )
    .toBe(true);
  await expect(
    page.getByRole("link", { name: "Open cited PDF page" }),
  ).toHaveAttribute("href", /\/pdf#page=1$/);
  await page.getByRole("button", { name: "Close source" }).click();
  await page.reload();
  await page.locator(".history-list summary").click();
  await page.locator(".history-list button").first().click();
  await expect(page.locator(".answer").last()).toContainText("42 units");
  await page.getByRole("button", { name: "Retrieval evaluation" }).click();
  await page.getByLabel("Question", { exact: true }).fill("solar electricity");
  await page.getByRole("button", { name: "Add test case" }).click();
  await page
    .getByRole("button", { name: "Run three retrieval baselines" })
    .click();
  await expect(page.locator(".eval-baselines article")).toHaveCount(3, {
    timeout: 30000,
  });
  await page.getByRole("button", { name: "Document chat" }).click();
  await expect(page.getByText("1 pages · Ready")).toBeVisible();
  await page.screenshot({ path: "../docs/workspace.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Toggle library" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
});
