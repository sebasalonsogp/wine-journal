import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { photo, processPhoto } from "./photo-fixtures";
import { finishSignIn } from "./journal-auth";

test("phone capture saves text through photo failure, retries once, reloads captions and removes memories", async ({
  page,
  request,
}, testInfo) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 390, height: 1000 });
  await page.goto("/auth/sign-in?next=%2Fcapture");
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  await page.getByLabel("Wine name", { exact: true }).fill("Photo journal test wine");
  await page.getByLabel("Quick notes").fill("Text is saved even when the photo fails.");
  await page.getByLabel("Add photos", { exact: true }).setInputFiles(photo);
  await expect(page.getByTestId("photo-selection")).toContainText("uploads after you save");
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
  await expect(page.getByRole("button", { name: "Retry photo" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("photo-failure-390.png"), fullPage: true });
  await page.unroute("**/storage/v1/object/upload/sign/**");
  const completed = page.waitForResponse(
    (response) => response.url().endsWith("/complete") && response.status() === 200,
  );
  await page.getByRole("button", { name: "Retry photo" }).click();
  await completed;
  processPhoto();
  await expect(page.getByTestId("entry-photo").locator("img")).toBeVisible({ timeout: 25000 });
  expect(
    await page
      .getByTestId("entry-photo")
      .locator("img")
      .evaluate((node: HTMLImageElement) => node.naturalWidth > 0),
  ).toBe(true);
  expect(entries).toBe(1);
  await page.getByLabel("Photo caption").fill("A memorable dinner");
  await page.getByRole("button", { name: "Save caption", exact: true }).click();
  await expect(page.getByRole("button", { name: "Save caption", exact: true })).toBeDisabled();
  await page.getByRole("link", { name: "View wine", exact: true }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await expect(page.getByTestId("drinking-entry")).toContainText(
    "Text is saved even when the photo fails.",
  );
  await page.getByText("Photos & memories", { exact: true }).click();
  await expect(page.getByLabel("Photo caption")).toHaveValue("A memorable dinner");
  await page.reload();
  await page.getByText("Photos & memories", { exact: true }).click();
  await expect(page.getByTestId("entry-photo").locator("img")).toBeVisible();
  await expect(page.getByLabel("Photo caption")).toHaveValue("A memorable dinner");
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`photo-gallery-${width}.png`),
      fullPage: true,
    });
  }
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()
    ).violations.map((item) => item.id),
  ).toEqual([]);
  // Focus rechecks must not discard a caption draft or remount an active upload.
  await page.getByLabel("Photo caption").fill("Unsaved caption survives focus");
  await page.evaluate(() => {
    document.dispatchEvent(new Event("visibilitychange"));
    window.dispatchEvent(new Event("focus"));
  });
  await expect(page.getByLabel("Photo caption")).toHaveValue("Unsaved caption survives focus");
  await page.getByRole("button", { name: "Use saved caption" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Remove photo", exact: true }).click();
  await expect(page.getByTestId("entry-photo")).toHaveCount(0);
  await page.reload();
  await page.getByText("Photos & memories", { exact: true }).click();
  await expect(page.getByTestId("entry-photo")).toHaveCount(0);
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  expect(entries).toBe(1);
});

test("existing entries show rejected photos, keep selections across focus, and clear them on cross-tab sign-out", async ({
  page,
  request,
  context,
}) => {
  test.setTimeout(120000);
  await page.goto("/auth/sign-in?next=%2Fcapture");
  await finishSignIn(page, request);
  await page.getByLabel("Wine name", { exact: true }).fill("Later memories");
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await page.getByText("Photos & memories", { exact: true }).click();
  const complete = page.waitForResponse(
    (response) => response.url().endsWith("/complete") && response.status() === 200,
  );
  await page.getByLabel("Add photos", { exact: true }).setInputFiles({
    name: "invalid.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("invalid image fixture"),
  });
  await complete;
  processPhoto();
  await expect(page.getByTestId("entry-photo")).toContainText("couldn’t be processed", {
    timeout: 25000,
  });
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Remove photo", exact: true }).click();
  await expect(page.getByTestId("entry-photo")).toHaveCount(0);
  await page.route("**/storage/v1/object/upload/sign/**", async (route) => {
    if (route.request().method() === "PUT") await route.abort("internetdisconnected");
    else await route.continue();
  });
  let reservations = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/media/uploads")) reservations++;
  });
  await page.getByLabel("Add photos", { exact: true }).setInputFiles(photo);
  await expect(page.getByRole("button", { name: "Retry photo" })).toBeVisible();
  const other = await context.newPage();
  await other.goto("/my-wines");
  await expect(other.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
  const recheck = page.waitForResponse(
    (response) => response.url().endsWith("/api/v1/me") && response.request().method() === "GET",
  );
  await page.bringToFront();
  // Headless tab activation does not reliably emit visibilitychange. Drive the
  // real browser event consumed by Query's focus manager, without touching app state.
  await page.evaluate(() => {
    const descriptor = Object.getOwnPropertyDescriptor(document, "visibilityState");
    for (const state of ["hidden", "visible"]) {
      Object.defineProperty(document, "visibilityState", { configurable: true, get: () => state });
      window.dispatchEvent(new Event("visibilitychange"));
    }
    if (descriptor) Object.defineProperty(document, "visibilityState", descriptor);
    else Reflect.deleteProperty(document, "visibilityState");
  });
  await recheck;
  await expect(page.getByRole("button", { name: "Retry photo" })).toBeVisible();
  expect(reservations).toBe(1);
  let blockedSignOut = false;
  page.on("dialog", async (dialog) => {
    blockedSignOut = true;
    await dialog.dismiss();
  });
  await other.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  await expect(page.getByTestId("photo-selection")).toHaveCount(0);
  expect(blockedSignOut).toBe(false);
  await other.close();
});
