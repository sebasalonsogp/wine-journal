import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";
import { photo, processPhoto } from "./photo-fixtures";

async function journal(page: Page, path: string, method = "GET", body?: object) {
  return page.evaluate(
    async ({ path, method, body }) => {
      const session = await (
        await fetch("/auth/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        })
      ).json();
      const response = await fetch(`${session.apiUrl}/api/v1/${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok)
        throw new Error(`Synthetic move fixture failed (${response.status}); contents withheld.`);
      return response.json();
    },
    { path, method, body },
  );
}

async function fixture(page: Page, many = false) {
  const occasion = await journal(page, "occasions", "POST", {
    occasionDate: "2026-10-20",
    title: "Dinner for correction",
  });
  const source = await journal(page, "entries", "POST", {
    consumedDate: "2026-10-20",
    manualWine: { name: "Original bottle", vintageStatus: "YEAR", year: 2021 },
    occasionId: occasion.id,
    notes: "Keep the dinner memory",
  });
  const target = await journal(page, "entries", "POST", {
    consumedDate: "2026-10-01",
    manualWine: { name: "Correct bottle", vintageStatus: "YEAR", year: 2022 },
  });
  const wine = await journal(page, `me/wines/${source.userWineId}`);
  await journal(page, "entries", "POST", { consumedDate: "2026-10-19", releaseId: wine.releaseId });
  await journal(page, `me/wines/${wine.id}/rating`, "PUT", { version: 0, score: 4.5 });
  if (many)
    for (let index = 0; index < 20; index++)
      await journal(page, "entries", "POST", {
        consumedDate: "2026-10-10",
        manualWine: { name: `Other bottle ${index}` },
      });
  return { source, target, occasion };
}

test("move chooses a paginated wine, preserves photos and occasions, and supports cancellation", async ({
  page,
  request,
}, testInfo) => {
  test.setTimeout(120000);
  await page.goto("/auth/sign-in");
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
  const { source, target, occasion } = await fixture(page, true);
  await page.goto(`/my-wines/${source.userWineId}`);
  const row = page.getByTestId("drinking-entry").first();
  await row.getByText("Photos & memories", { exact: true }).click();
  await page.route("**/storage/v1/object/upload/sign/**", async (route) => {
    if (route.request().method() === "PUT") await route.abort("failed");
    else await route.continue();
  });
  await row.getByLabel("Add photos", { exact: true }).setInputFiles(photo);
  await expect(row.getByRole("button", { name: "Retry photo" })).toBeVisible();
  await expect(row.getByRole("button", { name: "Move to another wine" })).toBeDisabled();
  await page.unroute("**/storage/v1/object/upload/sign/**");
  const completed = page.waitForResponse(
    (response) => response.url().endsWith("/complete") && response.ok(),
  );
  await row.getByRole("button", { name: "Retry photo" }).click();
  await completed;
  processPhoto();
  await expect(row.getByTestId("entry-photo").locator("img")).toBeVisible({ timeout: 25000 });
  await row.getByLabel("Photo caption").fill("Dinner together");
  await expect(row.getByRole("button", { name: "Move to another wine" })).toBeDisabled();
  await row.getByRole("button", { name: "Save caption", exact: true }).click();
  await expect(row.getByRole("button", { name: "Save caption", exact: true })).toBeDisabled();
  let failed = false;
  await page.route("**/api/v1/me/wines?**", async (route) => {
    if (!failed) {
      failed = true;
      await route.abort("failed");
    } else await route.continue();
  });
  await row.getByRole("button", { name: "Move to another wine" }).click();
  const move = page.getByRole("region", { name: "Move drinking entry" });
  await expect(move.getByRole("heading", { name: "Move to another wine" })).toBeFocused();
  await move.getByRole("button", { name: "Try loading wines again" }).click();
  await expect(
    move.getByLabel("Destination wine").locator(`option[value="${target.userWineId}"]`),
  ).toHaveCount(0);
  await move.getByRole("button", { name: "Load more wines" }).click();
  await move.getByLabel("Destination wine").selectOption(target.userWineId);
  await move.getByRole("button", { name: "Review move", exact: true }).click();
  await expect(move).toContainText("Correct bottle · 2022");
  await row.getByLabel("Photo caption").fill("A caption still being written");
  await expect(move.getByRole("button", { name: "Confirm move", exact: true })).toBeDisabled();
  await row.getByRole("button", { name: "Use saved caption", exact: true }).click();
  await expect(move.getByRole("button", { name: "Confirm move", exact: true })).toBeEnabled();
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    if (!process.env.CI)
      await page.screenshot({
        path: testInfo.outputPath(`move-review-${width}.png`),
        fullPage: true,
      });
  }
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await move.getByRole("button", { name: "Close without another change" }).click();
  expect((await journal(page, `entries/${source.id}`)).userWineId).toBe(source.userWineId);
  await row.getByRole("button", { name: "Move to another wine" }).click();
  await move.getByLabel("Search your wines").fill("Correct bottle");
  await move.getByRole("button", { name: "Search wines", exact: true }).click();
  await move.getByLabel("Destination wine").selectOption(target.userWineId);
  await move.getByRole("button", { name: "Review move", exact: true }).click();
  await move.getByRole("button", { name: "Confirm move", exact: true }).click();
  await expect(move.getByRole("link", { name: "View moved entry" })).toBeVisible();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await expect(page.getByTestId("current-rating")).toHaveText("4.5 / 5");
  const moved = await journal(page, `entries/${source.id}`);
  expect(moved).toEqual({ ...source, userWineId: target.userWineId, version: 2 });
  expect(
    (await journal(page, `occasions/${occasion.id}/wines`)).items.map(
      (wine: { id: string }) => wine.id,
    ),
  ).toEqual([target.userWineId]);
  await move.getByRole("link", { name: "View moved entry" }).click();
  await page.getByText("Photos & memories", { exact: true }).click();
  await expect(page.getByLabel("Photo caption")).toHaveValue("Dinner together");
  await expect(page.getByTestId("entry-photo").locator("img")).toBeVisible();
});

test("new wine move recovers a lost response without creating another wine", async ({
  page,
  request,
}) => {
  await page.goto("/auth/sign-in");
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
  const { source } = await fixture(page);
  await page.goto(`/my-wines/${source.userWineId}`);
  await page
    .getByTestId("drinking-entry")
    .first()
    .getByRole("button", { name: "Move to another wine" })
    .click();
  const move = page.getByRole("region", { name: "Move drinking entry" });
  await move.getByRole("button", { name: "Enter a new wine" }).click();
  await move.getByLabel("Wine name", { exact: true }).fill("New corrected bottle");
  await move.getByLabel("Vintage", { exact: true }).selectOption("YEAR");
  await move.getByLabel("Vintage year").fill("2020");
  await expect(move.getByLabel("Date tried")).toHaveCount(0);
  await move.getByRole("button", { name: "Review move", exact: true }).click();
  let puts = 0;
  await page.route("**/api/v1/entries/*/wine", async (route) => {
    if (route.request().method() === "PUT") {
      puts++;
      expect((await route.fetch()).status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await move.getByRole("button", { name: "Confirm move", exact: true }).click();
  await move.getByRole("button", { name: "Check saved entry" }).click();
  await expect(move).toContainText("currently with New corrected bottle · 2020");
  await expect(move.getByRole("button", { name: "Confirm move", exact: true })).toHaveCount(0);
  expect(puts).toBe(1);
  expect((await journal(page, "me/wines")).items).toHaveLength(3);
  await move.getByRole("link", { name: "View saved entry", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "New corrected bottle", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("drinking-entry")).toContainText("Keep the dinner memory");
  expect((await journal(page, "me/wines")).items).toHaveLength(3);
});

test("stale moves require review and private choices clear on cross-tab sign-out", async ({
  page,
  request,
  context,
}) => {
  await page.goto("/auth/sign-in");
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
  const { source, target } = await fixture(page);
  await page.goto(`/my-wines/${source.userWineId}`);
  await page
    .getByTestId("drinking-entry")
    .first()
    .getByRole("button", { name: "Move to another wine" })
    .click();
  const move = page.getByRole("region", { name: "Move drinking entry" });
  await move.getByLabel("Destination wine").selectOption(target.userWineId);
  await move.getByRole("button", { name: "Review move", exact: true }).click();
  await journal(page, `entries/${source.id}`, "PATCH", {
    version: 1,
    notes: "A newer tasting note",
  });
  await move.getByRole("button", { name: "Confirm move", exact: true }).click();
  await expect(move.getByRole("region", { name: "Latest saved entry" })).toContainText(
    "A newer tasting note",
  );
  expect((await journal(page, `entries/${source.id}`)).userWineId).toBe(source.userWineId);
  await move.getByRole("button", { name: "Review move using this version" }).click();
  await move.getByRole("button", { name: "Confirm move", exact: true }).click();
  await expect(move.getByRole("link", { name: "View moved entry" })).toBeVisible();
  expect((await journal(page, `entries/${source.id}`)).notes).toBe("A newer tasting note");
  await move.getByRole("button", { name: "Close move details" }).click();
  await page
    .getByTestId("drinking-entry")
    .getByRole("button", { name: "Move to another wine" })
    .click();
  await move.getByRole("button", { name: "Enter a new wine" }).click();
  await move.getByLabel("Wine name", { exact: true }).fill("Private unfinished choice");
  const other = await context.newPage();
  await other.goto("/my-wines");
  await other.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  await expect(page.getByText("Private unfinished choice")).toHaveCount(0);
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
});
