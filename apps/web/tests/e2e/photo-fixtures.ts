import { expect } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

export const photo = {
  name: "table-memory.png",
  mimeType: "image/png",
  buffer: Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII=",
    "base64",
  ),
};

export function processPhoto() {
  const result = spawnSync(
    "uv",
    ["run", "--locked", "python", "-m", "wine_journal.worker", "--once"],
    {
      cwd: resolve("../api"),
      env: { ...process.env, WINE_JOURNAL_MEDIA_UPLOADS_ENABLED: "true" },
      timeout: 45000,
      stdio: "pipe",
      windowsHide: true,
    },
  );
  expect(result.status, "Local photo worker finished; diagnostics withheld").toBe(0);
}
