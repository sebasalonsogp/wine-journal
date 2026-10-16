import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";
import { photo, processPhoto } from "./photo-fixtures";

// Synthetic local fixture operations; credentials remain inside the browser.
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
        throw new Error(`Synthetic album fixture failed (${response.status}); contents withheld.`);
      const data = await response.json();
      // Do not return upload capabilities or auth values to the test runner.
      if (path === "media/uploads") return { assetId: data.assetId };
      return data;
    },
    { path, method, body },
  );
}

test("occasion album retries uploads, preserves sources through unlink/deletion and supports private captions", async ({
  page,
  request,
  context,
}, testInfo) => {
  test.setTimeout(180000);
  await page.goto("/auth/sign-in?next=%2Foccasions%2Fnew");
  await finishSignIn(page, request);
  await page.getByLabel("Title", { exact: false }).fill("An evening around the table");
  await page.getByRole("button", { name: "Create occasion", exact: true }).click();
  await expect(page).toHaveURL(/\/occasions\/[0-9a-f-]+$/);
  const occasionUrl = page.url();
  const occasionId = occasionUrl.split("/").at(-1)!;
  await expect(
    page.getByText("The table, the people, the little details.", { exact: false }),
  ).toBeVisible();
  let occasionSaves = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/v1/occasions")) occasionSaves++;
  });
  await page.route("**/storage/v1/object/upload/sign/**", async (route) => {
    if (route.request().method() === "PUT") await route.abort("internetdisconnected");
    else await route.continue();
  });
  await page.getByLabel("Add occasion photos").setInputFiles(photo);
  await expect(page.getByRole("button", { name: "Retry photo" })).toBeVisible();
  await page.unroute("**/storage/v1/object/upload/sign/**");
  const completed = page.waitForResponse(
    (response) => response.url().endsWith("/complete") && response.status() === 200,
  );
  await page.getByRole("button", { name: "Retry photo" }).click();
  await completed;
  processPhoto();
  await expect(page.getByTestId("occasion-photo").locator("img")).toBeVisible({ timeout: 25000 });
  expect(occasionSaves).toBe(0);
  const shared = (await journal(page, `occasions/${occasionId}/album`)).items[0].assetId;
  await page.getByLabel("Photo caption").fill("A long dinner with good company");
  await page.getByRole("button", { name: "Save caption", exact: true }).click();
  await expect(page.getByRole("button", { name: "Save caption", exact: true })).toBeDisabled();
  const other = await context.newPage();
  await other.goto(occasionUrl);
  await other.getByLabel("Photo caption").fill("A stale draft to preserve");
  await page.getByLabel("Photo caption").fill("A table worth remembering");
  await page.getByRole("button", { name: "Save caption", exact: true }).click();
  await expect(page.getByRole("button", { name: "Save caption", exact: true })).toBeDisabled();
  await other.getByRole("button", { name: "Save caption", exact: true }).click();
  await expect(other.getByTestId("occasion-photo").getByRole("alert")).toContainText(
    "changed elsewhere",
  );
  await other.getByRole("button", { name: "Reload album" }).click();
  await expect(other.getByLabel("Photo caption")).toHaveValue("A stale draft to preserve");
  await other.getByRole("button", { name: "Use saved caption" }).click();
  await expect(other.getByLabel("Photo caption")).toHaveValue("A table worth remembering");
  await other.close();

  const entryIds: string[] = [];
  let wineId = "";
  for (const name of ["Evening Cabernet", "Evening Syrah", "Unlinked glass"]) {
    const entry = await journal(page, "entries", "POST", {
      consumedDate: "2026-10-12",
      manualWine: { name },
      ...(name !== "Unlinked glass" ? { occasionId } : {}),
    });
    entryIds.push(entry.id);
    if (!wineId) wineId = entry.userWineId;
  }
  for (const entryId of entryIds.slice(0, 2))
    await journal(page, `entries/${entryId}/photos/${shared}`, "PUT", {});
  await journal(page, `entries/${entryIds[0]}/photos/${shared}`, "PATCH", {
    version: 1,
    caption: "Cabernet at the table",
  });
  const standalone = await journal(page, "media/uploads", "POST", {
    contentType: "image/png",
    sizeBytes: photo.buffer.length,
  });
  await journal(page, `entries/${entryIds[2]}/photos/${standalone.assetId}`, "PUT", {});
  // A second ready asset arrives through the normal occasion upload flow.
  await page
    .getByLabel("Add occasion photos")
    .setInputFiles({ ...photo, name: "another-memory.png" });
  await expect(page.getByTestId("photo-selection")).toHaveCount(0, { timeout: 25000 });
  processPhoto();
  await expect(page.getByTestId("occasion-photo").locator("img")).toHaveCount(2, {
    timeout: 25000,
  });
  await page.getByRole("button", { name: "Reload album" }).click();
  await expect(page.getByText("Photo sources (3)")).toBeVisible();
  expect((await journal(page, `occasions/${occasionId}/album`)).items).toHaveLength(2);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page
      .locator(".occasion-album")
      .screenshot({ path: testInfo.outputPath(`occasion-album-${width}.png`) });
  }
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()
    ).violations.map((issue) => issue.id),
  ).toEqual([]);
  // Exercise the real paginated contract with small pages, without manufacturing extra assets.
  await page.route("**/api/v1/occasions/*/album**", async (route) => {
    const url = new URL(route.request().url());
    url.searchParams.set("limit", "1");
    await route.continue({ url: url.toString() });
  });
  await page.reload();
  await expect(page.getByTestId("occasion-photo")).toHaveCount(1);
  await page.getByRole("button", { name: "Load more memories" }).click();
  await expect(page.getByTestId("occasion-photo")).toHaveCount(2);
  const sharedCard = page.getByTestId("occasion-photo").filter({ hasText: "Photo sources (3)" });
  await sharedCard.getByText("Photo sources (3)").click();
  await sharedCard.getByRole("button", { name: "Load more sources" }).click();
  await sharedCard.getByRole("button", { name: "Load more sources" }).click();
  await expect(sharedCard.getByRole("link", { name: "Open wine & drinking history" })).toHaveCount(
    2,
  );
  await expect(sharedCard).toContainText("Cabernet at the table");
  page.once("dialog", (dialog) => dialog.accept());
  await sharedCard.getByRole("button", { name: "Remove photo", exact: true }).click();
  await expect(page.getByTestId("inherited-photo")).toHaveCount(1);
  await expect(
    page.getByTestId("inherited-photo").getByRole("button", { name: "Remove photo" }),
  ).toHaveCount(0);
  await expect(
    page
      .getByTestId("inherited-photo")
      .getByRole("link", { name: "From a wine entry · View wine" }),
  ).toHaveAttribute("href", /\/my-wines\//);
  for (const entryId of entryIds.slice(0, 2))
    await journal(page, `occasions/${occasionId}/entries/${entryId}?version=1`, "DELETE");
  await page.getByRole("button", { name: "Reload album" }).click();
  await expect(page.getByTestId("inherited-photo")).toHaveCount(0);
  await expect(page.getByTestId("occasion-photo")).toHaveCount(1);
  await journal(page, `occasions/${occasionId}?version=1`, "DELETE");
  await page.goto(`/my-wines/${wineId}`);
  await page.getByText("Photos & memories", { exact: true }).click();
  await expect(page.getByTestId("entry-photo").locator("img")).toBeVisible();
  await expect(page.getByLabel("Photo caption")).toHaveValue("Cabernet at the table");
  expect((await journal(page, `entries/${entryIds[2]}/photos`)).items).toHaveLength(1);
  // A source link remains precise after its entry falls beyond the first history page.
  const wine = await journal(page, `me/wines/${wineId}`);
  for (let index = 0; index < 21; index++)
    await journal(page, "entries", "POST", {
      consumedDate: "2026-10-13",
      releaseId: wine.releaseId,
    });
  await page.goto(`/my-wines/${wineId}?entry=${entryIds[0]}#history-title`);
  await expect(page.getByRole("heading", { name: "This photo’s drinking entry" })).toBeVisible();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await page.getByText("Photos & memories", { exact: true }).click();
  await expect(page.getByLabel("Photo caption")).toHaveValue("Cabernet at the table");
  await page.getByRole("link", { name: "Show all drinking history" }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(20);
  await page.goto(`/my-wines/${wineId}?entry=${entryIds[1]}`);
  await expect(page.getByText("This drinking entry is unavailable for this wine.")).toBeVisible();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(0);
});

