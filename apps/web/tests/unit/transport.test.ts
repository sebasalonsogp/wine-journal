import assert from "node:assert/strict";
import { test } from "node:test";
import { createTransport } from "../../src/lib/api/transport";
import { RequestFailure } from "../../src/lib/session/http";

test("parallel API rejections share one refresh and never retry indefinitely", async () => {
  const original = globalThis.fetch;
  let sessions = 0;
  let refreshes = 0;
  let apiCalls = 0;
  globalThis.fetch = async (input, init) => {
    if (input === "/auth/session") {
      sessions++;
      if (JSON.parse(String(init?.body)).refresh) refreshes++;
      return Response.json({
        accessToken: `test-${sessions}`,
        subject: "subject",
        email: "example@example.test",
        expiresAt: Date.now() / 1000 + 3600,
        apiUrl: "https://api.example.test",
      });
    }
    apiCalls++;
    const request = input as Request;
    assert.equal(request.credentials, "omit");
    return request.headers.get("Authorization") === "Bearer test-1"
      ? Response.json({}, { status: 401 })
      : Response.json({ id: "account", state: "ACTIVE", createdAt: "2026-09-14T00:00:00Z" });
  };
  try {
    const transport = createTransport();
    const results = await Promise.all([transport.account(), transport.account()]);
    assert.equal(results[0].id, results[1].id);
    assert.equal(sessions, 2);
    assert.equal(refreshes, 1);
    assert.equal(apiCalls, 4);
    transport.clear();
    await transport.account();
    assert.equal(sessions, 3);
  } finally {
    globalThis.fetch = original;
  }
});

test("an invalid refresh stops with 401 and a transient failure remains retryable", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return Response.json({ message: "Session ended" }, { status: 401 });
  };
  try {
    const transport = createTransport();
    await assert.rejects(transport.account(), (error: RequestFailure) => error.status === 401);
    assert.equal(calls, 1);
    globalThis.fetch = async () => {
      throw new TypeError("synthetic network failure");
    };
    await assert.rejects(transport.account(), (error: RequestFailure) => error.status === 503);
  } finally {
    globalThis.fetch = original;
  }
});
