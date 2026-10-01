import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";

test("occasion deletion confirms, reviews stale context and retains wines after a lost response", async ({
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
    async function call(path: string, method = "GET", body?: object) {
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
          `Synthetic deletion fixture failed (${response.status}); response withheld.`,
        );
      return response.json();
    }
    const occasion = await call("occasions", "POST", {
      title: "Dinner to organize",
      occasionDate: "2026-09-29",
      locationLabel: "A friend's house",
      notes: "General dinner note",
      wines: ["Cabernet", "Chardonnay", "Rose"].map((name, index) => ({
        manualWine: { name },
        entries: [
          { consumedDate: "2026-09-28", notes: `Keep ${name} notes` },
          ...(index === 0 ? [{ consumedDate: "2026-09-27", notes: "Keep the second glass" }] : []),
        ],
      })),
    });
    const wines = (await call(`occasions/${occasion.id}/wines`)).items;
    const red = wines.find((wine: { name: string }) => wine.name === "Cabernet");
    await call(`me/wines/${red.id}/rating`, "PUT", { version: 0, score: 4.5 });
    return { occasionId: occasion.id as string, wineId: red.id as string };
  });
  const occasionUrl = `/occasions/${fixture.occasionId}`;
  await page.goto(occasionUrl);
  await expect(page.locator(".occasion-wine-card")).toHaveCount(3);
  await expect(page.locator(".occasion-wine-card").filter({ hasText: "Cabernet" })).toContainText(
    "2 drinking entries",
  );
  await page.getByRole("button", { name: "Delete occasion", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Delete this occasion?" });
  await expect(dialog.getByRole("button", { name: "Keep occasion" })).toBeFocused();
  await expect(dialog).toContainText("All saved drinking entries");
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`occasion-delete-${width}.png`),
      fullPage: true,
    });
    const audit = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(audit.violations.map((issue) => issue.id)).toEqual([]);
  }
  await dialog.getByRole("button", { name: "Keep occasion" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Delete occasion", exact: true })).toBeFocused();
  await page.getByRole("button", { name: "Delete occasion", exact: true }).click();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await page.getByRole("button", { name: "Delete occasion", exact: true }).click();
  const other = await context.newPage();
  await other.goto(occasionUrl);
  await other.getByRole("button", { name: "Edit occasion", exact: true }).click();
  await other.getByLabel("Title", { exact: false }).fill("Dinner revised in another tab");
  await other.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(other.getByRole("heading", { name: "Dinner revised in another tab" })).toBeVisible();
  await dialog.getByRole("button", { name: "Delete this occasion", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Remove occasion" }).getByRole("alert"),
  ).toContainText("Review the saved details");
  await expect(page.getByRole("heading", { name: "Dinner revised in another tab" })).toBeVisible();
  await other.close();
  // An unsaved edit is explicitly discarded with its deleted parent.
  await page.getByRole("button", { name: "Edit occasion", exact: true }).click();
  await page.getByLabel("Title", { exact: false }).fill("Unsubmitted title");
  await page.getByRole("button", { name: "Delete occasion", exact: true }).click();
  await expect(dialog).toContainText("Dinner revised in another tab");
  const versions: string[] = [];
  await page.route(`**/api/v1/occasions/${fixture.occasionId}?*`, async (route) => {
    if (route.request().method() !== "DELETE") return route.continue();
    versions.push(new URL(route.request().url()).searchParams.get("version")!);
    if (versions.length === 1) {
      expect((await route.fetch()).status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await dialog.getByRole("button", { name: "Delete this occasion", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("We couldn’t confirm the deletion");
  await dialog.getByRole("button", { name: "Delete this occasion", exact: true }).click();
  await expect(page).toHaveURL(/\/occasions$/);
  expect(versions).toEqual(["2", "2"]);
  await expect(page.getByRole("heading", { name: "A place for the moments." })).toBeVisible();
  expect(
    await page.evaluate(
      (id) => Object.keys(sessionStorage).some((key) => key.includes(id)),
      fixture.occasionId,
    ),
  ).toBe(false);
  await page.goto(`/my-wines/${fixture.wineId}`);
  await expect(page.getByTestId("drinking-entry")).toHaveCount(2);
  await expect(page.getByTestId("current-rating")).toHaveText("4.5 / 5");
  await expect(page.getByText("Keep Cabernet notes", { exact: true })).toBeVisible();
  await expect(page.getByText("Keep the second glass", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "View occasion", exact: true })).toHaveCount(0);
  await page.goto("/my-wines");
  await expect(page.locator(".wine-card")).toHaveCount(3);
  await page.goto(occasionUrl);
  await expect(page.getByRole("button", { name: "Delete occasion", exact: true })).toHaveCount(0);
});
