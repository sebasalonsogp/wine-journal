import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";
import { photo, processPhoto } from "./photo-fixtures";

test("unsaved bottle selection preserves manual fields and clears on cross-tab sign-out", async ({
  page,
  request,
  context,
}) => {
  await page.goto("/auth/sign-in?next=%2Fcapture");
  await finishSignIn(page, request);
  await page.getByLabel("Wine name", { exact: true }).fill("An unfinished manual wine");
  await page.getByLabel("Choose bottle cover", { exact: true }).setInputFiles({
    name: "wrong.svg",
    mimeType: "image/svg+xml",
    buffer: Buffer.from("unsupported fixture"),
  });
  await expect(page.locator(".cover-editor").getByRole("alert")).toContainText("Choose a JPEG");
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue(
    "An unfinished manual wine",
  );
  await page.getByLabel("Choose bottle cover", { exact: true }).setInputFiles(photo);
  await page.getByLabel("Add photos", { exact: true }).setInputFiles(photo);
  let leavePrompts = 0;
  const acceptLeave = async (dialog: import("@playwright/test").Dialog) => {
    leavePrompts++;
    await dialog.accept();
  };
  page.on("dialog", acceptLeave);
  await page.getByRole("link", { name: "Browse wines", exact: true }).click();
  await expect(page).toHaveURL(/\/browse$/);
  expect(leavePrompts).toBe(1);
  page.off("dialog", acceptLeave);
  await page.goto("/capture");
  await expect(page.getByLabel("Wine name", { exact: true })).toHaveValue(
    "An unfinished manual wine",
  );
  await page.getByLabel("Choose bottle cover", { exact: true }).setInputFiles(photo);
  let blockedSignOut = false;
  page.on("dialog", async (dialog) => {
    blockedSignOut = true;
    await dialog.dismiss();
  });
  const other = await context.newPage();
  await other.goto("/my-wines");
  await other.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/browse$/);
  await expect(page.locator(".cover-editor")).toHaveCount(0);
  expect(blockedSignOut).toBe(false);
  await other.close();
});

test("personal cover survives retry, replaces independently and never becomes a memory", async ({
  page,
  request,
  context,
}, testInfo) => {
  test.setTimeout(150000);
  await page.setViewportSize({ width: 390, height: 1000 });
  await page.goto("/auth/sign-in?next=%2Fcapture");
  await finishSignIn(page, request);
  await page.getByLabel("Wine name", { exact: true }).fill("Personal cover wine");
  await page.getByLabel("Quick notes").fill("Cover changes keep this entry.");
  await page.getByLabel("Choose bottle cover", { exact: true }).setInputFiles(photo);
  await expect(
    page.getByText("Selected — uploads after you save the entry.", { exact: true }),
  ).toBeVisible();
  let entries = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/v1/entries")) entries++;
  });
  await page.route("**/storage/v1/object/upload/sign/**", async (route) => {
    if (route.request().method() === "PUT") await route.abort("internetdisconnected");
    else await route.continue();
  });
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your entry is saved." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry cover", exact: true })).toBeVisible();
  await page.unroute("**/storage/v1/object/upload/sign/**");
  const completed = page.waitForResponse(
    (r) => r.url().endsWith("/complete") && r.status() === 200,
  );
  await page.getByRole("button", { name: "Retry cover", exact: true }).click();
  await completed;
  processPhoto();
  await expect(page.getByText("Bottle cover saved.", { exact: true })).toBeVisible({
    timeout: 25000,
  });
  await expect(page.locator(".cover-editor img")).toBeVisible();
  expect(entries).toBe(1);
  await page.getByRole("link", { name: "View wine", exact: true }).click();
  await expect(page.locator(".wine-record img")).toBeVisible();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await page.getByText("Photos & memories", { exact: true }).click();
  await expect(page.getByTestId("entry-photo")).toHaveCount(0);
  await page.getByText("Manage bottle cover", { exact: true }).click();
  await expect(page.getByLabel("Replace bottle cover", { exact: true })).toBeEnabled();
  const stale = await context.newPage();
  await stale.goto(page.url());
  await stale.getByText("Manage bottle cover", { exact: true }).click();
  await expect(stale.getByRole("button", { name: "Remove cover", exact: true })).toBeVisible();
  const replaced = page.waitForResponse((r) => r.url().endsWith("/complete") && r.status() === 200);
  await page
    .getByLabel("Replace bottle cover", { exact: true })
    .setInputFiles({ ...photo, name: "new-bottle.png" });
  await replaced;
  processPhoto();
  await expect(page.getByText("Bottle cover saved.", { exact: true })).toBeVisible({
    timeout: 25000,
  });
  stale.once("dialog", (dialog) => dialog.accept());
  await stale.getByRole("button", { name: "Remove cover", exact: true }).click();
  await expect(stale.locator(".cover-editor").getByRole("alert")).toContainText(
    "could not be removed",
  );
  await stale.close();
  const rejected = page.waitForResponse((r) => r.url().endsWith("/complete") && r.status() === 200);
  await page.getByLabel("Replace bottle cover", { exact: true }).setInputFiles({
    name: "invalid-cover.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("invalid image fixture"),
  });
  await rejected;
  processPhoto();
  await expect(page.locator(".cover-editor").getByRole("alert")).toContainText(
    "couldn’t be processed",
    { timeout: 25000 },
  );
  await expect(page.locator(".wine-record img")).toBeVisible();
  await page.getByRole("button", { name: "Discard cover selection", exact: true }).click();
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`bottle-cover-${width}.png`),
      fullPage: true,
    });
  }
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()
    ).violations.map((v) => v.id),
  ).toEqual([]);
  await page.getByRole("link", { name: "Back to My wines" }).click();
  await expect(page.locator(".wine-card img")).toBeVisible();
  await page.getByRole("link", { name: /Personal cover wine/ }).click();
  await page.getByText("Manage bottle cover", { exact: true }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Remove cover", exact: true }).click();
  await expect(page.getByText("Personal cover removed.", { exact: true })).toBeVisible();
  await expect(page.locator(".wine-record img")).toHaveCount(0);
  await page.reload();
  await expect(page.locator(".wine-record img")).toHaveCount(0);
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await expect(page.getByTestId("drinking-entry")).toContainText("Cover changes keep this entry.");
  await page.getByText("Photos & memories", { exact: true }).click();
  await expect(page.getByTestId("entry-photo")).toHaveCount(0);
  expect(entries).toBe(1);
});