test("wine highlights show eligible memories, paginate and link to their original context", async ({
  page,
  request,
}, testInfo) => {
  test.setTimeout(180000);
  await page.goto("/auth/sign-in?next=%2Foccasions%2Fnew");
  await finishSignIn(page, request);
  await expect(page.getByRole("button", { name: "Create occasion", exact: true })).toBeVisible();
  const occasion = await journal(page, "occasions", "POST", {
    occasionDate: "2026-10-12",
    title: "Autumn dinner",
  });
  const own = await journal(page, "entries", "POST", {
    consumedDate: "2026-10-15",
    manualWine: { name: "Autumn Cabernet" },
    occasionId: occasion.id,
  });
  const other = await journal(page, "entries", "POST", {
    consumedDate: "2026-10-13",
    manualWine: { name: "Dinner Syrah" },
    occasionId: occasion.id,
  });
  const wineUrl = `/my-wines/${own.userWineId}`;
  await page.goto(wineUrl);
  await expect(page.getByRole("heading", { name: "Autumn Cabernet", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Moments with this wine" })).toHaveCount(0);
  await page.goto(`/occasions/${occasion.id}`);
  for (let index = 0; index < 3; index++) {
    await page.getByLabel("Add occasion photos").setInputFiles({
      ...photo,
      name: `autumn-${index}.png`,
    });
    await expect(page.getByTestId("photo-selection")).toHaveCount(0, { timeout: 25000 });
    processPhoto();
    await expect(page.getByTestId("occasion-photo").locator("img")).toHaveCount(index + 1, {
      timeout: 25000,
    });
  }
  const [shared, ownPhoto, otherPhoto] = (
    await journal(page, `occasions/${occasion.id}/album`)
  ).items.map((item: { assetId: string }) => item.assetId);
  for (const [entry, asset, caption] of [
    [own.id, shared, "A glass shared with friends"],
    [own.id, ownPhoto, "Cabernet at dinner"],
    [other.id, otherPhoto, "Only the Syrah"],
  ]) {
    await journal(page, `entries/${entry}/photos/${asset}`, "PUT", {});
    await journal(page, `entries/${entry}/photos/${asset}`, "PATCH", { version: 1, caption });
  }
  for (const asset of [ownPhoto, otherPhoto])
    await journal(page, `occasions/${occasion.id}/photos/${asset}?version=1`, "DELETE");
  await page.goto(wineUrl);
  const moments = page.getByRole("region", { name: "Moments with this wine" });
  await expect(moments.getByTestId("wine-moment")).toHaveCount(2);
  await expect(moments).not.toContainText("Only the Syrah");
  // Add an explicit general reference on another occasion with this wine.
  // Removed references are tombstones; a delayed retry must not resurrect them.
  const secondOccasion = await journal(page, "occasions", "POST", {
    occasionDate: "2026-10-10",
    title: "Another shared table",
  });
  const wine = await journal(page, `me/wines/${own.userWineId}`);
  await journal(page, "entries", "POST", {
    consumedDate: "2026-10-10",
    releaseId: wine.releaseId,
    occasionId: secondOccasion.id,
  });
  await journal(page, `occasions/${secondOccasion.id}/photos/${otherPhoto}`, "PUT", {});
  await page.getByRole("button", { name: "Reload memories" }).click();
  await expect(moments.getByTestId("wine-moment").locator("img")).toHaveCount(3);
  await expect(moments.getByRole("link", { name: "Open drinking entry" })).toHaveCount(2);
  await expect(moments.getByRole("link", { name: "Open occasion" })).toHaveAttribute(
    "href",
    `/occasions/${secondOccasion.id}`,
  );
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await moments.screenshot({ path: testInfo.outputPath(`wine-moments-${width}.png`) });
  }
  expect(
    (
      await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()
    ).violations.map((issue) => issue.id),
  ).toEqual([]);
  await moments.getByRole("link", { name: "Open drinking entry" }).first().click();
  await expect(page).toHaveURL(new RegExp(`entry=${own.id}#history-title$`));
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await page.getByRole("link", { name: "Show all drinking history" }).click();
  // Real keyset pagination, with smaller server pages to keep the upload fixture bounded.
  await page.route("**/api/v1/me/wines/*/moments**", async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("limit") === "20") url.searchParams.set("limit", "1");
    await route.continue({ url: url.toString() });
  });
  await page.getByRole("link", { name: "View all memories" }).click();
  await expect(moments.getByTestId("wine-moment")).toHaveCount(1);
  await page.getByRole("button", { name: "Load more memories" }).click();
  await expect(moments.getByTestId("wine-moment")).toHaveCount(2);
  await page.getByRole("button", { name: "Load more memories" }).click();
  await expect(moments.getByTestId("wine-moment")).toHaveCount(3);
  await expect(page.getByRole("button", { name: "Load more memories" })).toHaveCount(0);
  await page.getByRole("link", { name: "Show highlights" }).click();
  await expect(moments.getByTestId("wine-moment")).toHaveCount(3);
  await page.unroute("**/api/v1/me/wines/*/moments**");
  await page.route("**/api/v1/me/wines/*/moments**", (route) =>
    route.abort("internetdisconnected"),
  );
  await page.getByRole("button", { name: "Reload memories" }).click();
  await expect(moments.getByRole("alert")).toBeVisible();
  await page.unroute("**/api/v1/me/wines/*/moments**");
  await page.getByRole("button", { name: "Reload memories" }).click();
  await expect(moments.getByTestId("wine-moment")).toHaveCount(3);
  await page
    .getByTestId("drinking-entry")
    .first()
    .getByRole("button", { name: "Delete entry", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete this entry", exact: true })
    .click();
  await expect(moments.getByTestId("wine-moment")).toHaveCount(1);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/browse$/);
  await expect(page.getByTestId("wine-moment")).toHaveCount(0);
  await page.goto(wineUrl);
  await expect(page.getByTestId("wine-moment")).toHaveCount(0);
});

test("occasion selections guard navigation but clear on sign-out", async ({ page, request }) => {
  await page.goto("/auth/sign-in?next=%2Foccasions%2Fnew");
  await finishSignIn(page, request);
  await page.getByRole("button", { name: "Create occasion", exact: true }).click();
  await expect(page).toHaveURL(/\/occasions\/[0-9a-f-]+$/);
  await page.route("**/api/v1/media/uploads", (route) => route.abort("internetdisconnected"));
  await page.getByLabel("Add occasion photos").setInputFiles(photo);
  await expect(page.getByRole("button", { name: "Retry photo" })).toBeVisible();
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("link", { name: "Back to Occasions" }).click();
  await expect(page.getByTestId("photo-selection")).toHaveCount(1);
  let dialogs = 0;
  page.on("dialog", async (dialog) => {
    dialogs++;
    await dialog.dismiss();
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/browse$/);
  expect(dialogs).toBe(0);
  await expect(page.getByTestId("photo-selection")).toHaveCount(0);
});
