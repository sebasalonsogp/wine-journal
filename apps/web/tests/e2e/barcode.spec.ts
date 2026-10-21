import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";

const lookup = "**/api/v1/identification/barcode-lookups";
const confirmation = "**/api/v1/identification/barcode-confirmations";
async function openLookup(page: Page) {
  await page.goto("/browse");
  await page.getByText("Look up a barcode", { exact: true }).click();
  await page.getByLabel("Barcode number").fill("089121288122");
  await page.getByRole("button", { name: "Look up bottle", exact: true }).click();
}

test("guest barcode lookup requires the bottle vintage before details and deliberate journal save", async ({
  page,
  request,
}, testInfo) => {
  let writes = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/v1/entries")) writes++;
    if (request.url().includes("/api/v1/identification/")) {
      expect(request.headers().authorization).toBeUndefined();
      expect(request.headers().cookie).toBeUndefined();
      expect(request.url()).not.toContain("089121288122");
    }
  });
  await openLookup(page);
  await expect(page.getByRole("heading", { name: "Check your bottle" })).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(2);
  await expect(page.getByRole("radio", { checked: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Confirm bottle & view details" })).toBeDisabled();
  await expect(page.getByText("Your vintage isn’t listed", { exact: false })).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  for (const width of [320, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    if (!process.env.CI)
      await page.screenshot({ path: testInfo.outputPath(`barcode-${width}.png`), fullPage: true });
  }
  await page.getByRole("radio", { name: "2022", exact: true }).check();
  const sent = page.waitForRequest(confirmation);
  await page.getByRole("button", { name: "Confirm bottle & view details" }).click();
  const body = (await sent).postDataJSON();
  expect(body).toMatchObject({
    gtin: "00089121288122",
    year: 2022,
    vintageStatus: "YEAR",
    edition: null,
  });
  await expect(page).toHaveURL(new RegExp(`/browse/${body.catalogReleaseId}$`));
  await expect(page.locator(".catalog-detail-head")).toContainText("2022");
  expect(writes).toBe(0);
  await page.getByRole("link", { name: "I tried this wine", exact: true }).click();
  await expect(page.locator(".selected-wine")).toContainText("2022");
  await page.getByLabel("Quick notes").fill("Synthetic barcode memory");
  await page.getByRole("button", { name: "Sign in to save", exact: true }).click();
  await finishSignIn(page, request);
  await expect(page).toHaveURL(/\/capture$/);
  await expect(page.getByLabel("Quick notes")).toHaveValue("Synthetic barcode memory");
  expect(writes).toBe(0);
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page).toHaveURL(/\/my-wines\/[0-9a-f-]+$/);
  expect(writes).toBe(1);
});

test("invalid and unknown codes recover; changed confirmation clears the obsolete choice", async ({
  page,
}) => {
  await openLookup(page);
  await page.getByRole("radio", { name: "2022", exact: true }).check();
  await page.route(confirmation, (route) =>
    route.fulfill({ status: 409, json: { error: { code: "BARCODE_SELECTION_CHANGED" } } }),
  );
  await page.getByRole("button", { name: "Confirm bottle & view details" }).click();
  await expect(page.locator(".barcode-lookup").getByRole("alert")).toContainText(
    "This match has changed",
  );
  await expect(page.getByRole("radio")).toHaveCount(0);
  await expect(page).toHaveURL(/\/browse$/);
  await page.getByLabel("Barcode number").fill("089121288123");
  await page.getByRole("button", { name: "Look up bottle", exact: true }).click();
  await expect(page.locator(".barcode-lookup").getByRole("alert")).toContainText(
    "Check the numbers",
  );
  await page.getByLabel("Barcode number").fill("012345678905");
  await page.getByRole("button", { name: "Look up bottle", exact: true }).click();
  await expect(
    page.getByText("No match in our barcode library yet.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Search by name", exact: true }).click();
  await expect(page.getByLabel("Search the wine library")).toBeFocused();
  await page.getByLabel("Search the wine library").fill("Seven Oaks");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.locator(".catalog-wine")).toHaveCount(2);
});

test("a single release still needs a choice and a new lookup clears that choice", async ({
  page,
  request,
}) => {
  const response = await request.post(
    "http://127.0.0.1:8000/api/v1/identification/barcode-lookups",
    {
      data: { gtin: "089121288122" },
    },
  );
  expect(response.ok()).toBe(true);
  const result = await response.json();
  result.candidates[0].releases = result.candidates[0].releases.slice(0, 1);
  await page.route(lookup, (route) => route.fulfill({ json: result }));
  await openLookup(page);
  await expect(page.getByRole("radio")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Confirm bottle & view details" })).toBeDisabled();
  await page.getByRole("radio").check();
  await expect(page.getByRole("button", { name: "Confirm bottle & view details" })).toBeEnabled();
  await page.getByRole("button", { name: "Look up bottle", exact: true }).click();
  await expect(page.getByRole("radio", { checked: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Confirm bottle & view details" })).toBeDisabled();
});

test("lookup handles rate limits, overflow, cancellation and network failure without losing a manual draft", async ({
  page,
}) => {
  await page.goto("/capture");
  await page.getByLabel("Quick notes").fill("Synthetic unfinished note");
  await page.getByRole("link", { name: "Browse wines", exact: true }).click();
  await page.route(lookup, (route) =>
    route.fulfill({
      status: 429,
      headers: { "Retry-After": "2", "Access-Control-Expose-Headers": "Retry-After" },
      json: {},
    }),
  );
  await openLookup(page);
  await expect(page.locator(".barcode-lookup").getByRole("alert")).toContainText(
    "Too many lookups",
  );
  await expect(page.getByRole("button", { name: "Look up bottle", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Look up bottle", exact: true })).toBeEnabled();
  await page.unroute(lookup);
  await page.route(lookup, (route) =>
    route.fulfill({ json: { gtin: "00089121288122", status: "TOO_MANY_MATCHES", candidates: [] } }),
  );
  await page.getByRole("button", { name: "Look up bottle", exact: true }).click();
  await expect(
    page.getByText("This barcode has too many possible matches.", { exact: false }),
  ).toBeVisible();
  await page.unroute(lookup);
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(lookup, async (route) => {
    await held;
    // Closing the panel aborts the browser request before this held response arrives.
    await route
      .fulfill({ json: { gtin: "00089121288122", status: "NOT_FOUND", candidates: [] } })
      .catch((error: Error) => {
        if (!error.message.includes("already handled")) throw error;
      });
  });
  const pending = page.waitForRequest(lookup);
  await page.getByRole("button", { name: "Look up bottle", exact: true }).click();
  await pending;
  const cancelled = page.waitForEvent("requestfailed", (request) =>
    request.url().endsWith("/barcode-lookups"),
  );
  await page.getByText("Look up a barcode", { exact: true }).click();
  await cancelled;
  release();
  await page.unroute(lookup);
  await page.getByText("Look up a barcode", { exact: true }).click();
  await expect(
    page.getByText("No match in our barcode library yet.", { exact: false }),
  ).toHaveCount(0);
  await page.route(lookup, (route) => route.abort("failed"));
  await page.getByRole("button", { name: "Look up bottle", exact: true }).click();
  await expect(page.locator(".barcode-lookup").getByRole("alert")).toContainText(
    "Check your connection",
  );
  await page.getByRole("link", { name: "Add your bottle manually", exact: true }).click();
  await expect(page.getByLabel("Quick notes")).toHaveValue("Synthetic unfinished note");
});
