import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";

test("guest catalog keeps vintages distinct, preserves search, and offers honest missing information", async ({
  page,
}, testInfo) => {
  await page.goto("/browse");
  await expect(page.locator(".catalog-wine")).toHaveCount(24);
  await expect(page.getByRole("link", { name: "Sign in", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Next wines", exact: true }).click();
  await expect(page.locator(".catalog-wine")).toHaveCount(6);
  await page.getByRole("link", { name: "Previous wines", exact: true }).click();
  await expect(page.locator(".catalog-wine")).toHaveCount(24);
  await page.getByLabel("Search the wine library").fill("ridge monte bello");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.locator(".catalog-wine")).toHaveCount(2);
  const releases = await page.locator(".catalog-wine .wine-release").allTextContents();
  expect(new Set(releases).size).toBe(2);
  const urls = await page
    .locator(".catalog-wine")
    .evaluateAll((links) => links.map((link) => (link as HTMLAnchorElement).href));
  expect(new Set(urls).size).toBe(2);
  await expect(page.getByRole("link", { name: "Next wines", exact: true })).toHaveCount(0);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  if (!process.env.CI) {
    await mkdir(testInfo.outputPath("visuals"), { recursive: true });
    await page.screenshot({
      path: testInfo.outputPath("visuals", "catalog-desktop.png"),
      fullPage: true,
    });
  }
  await page.locator(".catalog-wine").first().click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Monte Bello", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".catalog-detail-head")).toContainText(releases[0]);
  await expect(page.getByText("No verified offer available")).toBeVisible();
  const source = page.locator(".catalog-sources a");
  await expect(source).toHaveAttribute("href", /^https:\/\//);
  await expect(source).toHaveAttribute("rel", "noopener noreferrer");
  await expect(page.getByRole("link", { name: "Browse wines", exact: true })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (!process.env.CI) {
    await page.screenshot({
      path: testInfo.outputPath("visuals", "catalog-mobile.png"),
      fullPage: true,
    });
  }
  await page.getByRole("link", { name: "Back to wines", exact: true }).click();
  await expect(page.getByLabel("Search the wine library")).toHaveValue("ridge monte bello");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator(".catalog-wine").last().click();
  await expect(page.locator(".catalog-detail-head")).toContainText(releases[1]);
  await page.getByRole("link", { name: "Back to wines", exact: true }).click();
  await page.getByLabel("Search the wine library").fill("no such wine exists");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No matching wines yet." })).toBeVisible();
  await page.goto("/browse?offset=99999");
  await expect(page.getByRole("heading", { name: "That search link isn’t valid." })).toBeVisible();
  await page.goto("/browse/00000000-0000-0000-0000-000000000000");
  await expect(page.getByRole("heading", { name: "Wine not found", exact: true })).toBeVisible();
  await expect(page.locator('head meta[name="robots"]')).toHaveAttribute("content", "noindex");
});
