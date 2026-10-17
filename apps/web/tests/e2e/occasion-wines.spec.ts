import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";

test("occasion-first dinner stages three wines and four entries with safe retry and later additions", async ({
  page,
  request,
}, testInfo) => {
  await page.goto("/auth/sign-in?next=%2Foccasions%2Fnew");
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "New occasion", exact: true })).toBeVisible();
  await page.getByLabel("Title", { exact: false }).fill("Dinner with friends");
  await page.getByLabel("Occasion date").fill("2026-09-29");
  await page.getByRole("button", { name: "Add a wine", exact: true }).click();
  await page.getByLabel("Wine name", { exact: true }).fill("Cancelled wine");
  await page.getByRole("button", { name: "Cancel wine", exact: true }).click();
  await expect(page.locator(".staged-wine-list li")).toHaveCount(0);
  await expect(page.getByLabel("Title", { exact: false })).toHaveValue("Dinner with friends");
  for (const name of ["Cabernet", "Chardonnay", "Rose"]) {
    await page.getByRole("button", { name: "Add a wine", exact: true }).click();
    await page.getByLabel("Wine name", { exact: true }).fill(name);
    await expect(page.getByLabel("Date tried", { exact: true })).toHaveValue("2026-09-29");
    await page.getByLabel("Wine notes", { exact: false }).fill(`${name} first impression`);
    if (name === "Cabernet") {
      await page.getByRole("button", { name: "Add another glass of this wine" }).click();
      await page.getByLabel("Date tried — entry 2", { exact: true }).fill("2026-09-28");
      await page
        .getByLabel("Notes — entry 2", { exact: true })
        .fill("Earlier glass, softer finish");
      await page.reload();
      await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue(name);
      await expect(page.getByLabel("Notes — entry 2", { exact: true })).toHaveValue(
        "Earlier glass, softer finish",
      );
      await expect(
        page.getByRole("button", { name: "Create occasion", exact: true }),
      ).toBeDisabled();
    }
    await page.getByRole("button", { name: "Keep wine in draft", exact: true }).click();
  }
  await expect(page.locator(".staged-wine-list li")).toHaveCount(3);
  await page.getByRole("button", { name: "Edit Rose", exact: true }).click();
  await page.getByLabel("Wine name", { exact: true }).fill("Changed but cancelled");
  await page.getByRole("button", { name: "Cancel wine", exact: true }).click();
  await expect(page.locator(".staged-wine-list")).toContainText("Rose");
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`dinner-draft-${width}.png`),
      fullPage: true,
    });
  }
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()
    ).violations.map((issue) => issue.id),
  ).toEqual([]);
  const keys: string[] = [];
  await page.route("**/api/v1/occasions", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1) {
      expect((await route.fetch()).status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Create occasion", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry save", exact: true })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Add a wine", exact: true })).toBeDisabled();
  await page.reload();
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page).toHaveURL(/\/occasions\/[0-9a-f-]+$/);
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
  await expect(page.locator(".occasion-wine-card")).toHaveCount(3);
  await expect(page.locator(".occasion-wine-card").filter({ hasText: "Cabernet" })).toContainText(
    "2 drinking entries",
  );
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`dinner-saved-${width}.png`),
      fullPage: true,
    });
  }
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()
    ).violations.map((issue) => issue.id),
  ).toEqual([]);
  await page.getByRole("button", { name: "Add wines to occasion" }).click();
  await page.getByRole("button", { name: "Add a wine", exact: true }).click();
  await page.getByLabel("Wine name", { exact: true }).fill("Late arrival");
  await page.getByRole("button", { name: "Keep wine in draft", exact: true }).click();
  await page.reload();
  const addKeys: string[] = [];
  await page.route("**/api/v1/occasions/*/wines", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    addKeys.push(route.request().headers()["idempotency-key"]);
    if (addKeys.length === 1) {
      expect((await route.fetch()).status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Save wines", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry wine save", exact: true })).toBeEnabled();
  await page.reload();
  await page.getByRole("button", { name: "Retry wine save", exact: true }).click();
  await expect(page.locator(".occasion-wine-card")).toHaveCount(4);
  expect(addKeys).toHaveLength(2);
  expect(addKeys[0]).toBe(addKeys[1]);
  await page.locator(".occasion-wine-card").filter({ hasText: "Cabernet" }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(2);
  await expect(
    page.getByTestId("drinking-entry").filter({ hasText: "Earlier glass" }),
  ).toContainText("September 28, 2026");
  await page.getByRole("link", { name: "Back to My wines", exact: true }).click();
  await expect(page.locator(".wine-card")).toHaveCount(4);
});
