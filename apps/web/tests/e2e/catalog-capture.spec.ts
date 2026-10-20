import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";
import { finishSignIn } from "./journal-auth";

async function journalCounts(page: Page) {
  return page.evaluate(async () => {
    const session = await (
      await fetch("/auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      })
    ).json();
    const response = await fetch(`${session.apiUrl}/api/v1/me/wines`, {
      headers: { Authorization: `Bearer ${session.accessToken}` },
    });
    if (!response.ok) throw new Error("Could not read synthetic journal counts.");
    const data = await response.json();
    return data.items.map((wine: { id: string; entryCount: number; year: number }) => ({
      id: wine.id,
      count: wine.entryCount,
      year: wine.year,
    })) as { id: string; count: number; year: number }[];
  });
}

test("catalog selection survives sign-in, lost save response, repeats and a different vintage", async ({
  page,
  request,
}, testInfo) => {
  const { items } = await (
    await request.get("http://127.0.0.1:8000/api/v1/catalog/wines?q=ridge%20monte%20bello")
  ).json();
  expect(items).toHaveLength(2);
  await page.goto(`/browse/${items[0].id}`);
  await page.getByRole("link", { name: "I tried this wine", exact: true }).click();
  await expect(page.locator(".selected-wine")).toContainText(String(items[0].year));
  await page.getByLabel("Date tried").fill("2026-10-20");
  await page.getByLabel("Quick notes").fill("A catalog memory with friends");
  await page.getByRole("button", { name: "Sign in to save", exact: true }).click();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  await expect(page.getByLabel("Quick notes")).toHaveValue("A catalog memory with friends");
  await expect(page.locator(".selected-wine")).toContainText(String(items[0].year));
  expect(await journalCounts(page)).toEqual([]);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  if (!process.env.CI) {
    await mkdir(testInfo.outputPath("visuals"), { recursive: true });
    await page.screenshot({
      path: testInfo.outputPath("visuals", "catalog-capture-desktop.png"),
      fullPage: true,
    });
  }
  let dropResponse = true;
  await page.route("**/api/v1/entries", async (route) => {
    if (route.request().method() === "POST" && dropResponse) {
      dropResponse = false;
      const response = await route.fetch();
      expect(response.status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry save", exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page).toHaveURL(/\/my-wines\/[0-9a-f-]+$/);
  const firstUrl = page.url();
  expect((await journalCounts(page)).map((wine) => wine.count)).toEqual([1]);
  await page.goto(`/capture?catalog=${items[0].id}`);
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page).toHaveURL(firstUrl);
  expect((await journalCounts(page)).map((wine) => wine.count)).toEqual([2]);
  await page.goto(`/capture?catalog=${items[1].id}`);
  await expect(page.locator(".selected-wine")).toContainText(String(items[1].year));
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page).toHaveURL(/\/my-wines\/[0-9a-f-]+$/);
  expect(page.url()).not.toBe(firstUrl);
  const wines = await journalCounts(page);
  expect(wines).toHaveLength(2);
  expect(wines.find((wine) => wine.year === items[0].year)?.count).toBe(2);
  expect(wines.find((wine) => wine.year === items[1].year)?.count).toBe(1);
});

test("a new catalog selection cannot silently replace an unfinished or uncertain entry", async ({
  page,
  request,
}, testInfo) => {
  const { items } = await (
    await request.get("http://127.0.0.1:8000/api/v1/catalog/wines?q=ridge%20monte%20bello")
  ).json();
  await page.goto("/capture");
  await page.getByLabel("Wine name", { exact: true }).fill("My unfinished bottle");
  await page.getByLabel("Quick notes").fill("Keep these notes");
  await page.goto(`/capture?catalog=${items[0].id}`);
  await expect(
    page.getByRole("heading", { name: "You already have an unfinished entry." }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (!process.env.CI) {
    await mkdir(testInfo.outputPath("visuals"), { recursive: true });
    await page.screenshot({
      path: testInfo.outputPath("visuals", "catalog-draft-choice-mobile.png"),
      fullPage: true,
    });
  }
  await page.getByRole("button", { name: "Continue my unfinished entry", exact: true }).click();
  await expect(page.getByLabel("Quick notes")).toHaveValue("Keep these notes");
  await page.reload();
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue("My unfinished bottle");
  await page.goto(`/capture?catalog=${items[0].id}`);
  await page
    .getByRole("button", { name: "Discard draft and use selected wine", exact: true })
    .click();
  await expect(page.locator(".selected-wine")).toContainText(String(items[0].year));
  await expect(page.getByLabel("Quick notes")).toHaveValue("");
  await page.getByRole("button", { name: "Sign in to save", exact: true }).click();
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  // A request with an uncertain outcome must keep its original identity and key.
  await page.route("**/api/v1/entries", (route) => route.abort("failed"));
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry save", exact: true })).toBeVisible();
  await page.goto(`/capture?catalog=${items[1].id}`);
  await expect(
    page.getByRole("heading", { name: "You already have an unfinished entry." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Discard draft and use selected wine", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Continue my unfinished entry", exact: true }).click();
  await expect(page.locator(".selected-wine")).toContainText(String(items[0].year));
  await page.unroute("**/api/v1/entries");
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page).toHaveURL(/\/my-wines\/[0-9a-f-]+$/);
  expect((await journalCounts(page)).map((wine) => wine.year)).toEqual([items[0].year]);
});

test("catalog return through sign-in hides an owned draft and clears it on account change", async ({
  page,
  request,
  context,
}) => {
  const { items } = await (
    await request.get("http://127.0.0.1:8000/api/v1/catalog/wines?q=ridge%20monte%20bello")
  ).json();
  await page.goto(`/capture?catalog=${items[0].id}`);
  await page.getByRole("button", { name: "Sign in to save", exact: true }).click();
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  await page.getByLabel("Quick notes").fill("The first account's private draft");
  await context.clearCookies();
  await page.goto(`/capture?catalog=${items[1].id}`);
  await expect(
    page.getByRole("heading", { name: "Your unfinished entry is private." }),
  ).toBeVisible();
  await expect(page.getByText("The first account's private draft", { exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Sign in to continue", exact: true }).click();
  await finishSignIn(page, request);
  await expect(page).toHaveURL(new RegExp(`/capture\\?catalog=${items[1].id}$`));
  await expect(page.locator(".selected-wine")).toContainText(String(items[1].year));
  await expect(page.getByLabel("Quick notes")).toHaveValue("");
  await expect(
    page.getByText("The previous account’s unfinished entry was cleared."),
  ).toBeVisible();
  expect(await journalCounts(page)).toEqual([]);
});
