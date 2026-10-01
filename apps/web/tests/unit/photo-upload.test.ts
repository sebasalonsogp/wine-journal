import assert from "node:assert/strict";
import { test } from "node:test";
import { createTransport } from "../../src/lib/api/transport";
import { RequestFailure } from "../../src/lib/session/http";
import { photoType, uploadPhoto, type UploadIdentity } from "../../src/features/media/photo-upload";

test("photo selection rejects empty, oversized and unsupported files, with an HEIC fallback", () => {
  assert.equal(photoType({ type: "", name: "Memory.HEIC", size: 10 }), "image/heic");
  for (const file of [
    { type: "image/png", name: "empty.png", size: 0 },
    { type: "image/jpeg", name: "large.jpg", size: 20 * 1024 * 1024 + 1 },
    { type: "image/svg+xml", name: "wrong.heic", size: 10 },
    { type: "video/quicktime", name: "clip.mov", size: 10 },
  ])
    assert.throws(() => photoType(file));
});

for (const failure of [
  "lost-upload-response",
  "failed-upload",
  "lost-completion-response",
  "expired-grant",
]) {
  test(`photo retry preserves identity after ${failure} and never recreates the entry`, async () => {
    const original = globalThis.fetch;
    let stored = false;
    let uploaded = 0;
    let completed = 0;
    const keys: string[] = [];
    globalThis.fetch = async (input, init) => {
      if (input === "/auth/session")
        return Response.json({
          accessToken: "synthetic",
          subject: "test",
          expiresAt: Date.now() / 1000 + 3600,
          apiUrl: "https://api.example.test",
        });
      if (input === "https://storage.example.test/signed-upload") {
        assert.equal(init?.credentials, "omit");
        assert.equal(init?.cache, "no-store");
        assert.equal(new Headers(init?.headers).has("Authorization"), false);
        assert.equal(new Headers(init?.headers).has("x-upsert"), false);
        uploaded++;
        if (failure === "failed-upload" && uploaded === 1) throw new TypeError("offline");
        stored = true;
        if (failure === "lost-upload-response") throw new TypeError("response lost");
        return new Response(null, { status: 200 });
      }
      const request = input as Request;
      const path = new URL(request.url).pathname;
      if (path.endsWith("/media/uploads")) {
        keys.push(request.headers.get("Idempotency-Key")!);
        return Response.json({
          assetId: "asset",
          uploadUrl: "https://storage.example.test/signed-upload",
          contentType: "image/png",
        });
      }
      if (path === "/api/v1/entries/entry/photos/asset")
        return Response.json({ assetId: "asset", version: 1 });
      if (path.endsWith("/complete")) {
        completed++;
        if (failure === "expired-grant" && completed <= 2)
          return Response.json({ error: { code: "UPLOAD_EXPIRED" } }, { status: 409 });
        if (!stored) return Response.json({ error: { code: "UPLOAD_MISSING" } }, { status: 409 });
        if (failure === "lost-completion-response" && completed === 1)
          throw new TypeError("response lost");
        return Response.json({ assetId: "asset", state: "PROCESSING" });
      }
      throw new Error("Unexpected request; entry creation is forbidden in photo retries.");
    };
    try {
      const identity: UploadIdentity = { operationKey: "same-operation" };
      const api = createTransport();
      const run = () =>
        uploadPhoto(
          api,
          "entry",
          new File(["image"], "memory.png", { type: "image/png" }),
          identity,
          new AbortController().signal,
          () => {},
        );
      if (failure === "lost-upload-response") await run();
      else {
        await assert.rejects(run(), RequestFailure);
        await run();
      }
      assert.equal(identity.assetId, "asset");
      assert.ok(keys.every((key) => key === identity.operationKey));
      assert.equal(uploaded, ["failed-upload", "expired-grant"].includes(failure) ? 2 : 1);
    } finally {
      globalThis.fetch = original;
    }
  });
}

test("aborted photo work does not request a new capability", async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    uploadPhoto(
      createTransport(),
      "entry",
      new File(["x"], "x.png", { type: "image/png" }),
      { operationKey: "key" },
      controller.signal,
      () => {},
    ),
    { name: "AbortError" },
  );
});
