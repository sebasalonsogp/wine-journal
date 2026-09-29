import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";

async function finishSignIn(page: Page, request: APIRequestContext) {
  const email = `journal-${crypto.randomUUID()}@example.test`;
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send me a code", exact: true }).click();
  let code = "";
  await expect
    .poll(
      async () => {
        const inbox = await (await request.get("http://127.0.0.1:54324/api/v1/messages")).json();
        const message = inbox.messages.find((item: { To: { Address: string }[] }) =>
          item.To.some((recipient) => recipient.Address === email),
        );
        if (!message) return false;
        const content = await (
          await request.get(`http://127.0.0.1:54324/api/v1/message/${message.ID}`)
        ).json();
        code = (content.Text || content.HTML).match(/\b\d{6}\b/)?.[0] ?? "";
        return code.length === 6;
      },
      { timeout: 15000, message: "Synthetic local email code received (contents withheld)" },
    )
    .toBe(true);
  try {
    await page.getByLabel("Verification code").fill(code);
  } catch {
    throw new Error("Could not enter code; value withheld.");
  }
  await page.getByRole("button", { name: "Open my journal" }).click();
}

test("guest draft survives sign-in; lost save response retries once; repeats persist under one wine", async ({
  page,
  request,
}, testInfo) => {
  await page.goto("/browse");
  await page.getByRole("link", { name: "Add wine manually" }).click();
  await page.getByLabel("Wine name", { exact: true }).fill("Calculated Risk Cabernet Sauvignon");
  await page.getByLabel("Vintage", { exact: true }).selectOption("YEAR");
  await page.getByLabel("Vintage year").fill("2021");
  await page.getByLabel("Date tried").fill("2026-09-12");
  await page.getByText("More label details", { exact: false }).click();
  await page.getByLabel("Producer", { exact: true }).fill("Calculated Risk");
  await page.getByLabel("Edition or release").fill("Reserve");
  await page.getByRole("button", { name: "Sign in to save" }).click();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue(
    "Calculated Risk Cabernet Sauvignon",
  );
  await expect(page.getByLabel("Date tried")).toHaveValue("2026-09-12");
  const keys: string[] = [];
  await page.route("**/api/v1/entries", async (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1 || keys.length === 3) {
      const saved = await route.fetch();
      expect(saved.status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry save", exact: true })).toBeEnabled();
  await expect(page.getByLabel("Wine name", { exact: true })).toBeDisabled();
  await page.reload();
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue(
    "Calculated Risk Cabernet Sauvignon",
  );
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page).toHaveURL(/\/my-wines\/[0-9a-f-]+$/);
  expect(keys.length).toBe(2);
  expect(keys[0] === keys[1]).toBe(true);
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await page.reload();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await page.getByRole("link", { name: "Log this wine again" }).click();
  await page.getByLabel("Date tried").fill("2026-09-12");
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry save", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(2);
  expect(keys[2] !== keys[1]).toBe(true);
  expect(keys[2] === keys[3]).toBe(true);
  await page.getByRole("link", { name: "Back to My wines" }).click();
  await expect(page.locator(".wine-card")).toHaveCount(1);
  await expect(page.locator(".wine-card")).toContainText("2 entries");
  await page.locator(".wine-card").click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(2);

  await mkdir(testInfo.outputPath("visuals"), { recursive: true });
  for (const route of ["detail", "list", "capture"]) {
    if (route === "list") await page.getByRole("link", { name: "Back to My wines" }).click();
    if (route === "capture")
      await page.getByRole("link", { name: "Log a wine", exact: true }).click();
    if (route === "list") {
      await expect(page).toHaveURL(/\/my-wines$/);
      await expect(page.locator(".wine-card")).toHaveCount(1);
    }
    for (const width of [390, 1440]) {
      await page.setViewportSize({ width, height: 950 });
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      if (route === "capture")
        await expect(page.getByLabel("Wine name", { exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
      await page.screenshot({
        path: testInfo.outputPath(`visuals/${route}-${width}.png`),
        fullPage: true,
      });
    }
    const audit = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(audit.violations.map((issue) => issue.id)).toEqual([]);
  }
});

test("validation keeps input; owned drafts stay hidden across expiry and clear for another account", async ({
  page,
  request,
  context,
}) => {
  await page.goto("/auth/sign-in?next=%2Fcapture");
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  await page.getByLabel("Wine name", { exact: true }).fill("   ");
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Check the wine and date" }),
  ).toBeVisible();
  await expect(page.getByLabel("Wine name", { exact: true })).toBeEnabled();
  await page.getByLabel("Wine name", { exact: true }).fill("Private unfinished wine");
  await page.reload();
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue(
    "Private unfinished wine",
  );
  await context.clearCookies();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your unfinished entry is private." }),
  ).toBeVisible();
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Sign in to continue", exact: true }).click();
  await finishSignIn(page, request);
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue("");
  await page.getByLabel("Wine name", { exact: true }).fill("Second account draft");
  const secondTab = await context.newPage();
  await secondTab.goto("/my-wines");
  await secondTab.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/browse$/);
  await page.goto("/capture");
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue("");
  expect(
    await page.evaluate(
      () =>
        Object.keys(sessionStorage).filter((key) => key.startsWith("wine-journal:draft:")).length,
    ),
  ).toBe(0);
  await secondTab.close();
});

test("wine cards and drinking history load subsequent real pages", async ({ page, request }) => {
  await page.goto("/auth/sign-in");
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/my-wines$/);
  await expect(page.getByRole("heading", { name: "My wines", exact: true })).toBeVisible();
  const wineId = await page.evaluate(async () => {
    const response = await fetch("/auth/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const session = await response.json();
    const headers = {
      Authorization: `Bearer ${session.accessToken}`,
      "Content-Type": "application/json",
    };
    let firstWine = "";
    const save = async (body: object) => {
      const result = await fetch(`${session.apiUrl}/api/v1/entries`, {
        method: "POST",
        headers: { ...headers, "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      });
      if (!result.ok)
        throw new Error(
          `Could not seed synthetic journal entries (${result.status}); response withheld.`,
        );
      return result.json();
    };
    for (let index = 0; index < 21; index++) {
      const saved = await save({
        consumedDate: "2026-09-01",
        manualWine: { name: `Pagination wine ${index}` },
      });
      if (!index) firstWine = saved.userWineId;
    }
    const wine = await (
      await fetch(`${session.apiUrl}/api/v1/me/wines/${firstWine}`, { headers })
    ).json();
    for (let index = 0; index < 20; index++)
      await save({ consumedDate: "2026-09-01", releaseId: wine.releaseId });
    return firstWine as string;
  });
  await page.reload();
  await expect(page.locator(".wine-card")).toHaveCount(20);
  await page.getByRole("button", { name: "Load more wines" }).click();
  await expect(page.locator(".wine-card")).toHaveCount(21);
  await expect(page.getByRole("button", { name: "Load more wines" })).toHaveCount(0);
  await page.goto(`/my-wines/${wineId}`);
  await expect(page.getByTestId("drinking-entry")).toHaveCount(20);
  await page.getByRole("button", { name: "Load more entries" }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(21);
  await expect(page.getByRole("button", { name: "Load more entries" })).toHaveCount(0);
});

test("entry edits survive reload, retain a stale draft, and require explicit conflict resolution", async ({
  page,
  request,
  context,
}, testInfo) => {
  await page.goto("/auth/sign-in?next=%2Fcapture");
  await finishSignIn(page, request);
  await page.getByLabel("Wine name", { exact: true }).fill("Editing example wine");
  let created: { id: string } = { id: "" };
  await page.route("**/api/v1/entries", async (route) => {
    const response = await route.fetch();
    created = await response.json();
    await route.fulfill({ response });
  });
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  const wineUrl = page.url();
  await page.getByRole("button", { name: "Edit entry", exact: true }).click();
  await page.getByLabel("Date tried", { exact: true }).fill("2026-01-01");
  await page.getByLabel("Local time", { exact: true }).fill("00:15");
  await page.getByLabel("Timezone", { exact: true }).fill("Pacific/Kiritimati");
  await page.getByLabel("Location", { exact: true }).fill("A friend's house");
  await page.getByLabel("Notes", { exact: true }).fill("My unfinished memory");
  await page.reload();
  await expect(page.getByLabel("Notes", { exact: true })).toHaveValue("My unfinished memory");

  const second = await context.newPage();
  await second.goto(wineUrl);
  await second.getByRole("button", { name: "Edit entry", exact: true }).click();
  await second.getByLabel("Notes", { exact: true }).fill("Newer saved memory");
  await second.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(second.getByTestId("drinking-entry")).toContainText("Newer saved memory");
  await page.bringToFront();
  await expect(page.getByLabel("Notes", { exact: true })).toHaveValue("My unfinished memory");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByRole("heading", { name: "This entry has changed" })).toBeVisible();
  await expect(page.locator(".edit-conflict")).toContainText("Newer saved memory");
  await expect(page.getByLabel("Notes", { exact: true })).toHaveValue("My unfinished memory");
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`edit-conflict-${width}.png`),
      fullPage: true,
    });
  }
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(audit.violations.map((issue) => issue.id)).toEqual([]);
  const changedResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/entries/${created.id}`) && response.request().method() === "PATCH",
  );
  await page
    .getByRole("button", { name: "Save my changes over this version", exact: true })
    .click();
  const changed = await (await changedResponse).json();
  expect(changed.id === created.id && changed.version === 3).toBe(true);
  await page.reload();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await expect(page.getByTestId("drinking-entry").locator("time")).toHaveAttribute(
    "datetime",
    "2026-01-01",
  );
  await expect(page.getByTestId("drinking-entry")).toContainText("00:15");
  await expect(page.getByTestId("drinking-entry")).toContainText("Pacific/Kiritimati");
  await expect(page.getByTestId("drinking-entry")).toContainText("My unfinished memory");
  await page.getByRole("button", { name: "Edit entry", exact: true }).click();
  await page.getByLabel("Local time", { exact: true }).fill("");
  await page.getByLabel("Location", { exact: true }).fill("");
  await page.getByLabel("Notes", { exact: true }).fill("");
  let interrupted = false;
  await page.route("**/api/v1/entries/*", async (route) => {
    if (route.request().method() === "PATCH" && !interrupted) {
      interrupted = true;
      expect((await route.fetch()).status()).toBe(200);
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "couldn’t confirm the update" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByRole("heading", { name: "This entry has changed" })).toBeVisible();
  await page.getByRole("button", { name: "Use latest saved entry", exact: true }).click();
  await expect(page.getByRole("button", { name: "Edit entry", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("drinking-entry")).not.toContainText("00:15");
  await expect(page.getByTestId("drinking-entry")).not.toContainText("My unfinished memory");
  await second.close();
});
