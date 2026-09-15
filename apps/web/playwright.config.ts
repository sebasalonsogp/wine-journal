import { defineConfig } from "@playwright/test";

// The pinned runner honors this flag to omit automatic DOM snapshots on failure.
process.env.PLAYWRIGHT_NO_COPY_PROMPT = "1";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45000,
  reporter: [["list"], ["./tests/e2e/safe-reporter.ts"]],
  use: {
    baseURL: "http://localhost:3000",
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    // Auth traffic contains credentials. Never record HAR, traces, video or storageState.
    trace: "off",
    video: "off",
    screenshot: "off",
  },
  webServer: [
    {
      command: "npm run start -- --hostname 127.0.0.1",
      url: "http://localhost:3000/browse",
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command:
        "uv run --project ../api --locked uvicorn wine_journal.main:app --host 127.0.0.1 --port 8000 --no-access-log",
      url: "http://127.0.0.1:8000/api/v1/health/live",
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
