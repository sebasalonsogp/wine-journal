import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";

test("saved entries link, move and unlink with conflict review and lost-response recovery", async ({
  page,
  request,
  context,
}, testInfo) => {
  await page.goto("/auth/sign-in");
  await finishSignIn(page, request);
  await expect(page.getByRole("heading", { name: "Your first page is waiting." })).toBeVisible();
  const fixture = await page.evaluate(async () => {
    const session = await (
      await fetch("/auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      })
    ).json();
    async function save(path: string, body: object, method = "POST") {
      const response = await fetch(`${session.apiUrl}/api/v1/${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify(body),
      });
      if (!response.ok)
        throw new Error(`Synthetic link fixture failed (${response.status}); response withheld.`);
      return response.json();
    }
    const dinner = await save("occasions", {
      title: "Dinner with friends",
      occasionDate: "2026-09-29",
    });
    const tasting = await save("occasions", {
      title: "Winery tasting",
      occasionDate: "2026-09-28",
    });
    const first = await save("entries", {
      manualWine: { name: "Journal Cabernet" },
      consumedDate: "2026-09-29",
      notes: "First entry, blackberry",
    });
    const wineResponse = await fetch(`${session.apiUrl}/api/v1/me/wines/${first.userWineId}`, {
      headers: { Authorization: `Bearer ${session.accessToken}` },
    });
    if (!wineResponse.ok) throw new Error("Synthetic wine unavailable; response withheld.");
    const wine = await wineResponse.json();
    await save("entries", {
      releaseId: wine.releaseId,
      consumedDate: "2026-09-28",
      notes: "Second entry, plum",
    });
    await save(`me/wines/${wine.id}/rating`, { version: 0, score: 4.5 }, "PUT");
    return {
      wineId: wine.id as string,
      dinnerId: dinner.id as string,
      tastingId: tasting.id as string,
    };
  });
  const wineUrl = `/my-wines/${fixture.wineId}`;
  await page.goto(wineUrl);
  const entries = page.getByTestId("drinking-entry");
  await expect(entries).toHaveCount(2);
  for (let index = 0; index < 2; index++) {
    const row = entries.nth(index);
    await row.getByRole("button", { name: "Organize occasion" }).click();
    await row.getByLabel("Choose an occasion", { exact: true }).selectOption(fixture.dinnerId);
    await row.getByRole("button", { name: "Save occasion link" }).click();
    await expect(row.getByRole("link", { name: "View occasion", exact: true })).toHaveAttribute(
      "href",
      `/occasions/${fixture.dinnerId}`,
    );
  }
  await expect(page.getByTestId("current-rating")).toHaveText("4.5 / 5");
  const first = entries.first();
  await first.getByRole("button", { name: "Organize occasion" }).click();
  await first.getByLabel("Choose an occasion", { exact: true }).selectOption(fixture.tastingId);
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`organize-entry-${width}.png`),
      fullPage: true,
    });
  }
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()
    ).violations.map((issue) => issue.id),
  ).toEqual([]);
  page.once("dialog", (dialog) => dialog.dismiss());
  await first.getByRole("button", { name: "Save occasion link" }).click();
  await expect(first.getByRole("link", { name: "View occasion", exact: true })).toHaveAttribute(
    "href",
    `/occasions/${fixture.dinnerId}`,
  );
  page.once("dialog", (dialog) => dialog.accept());
  await first.getByRole("button", { name: "Save occasion link" }).click();
  await expect(first.getByRole("link", { name: "View occasion", exact: true })).toHaveAttribute(
    "href",
    `/occasions/${fixture.tastingId}`,
  );
  await first.getByRole("button", { name: "Organize occasion" }).click();
  await first.getByLabel("Choose an occasion", { exact: true }).selectOption("");
  let dropped = false;
  await page.route("**/api/v1/occasions/*/entries/*", async (route) => {
    if (route.request().method() === "DELETE" && !dropped) {
      dropped = true;
      expect((await route.fetch()).status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  page.once("dialog", (dialog) => dialog.accept());
  await first.getByRole("button", { name: "Save occasion link" }).click();
  await first.getByRole("button", { name: "Check saved entry" }).click();
  await first.getByRole("button", { name: "Keep current occasion" }).click();
  await expect(first.getByRole("link", { name: "View occasion", exact: true })).toHaveCount(0);
  await expect(first).toContainText("First entry, blackberry");
  const second = entries.nth(1);
  await second.getByRole("button", { name: "Organize occasion" }).click();
  await second.getByLabel("Choose an occasion", { exact: true }).selectOption(fixture.tastingId);
  const other = await context.newPage();
  await other.goto(wineUrl);
  const otherEntry = other.getByTestId("drinking-entry").nth(1);
  await otherEntry.getByRole("button", { name: "Edit entry", exact: true }).click();
  await otherEntry.getByLabel("Notes", { exact: true }).fill("Updated in another tab");
  await otherEntry.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(otherEntry.locator(".entry-notes")).toContainText("Updated in another tab");
  page.once("dialog", (dialog) => dialog.accept());
  await second.getByRole("button", { name: "Save occasion link" }).click();
  await expect(second.getByRole("heading", { name: "Review the latest entry" })).toBeVisible();
  await expect(second.locator(".edit-conflict")).toContainText("Updated in another tab");
  await expect(second.getByLabel("Choose an occasion", { exact: true })).toHaveValue(
    fixture.tastingId,
  );
  page.once("dialog", (dialog) => dialog.accept());
  await second.getByRole("button", { name: "Apply selection to latest entry" }).click();
  await expect(second.getByRole("link", { name: "View occasion", exact: true })).toHaveAttribute(
    "href",
    `/occasions/${fixture.tastingId}`,
  );
  await expect(second).toContainText("Updated in another tab");
  await expect(second).toContainText("September 28, 2026");
  await expect(entries).toHaveCount(2);
  await expect(page.getByTestId("current-rating")).toHaveText("4.5 / 5");
  await other.close();
  await second.getByRole("link", { name: "View occasion", exact: true }).click();
  await expect(page.locator(".occasion-wine-card")).toHaveCount(1);
  await expect(page.locator(".occasion-wine-card")).toContainText(
    "1 drinking entry at this occasion",
  );
  await page.goto(`/occasions/${fixture.dinnerId}`);
  await expect(page.getByText("No wines added yet.", { exact: true })).toBeVisible();
});
