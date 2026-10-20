import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { build } from "esbuild";
import { chromium } from "@playwright/test";

const require = createRequire(import.meta.url);
const assets = new URL("../../../assets/evaluation/", import.meta.url);
const { values } = parseArgs({
  options: { manifest: { type: "string", default: "barcode-images.json" } },
});
assert.match(values.manifest, /^barcode-images(?:-[a-z]+)?\.json$/);
const manifestPath = new URL(values.manifest, assets);
assert.ok((await stat(manifestPath)).size <= 65536);
const manifestBytes = await readFile(manifestPath);
const manifest = JSON.parse(manifestBytes.toString("utf8"));
assert.ok(manifest.images.length > 0 && manifest.images.length <= 10);
const inputs = [];
for (const sample of manifest.images) {
  assert.match(sample.file, /^[a-z0-9-]+\.(jpg|png)$/);
  assert.ok(["image/jpeg", "image/png"].includes(sample.mime));
  assert.ok(Number.isInteger(sample.width) && sample.width > 0);
  assert.ok(Number.isInteger(sample.height) && sample.height > 0);
  assert.ok(sample.width * sample.height <= 4_000_000);
  assert.ok(sample.expected_gtin === null || /^\d{14}$/.test(sample.expected_gtin));
  const path = new URL(`barcode/${sample.file}`, assets);
  assert.ok((await stat(path)).size <= 4 * 1024 * 1024);
  const bytes = await readFile(path);
  assert.equal(createHash("sha256").update(bytes).digest("hex"), sample.sha256);
  inputs.push({ ...sample, dataUrl: `data:${sample.mime};base64,${bytes.toString("base64")}` });
}

// Bundle exact locked packages, not a CDN/UMD with an unknown embedded core.
const bundle = await build({
  entryPoints: [fileURLToPath(new URL("barcode-browser.js", import.meta.url))],
  bundle: true,
  write: false,
  platform: "browser",
  format: "iife",
  logLevel: "silent",
});
const browser = await chromium.launch({ headless: true, timeout: 10_000 });
const deadline = setTimeout(() => void browser.close(), 20_000);
try {
  const context = await browser.newContext({ offline: true, serviceWorkers: "block" });
  let networkAttempts = 0;
  await context.route("**/*", (route) => {
    networkAttempts++;
    return route.abort();
  });
  const page = await context.newPage();
  await page.addScriptTag({ content: bundle.outputFiles[0].text });
  const results = [];
  for (const sample of inputs) {
    const attempts = await page.evaluate((input) => window.evaluateBarcodeImage(input), {
      dataUrl: sample.dataUrl,
      width: sample.width,
      height: sample.height,
    });
    // Compare to independently read digits. UPC-E/QR cannot be zero-padded.
    const decoded = attempts.filter((attempt) => attempt.status === "DECODED");
    const correct = decoded.every(
      (attempt) =>
        ["UPC_A", "EAN_13", "EAN_8"].includes(attempt.format) &&
        attempt.text.padStart(14, "0") === sample.expected_gtin,
    );
    results.push({
      id: sample.id,
      expected_gtin: sample.expected_gtin,
      attempts,
      passed:
        correct && (sample.expected_gtin === null ? decoded.length === 0 : decoded.length > 0),
    });
  }
  const report = {
    measured_at: new Date().toISOString(),
    manifest: values.manifest,
    manifest_sha256: createHash("sha256").update(manifestBytes).digest("hex"),
    browser: `Chromium ${browser.version()}`,
    decoder: require("@zxing/browser/package.json").version,
    core: require("@zxing/library/package.json").version,
    source_images: inputs.length,
    physical_bottles: 0,
    unique_expected_codes: new Set(inputs.map((s) => s.expected_gtin).filter(Boolean)).size,
    camera_tested: false,
    iphone_tested: false,
    confirmed_wine_releases: 0,
    network_attempts: networkAttempts,
    results,
  };
  console.log(JSON.stringify(report, null, 2));
  assert.equal(networkAttempts, 0, "Offline experiment attempted a request");
  assert.ok(
    results.every((result) => result.passed),
    "Decoder did not match the reviewed fixtures",
  );
} finally {
  clearTimeout(deadline);
  await browser.close();
}
