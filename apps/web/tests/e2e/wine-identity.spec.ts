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
        throw new Error(
          `Synthetic identity fixture failed (${response.status}); contents withheld.`,
        );
      return response.json();
    },
    { path, method, body },
  );
}

async function fixture(page: Page) {
  const occasion = await journal(page, "occasions", "POST", {
    occasionDate: "2026-10-20",
    title: "Label correction dinner",
  });
  const entry = await journal(page, "entries", "POST", {
    consumedDate: "2026-10-20",
    manualWine: { name: "Label typo" },
    occasionId: occasion.id,
    notes: "A memory to keep",
  });
  const wine = await journal(page, `me/wines/${entry.userWineId}`);
  await journal(page, "entries", "POST", {
    consumedDate: "2026-10-19",
    releaseId: wine.releaseId,
  });
  await journal(page, `me/wines/${wine.id}/rating`, "PUT", { version: 0, score: 4.5 });
  return { entry, wine, occasion };
}

test("manual corrections review shared impact and preserve memories", async ({
  page,
  request,
}, testInfo) => {
  test.setTimeout(120000);
  await page.goto("/auth/sign-in");
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
  const { wine, entry, occasion } = await fixture(page);
  await page.goto(`/my-wines/${wine.id}`);
  const row = page.getByTestId("drinking-entry").first();
  await row.getByText("Photos & memories", { exact: true }).click();
  const completed = page.waitForResponse((r) => r.url().endsWith("/complete") && r.ok());
  await row.getByLabel("Add photos", { exact: true }).setInputFiles(photo);
  await completed;
  processPhoto();
  await expect(row.getByTestId("entry-photo").locator("img")).toBeVisible({ timeout: 25000 });
  await row.getByLabel("Photo caption").fill("Still editing this caption");
  await page.getByRole("button", { name: "Correct wine details", exact: true }).click();
  const editor = page.getByRole("region", { name: "Correct wine details", exact: true });
  await expect(editor.getByRole("heading", { name: "Correct wine details" })).toBeFocused();
  await editor.getByLabel("Wine name", { exact: true }).fill("Cancelled correction");
  await editor.getByRole("button", { name: "Close without another change" }).click();
  expect((await journal(page, `me/wines/${wine.id}`)).name).toBe("Label typo");
  await page.getByRole("button", { name: "Correct wine details", exact: true }).click();
  await editor.getByLabel("Wine name", { exact: true }).fill("Correct label");
  await editor.getByLabel("Vintage", { exact: true }).selectOption("YEAR");
  await editor.getByLabel("Vintage year").fill("2022");
  await editor.getByText("More label details", { exact: false }).click();
  await editor.getByLabel("Producer", { exact: true }).fill("Example Estate");
  await editor.getByLabel("Edition", { exact: false }).fill("Reserve");
  await expect(editor).toContainText("all 2 tastings");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await editor.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("identity-desktop.png") });
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await editor.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("identity-phone.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await editor.getByRole("button", { name: "Review correction" }).click();
  await expect(editor.getByRole("heading", { name: "Correct wine details" })).toBeFocused();
  expect((await journal(page, `me/wines/${wine.id}`)).identityVersion).toBe(0);
  await editor.getByRole("button", { name: "Confirm correction" }).click();
  await expect(page.getByText("Wine details saved.", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Correct label", exact: true })).toBeVisible();
  await expect(row.getByLabel("Photo caption")).toHaveValue("Still editing this caption");
  await row.getByRole("button", { name: "Save caption", exact: true }).click();
  await expect(row.getByRole("button", { name: "Save caption", exact: true })).toBeDisabled();
  expect(await journal(page, `entries/${entry.id}`)).toEqual(entry);
  const saved = await journal(page, `me/wines/${wine.id}`);
  expect(saved).toMatchObject({
    releaseId: wine.releaseId,
    identityVersion: 1,
    currentRating: 4.5,
    entryCount: 2,
  });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Correct label", exact: true })).toBeVisible();
  await page.goto(`/occasions/${occasion.id}`);
  await expect(page.getByText("Correct label", { exact: true }).first()).toBeVisible();
});

test("stale corrections need review, lost responses are checked, and sign-out clears drafts", async ({
  page,
  request,
  context,
}) => {
  await page.goto("/auth/sign-in");
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
  const { wine } = await fixture(page);
  await page.goto(`/my-wines/${wine.id}`);
  await page.getByRole("button", { name: "Correct wine details", exact: true }).click();
  const editor = page.getByRole("region", { name: "Correct wine details", exact: true });
  await editor.getByLabel("Wine name", { exact: true }).fill("My correction");
  await journal(page, `me/wines/${wine.id}/identity`, "PUT", {
    version: 0,
    wine: { name: "Newer saved label" },
  });
  await editor.getByRole("button", { name: "Review correction" }).click();
  await editor.getByRole("button", { name: "Confirm correction" }).click();
  await expect(editor.getByRole("region", { name: "Latest saved wine" })).toContainText(
    "Newer saved label",
  );
  expect((await journal(page, `me/wines/${wine.id}`)).name).toBe("Newer saved label");
  await editor.getByRole("button", { name: "Review my correction using this version" }).click();
  let puts = 0;
  await page.route("**/api/v1/me/wines/*/identity", async (route) => {
    if (route.request().method() === "PUT") {
      puts++;
      await route.fetch();
      await route.abort("failed");
    } else await route.continue();
  });
  await editor.getByRole("button", { name: "Confirm correction" }).click();
  await editor.getByRole("button", { name: "Check saved wine" }).click();
  await expect(page.getByText("Wine details saved.", { exact: false })).toBeVisible();
  expect(puts).toBe(1);
  expect((await journal(page, `me/wines/${wine.id}`)).identityVersion).toBe(2);
  await page.getByRole("button", { name: "Correct wine details", exact: true }).click();
  await editor.getByLabel("Wine name", { exact: true }).fill("Private unfinished correction");
  const other = await context.newPage();
  await other.goto("/my-wines");
  await other.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  await expect(editor).toHaveCount(0);
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
});
