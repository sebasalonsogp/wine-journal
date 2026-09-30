import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";

test("occasions save titled and untitled memories and safely retry a lost response", async ({
  page,
  request,
}, testInfo) => {
  await page.goto("/occasions/new");
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/occasions\/new$/);
  await page.getByLabel("Title", { exact: false }).fill("Dinner with Maya and Alex");
  await page.getByLabel("Occasion date").fill("2026-09-12");
  await page.getByLabel("Local time", { exact: false }).fill("19:30");
  await page.getByLabel("Timezone", { exact: true }).fill("America/New_York");
  await page.getByLabel("Location", { exact: false }).fill("Maya’s house");
  await page
    .getByRole("textbox", { name: "Notes optional", exact: true })
    .fill(
      "Homemade pasta, a few favorite bottles, and a long conversation.\nA night worth remembering.",
    );
  await page.reload();
  await expect(page.getByLabel("Title", { exact: false })).toHaveValue("Dinner with Maya and Alex");
  await page.setViewportSize({ width: 390, height: 1000 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("occasion-form-390.png"), fullPage: true });
  const formAudit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(formAudit.violations.map((issue) => issue.id)).toEqual([]);
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
  await expect(page.getByLabel("Title", { exact: false })).toBeDisabled();
  await page.reload();
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page).toHaveURL(/\/occasions\/[0-9a-f-]+$/);
  expect(keys).toHaveLength(2);
  expect(keys[0] === keys[1]).toBe(true);
  await expect(page.getByRole("heading", { name: "Dinner with Maya and Alex" })).toBeVisible();
  await expect(page.locator(".occasion-heading")).toContainText("19:30");
  await expect(page.locator(".occasion-heading")).toContainText("Maya’s house");
  await expect(page.locator(".occasion-notes")).toContainText("Homemade pasta");
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`occasion-detail-${width}.png`),
      fullPage: true,
    });
  }
  await page.getByRole("link", { name: "Back to Occasions" }).click();
  await expect(page.locator(".occasion-card")).toHaveCount(1);
  await page.getByRole("link", { name: "New occasion", exact: true }).click();
  await page.getByLabel("Occasion date").fill("2026-09-20");
  await page.getByRole("button", { name: "Create occasion", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("September 20, 2026");
  await page.getByRole("link", { name: "Back to Occasions" }).click();
  await expect(page.locator(".occasion-card")).toHaveCount(2);
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.screenshot({
      path: testInfo.outputPath(`occasion-list-${width}.png`),
      fullPage: true,
    });
  }
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(audit.violations.map((issue) => issue.id)).toEqual([]);
  await page.getByRole("link", { name: "My wines", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
});

test("occasion edits retain stale drafts, reconcile lost responses and isolate accounts", async ({
  page,
  request,
  context,
}) => {
  await page.goto("/auth/sign-in?next=%2Foccasions%2Fnew");
  await finishSignIn(page, request);
  await page.getByLabel("Title", { exact: false }).fill("Dinner");
  await page.getByLabel("Occasion date").fill("2026-09-29");
  await page.getByRole("button", { name: "Create occasion", exact: true }).click();
  await expect(page.getByRole("button", { name: "Edit occasion", exact: true })).toBeVisible();
  const occasionUrl = page.url();
  await page.getByRole("button", { name: "Edit occasion", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Notes optional", exact: true })
    .fill("My unfinished notes");
  await page.reload();
  await expect(page.getByRole("textbox", { name: "Notes optional", exact: true })).toHaveValue(
    "My unfinished notes",
  );
  const second = await context.newPage();
  await second.goto(occasionUrl);
  await second.getByRole("button", { name: "Edit occasion", exact: true }).click();
  await second
    .getByRole("textbox", { name: "Notes optional", exact: true })
    .fill("A newer saved memory");
  await second.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(second.locator(".occasion-notes")).toContainText("A newer saved memory");
  await page.bringToFront();
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByRole("heading", { name: "This occasion has changed" })).toBeVisible();
  await expect(page.locator(".edit-conflict")).toContainText("A newer saved memory");
  await expect(page.getByRole("textbox", { name: "Notes optional", exact: true })).toHaveValue(
    "My unfinished notes",
  );
  await page.getByRole("button", { name: "Save my changes over this version" }).click();
  await expect(page.locator(".occasion-notes")).toContainText("My unfinished notes");
  await second.close();
  await page.getByRole("button", { name: "Edit occasion", exact: true }).click();
  await page.getByRole("textbox", { name: "Notes optional", exact: true }).fill("");
  let dropped = false;
  await page.route("**/api/v1/occasions/*", async (route) => {
    if (route.request().method() === "PUT" && !dropped) {
      dropped = true;
      expect((await route.fetch()).status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "couldn’t confirm" })).toBeVisible();
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByRole("heading", { name: "This occasion has changed" })).toBeVisible();
  await page.getByRole("button", { name: "Use latest saved occasion" }).click();
  await expect(page.locator(".occasion-notes")).not.toContainText("My unfinished notes");
  await page.getByRole("button", { name: "Edit occasion", exact: true }).click();
  await page.getByLabel("Title", { exact: false }).fill("Private unfinished title");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/browse$/);
  await page.goto("/auth/sign-in?next=%2Foccasions");
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "A place for the moments." })).toBeVisible();
  await page.goto(occasionUrl);
  await expect(
    page.getByRole("alert").filter({ hasText: "This record is unavailable" }),
  ).toBeVisible();
  await expect(page.getByText("Private unfinished title")).toHaveCount(0);
});
