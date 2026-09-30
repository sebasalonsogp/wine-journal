import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";

test("inline occasion cancellation, auth, validation and lost-response retry keep one linked entry", async ({
  page,
  request,
}, testInfo) => {
  await page.goto("/capture");
  await page.getByLabel("Wine name", { exact: true }).fill("A dinner Cabernet");
  await page.getByLabel("Date tried").fill("2026-09-12");
  await page.getByLabel("Quick notes", { exact: false }).fill("Black cherry, soft finish");
  await page.getByRole("button", { name: "Create new occasion", exact: true }).click();
  await expect(page.getByLabel("Occasion date")).toHaveValue("2026-09-12");
  await page.getByLabel("Title", { exact: false }).fill("Cancelled occasion");
  await page.getByRole("button", { name: "Cancel new occasion" }).click();
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue("A dinner Cabernet");
  await expect(page.getByLabel("Quick notes", { exact: false })).toHaveValue(
    "Black cherry, soft finish",
  );
  await page.getByRole("button", { name: "Create new occasion", exact: true }).click();
  await page.getByLabel("Title", { exact: false }).fill("Dinner at Maya’s");
  await page.getByLabel("Occasion date").fill("2026-09-11");
  await page
    .getByRole("textbox", { name: "Notes optional", exact: true })
    .fill("Homemade pasta with friends");
  await page.getByRole("button", { name: "Sign in to save", exact: true }).click();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  await expect(page.getByLabel("Title", { exact: false })).toHaveValue("Dinner at Maya’s");
  await page.getByLabel("Local time", { exact: false }).fill("19:30");
  await page.getByLabel("Timezone", { exact: true }).fill("Invalid/Zone");
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Check the details" })).toBeVisible();
  await page.getByLabel("Timezone", { exact: true }).fill("America/New_York");
  await page.getByLabel("Location", { exact: false }).fill("Maya’s house");
  await page.reload();
  await expect(page.getByLabel("Quick notes", { exact: false })).toHaveValue(
    "Black cherry, soft finish",
  );
  await expect(page.getByRole("textbox", { name: "Notes optional", exact: true })).toHaveValue(
    "Homemade pasta with friends",
  );
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`inline-occasion-${width}.png`),
      fullPage: true,
    });
  }
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()
    ).violations.map((issue) => issue.id),
  ).toEqual([]);
  const keys: string[] = [];
  await page.route("**/api/v1/entries", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1) {
      expect((await route.fetch()).status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry save", exact: true })).toBeEnabled();
  await expect(page.getByLabel("Title", { exact: false })).toBeDisabled();
  await expect(page.getByLabel("Quick notes", { exact: false })).toBeDisabled();
  await page.reload();
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page).toHaveURL(/\/my-wines\/[0-9a-f-]+$/);
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await expect(page.getByTestId("drinking-entry")).toContainText("September 12, 2026");
  await expect(page.getByTestId("drinking-entry")).toContainText("Black cherry, soft finish");
  await page.getByRole("link", { name: "View occasion", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Dinner at Maya’s");
  await expect(page.locator(".occasion-heading")).toContainText("September 11, 2026");
  await expect(page.locator(".occasion-notes")).toContainText("Homemade pasta with friends");
  await page.getByRole("link", { name: "Back to Occasions", exact: true }).click();
  await expect(page.locator(".occasion-card")).toHaveCount(1);
});

test("existing occasions paginate and recover while navigation keeps the wine draft", async ({
  page,
  request,
}) => {
  await page.goto("/auth/sign-in?next=%2Fcapture");
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  await expect(page.getByLabel("Wine name", { exact: true })).toBeVisible();
  const lastId = await page.evaluate(async () => {
    const session = await (
      await fetch("/auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      })
    ).json();
    let id = "";
    for (let index = 0; index < 21; index++) {
      const response = await fetch(`${session.apiUrl}/api/v1/occasions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify({
          occasionDate: `2026-09-${String(30 - index).padStart(2, "0")}`,
          title: `Dinner ${index}`,
        }),
      });
      if (!response.ok)
        throw new Error(`Synthetic occasion setup failed (${response.status}); response withheld.`);
      id = (await response.json()).id;
    }
    return id as string;
  });
  await page.getByLabel("Wine name", { exact: true }).fill("A shared white");
  await page.getByLabel("Date tried").fill("2026-09-29");
  await page.getByLabel("Quick notes", { exact: false }).fill("Keep this entry note");
  let failed = false;
  await page.route("**/api/v1/occasions?*", async (route) => {
    if (!failed) {
      failed = true;
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Choose existing occasion" }).click();
  await page.getByRole("button", { name: "Try loading occasions again" }).click();
  await expect(page.locator("#existing-occasion option")).toHaveCount(21);
  await page.getByRole("button", { name: "Load more occasions" }).click();
  await expect(page.locator("#existing-occasion option")).toHaveCount(22);
  await page.getByLabel("Choose an occasion", { exact: true }).selectOption(lastId);
  await page.getByRole("link", { name: "Back to My wines", exact: true }).click();
  await expect(page).toHaveURL(/\/my-wines$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/capture$/);
  await expect(page.getByLabel("Choose an occasion", { exact: true })).toHaveValue(lastId);
  await expect(page.getByLabel("Date tried")).toHaveValue("2026-09-29");
  await expect(page.getByLabel("Quick notes", { exact: false })).toHaveValue(
    "Keep this entry note",
  );
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page).toHaveURL(/\/my-wines\/[0-9a-f-]+$/);
  await expect(page.getByRole("link", { name: "View occasion", exact: true })).toHaveAttribute(
    "href",
    `/occasions/${lastId}`,
  );
  await page.getByRole("link", { name: "Log this wine again", exact: true }).click();
  await page.getByRole("button", { name: "Choose existing occasion" }).click();
  await expect(page.locator("#existing-occasion option")).toHaveCount(21);
  await page.getByRole("button", { name: "Keep without an occasion" }).click();
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(2);
  await expect(page.getByRole("link", { name: "View occasion", exact: true })).toHaveCount(1);
});
