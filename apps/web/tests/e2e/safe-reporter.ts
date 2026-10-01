import type { Reporter, TestCase, TestResult } from "@playwright/test/reporter";
import { mkdir, writeFile } from "node:fs/promises";

export default class SafeReporter implements Reporter {
  private results: { test: string; status: string; durationMs: number; errors: number }[] = [];
  onTestEnd(test: TestCase, result: TestResult) {
    this.results.push({
      test: test.title,
      status: result.status,
      durationMs: result.duration,
      errors: result.errors.length,
    });
  }
  async onEnd() {
    await mkdir("test-results", { recursive: true });
    // Explicit allowlist: no error bodies, stack traces, DOM, attachments or network traffic.
    await writeFile(
      "test-results/auth-check-summary.json",
      JSON.stringify(this.results, null, 2) + "\n",
    );
  }
}
