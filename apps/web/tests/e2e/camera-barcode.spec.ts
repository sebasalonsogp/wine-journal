import { readFile } from "node:fs/promises";
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

declare global {
  interface Window {
    cameraTest: { requests: number; constraints?: MediaStreamConstraints; stream?: MediaStream };
  }
}

// Real canvas/video frames exercise the production decoder without accessing hardware.
async function cameraFixture(page: Page, image = "", failure = "") {
  await page.addInitScript(
    ({ image, failure }) => {
      window.cameraTest = { requests: 0 };
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
        value: async (constraints: MediaStreamConstraints) => {
          window.cameraTest.requests++;
          window.cameraTest.constraints = constraints;
          if (failure) throw new DOMException("Synthetic private device diagnostic", failure);
          const canvas = document.createElement("canvas");
          canvas.width = 750;
          canvas.height = 834;
          const ctx = canvas.getContext("2d")!;
          ctx.fillStyle = "white";
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          if (image) {
            const source = new Image();
            source.src = image;
            await source.decode();
            ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
          }
          const stream = canvas.captureStream(5);
          window.cameraTest.stream = stream;
          return stream;
        },
      });
    },
    { image, failure },
  );
}

async function openCamera(page: Page) {
  await page.goto("/browse");
  await page.getByText("Look up a barcode", { exact: true }).click();
  expect(await page.evaluate(() => window.cameraTest.requests)).toBe(0);
  await page.getByRole("button", { name: "Scan with camera", exact: true }).click();
}

async function expectStopped(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(() =>
        window.cameraTest.stream?.getTracks().every((t) => t.readyState === "ended"),
      ),
    )
    .toBe(true);
}

test("camera decodes a rotated bottle barcode, stops before lookup and requires a vintage", async ({
  page,
}) => {
  const image = await readFile("../../assets/evaluation/barcode/seven-oaks-label-back.jpg");
  await cameraFixture(page, `data:image/jpeg;base64,${image.toString("base64")}`);
  let lookups = 0;
  await page.route("**/api/v1/identification/barcode-lookups", async (route) => {
    lookups++;
    await expectStopped(page);
    expect(route.request().postDataJSON().gtin).toMatch(/^0?089121288122$/);
    await route.continue();
  });
  await openCamera(page);
  await expect(page.getByRole("heading", { name: "Check your bottle" })).toBeVisible();
  expect(lookups).toBe(1);
  expect(await page.evaluate(() => window.cameraTest.constraints)).toMatchObject({
    audio: false,
    video: { facingMode: { ideal: "environment" } },
  });
  await expect(page.getByRole("radio")).toHaveCount(2);
  await expect(page.getByRole("radio", { checked: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Confirm bottle & view details" })).toBeDisabled();
  await page.getByRole("radio", { name: "2023", exact: true }).check();
  await page.getByRole("button", { name: "Confirm bottle & view details" }).click();
  await expect(page.locator(".catalog-detail-head")).toContainText("2023");
});

for (const failure of ["NotAllowedError", "NotFoundError", "NotReadableError"]) {
  test(`${failure} recovers through manual barcode lookup`, async ({ page }) => {
    await cameraFixture(page, "", failure);
    await openCamera(page);
    await expect(page.locator(".barcode-camera [role=status]")).toContainText(
      /permission|No camera|unavailable/,
    );
    await expect(page.locator(".barcode-camera")).not.toContainText("private device diagnostic");
    await expect(page.getByRole("button", { name: "Scan with camera" })).toBeEnabled();
    await page.getByLabel("Barcode number").fill("089121288122");
    await page.getByRole("button", { name: "Look up bottle", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Check your bottle" })).toBeVisible();
  });
}

test("blank frames stay local; stop, close, manual input, fallback and navigation release the camera", async ({
  page,
}, testInfo) => {
  await cameraFixture(page);
  let lookups = 0;
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/identification/")) lookups++;
  });
  await openCamera(page);
  await expect(page.locator(".barcode-camera [role=status]")).toContainText("Point at the barcode");
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  for (const width of [320, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    if (!process.env.CI)
      await page.screenshot({ path: testInfo.outputPath(`camera-${width}.png`), fullPage: true });
  }
  await page.getByRole("button", { name: "Stop camera", exact: true }).click();
  await expectStopped(page);
  for (const action of ["close", "manual", "fallback", "navigate"]) {
    await page.getByRole("button", { name: "Scan with camera", exact: true }).click();
    await expect(page.locator(".barcode-camera [role=status]")).toContainText(
      "Point at the barcode",
    );
    // Retain the old stream across route unmounts so the cleanup is observable.
    const stream = await page.evaluateHandle(() => window.cameraTest.stream!);
    if (action === "close") await page.getByText("Look up a barcode", { exact: true }).click();
    if (action === "manual") await page.getByLabel("Barcode number").focus();
    if (action === "fallback")
      await page.getByRole("link", { name: "Search by name", exact: true }).click();
    if (action === "navigate")
      await page.getByRole("link", { name: "Add your bottle manually", exact: true }).click();
    await expect
      .poll(() => stream.evaluate((s) => s.getTracks().every((t) => t.readyState === "ended")))
      .toBe(true);
    await stream.dispose();
    if (action === "close") await page.getByText("Look up a barcode", { exact: true }).click();
  }
  expect(lookups).toBe(0);
});
