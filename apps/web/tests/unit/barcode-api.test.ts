import assert from "node:assert/strict";
import { test } from "node:test";
import { barcodeApi, BarcodeFailure } from "../../src/features/identification/api";

test("barcode requests omit credentials, keep codes out of URLs, and confirm the exact release", async () => {
  const original = globalThis.fetch;
  const requests: Request[] = [];
  globalThis.fetch = async (input) => {
    const request = input as Request;
    requests.push(request);
    assert.equal(request.credentials, "omit");
    assert.equal(request.cache, "no-store");
    assert.equal(request.redirect, "error");
    assert.equal(request.headers.has("Authorization"), false);
    assert.equal(request.url.includes("089121288122"), false);
    return Response.json({ status: "NOT_FOUND", gtin: "00089121288122", candidates: [] });
  };
  try {
    const api = barcodeApi("https://api.example.test");
    await api.lookup("089121288122", new AbortController().signal);
    assert.deepEqual(await requests[0].json(), { gtin: "089121288122" });
    const body = {
      gtin: "00089121288122",
      catalogReleaseId: "release",
      vintageStatus: "YEAR" as const,
      year: 2022,
      edition: null,
    };
    await api.confirm(body, new AbortController().signal);
    assert.deepEqual(await requests[1].json(), body);
    assert.equal(requests.length, 2);
  } finally {
    globalThis.fetch = original;
  }
});

test("barcode errors are sanitized, respect retry hints and never retry automatically", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  try {
    for (const status of [409, 422, 429, 503]) {
      globalThis.fetch = async () => {
        calls++;
        return Response.json(
          { detail: "untrusted private diagnostic" },
          {
            status,
            headers: { "Retry-After": "7" },
          },
        );
      };
      await assert.rejects(
        barcodeApi("https://api.example.test").lookup("code", new AbortController().signal),
        (error: BarcodeFailure) => {
          assert.equal(error.status, status);
          assert.equal(error.message.includes("private diagnostic"), false);
          assert.equal(error.retryAfter, status === 429 || status === 503 ? 7 : 0);
          return true;
        },
      );
    }
    assert.equal(calls, 4);
    globalThis.fetch = async () => {
      throw new TypeError("internal network detail");
    };
    await assert.rejects(
      barcodeApi("https://api.example.test").lookup("code", new AbortController().signal),
      (error: BarcodeFailure) => error.status === 503 && !error.message.includes("internal"),
    );
  } finally {
    globalThis.fetch = original;
  }
});
