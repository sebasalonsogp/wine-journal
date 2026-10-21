import assert from "node:assert/strict";
import { test } from "node:test";
import { cameraFailure, startCamera } from "../../src/features/identification/camera-session";

test("camera errors give recovery guidance without exposing device diagnostics", () => {
  for (const name of [
    "NotAllowedError",
    "NotFoundError",
    "NotReadableError",
    "OverconstrainedError",
    "Error",
  ]) {
    const message = cameraFailure({ name, message: "private device details" });
    assert.ok(message.length > 20);
    assert.equal(message.includes("private device"), false);
  }
  assert.match(cameraFailure({ name: "NotAllowedError" }), /permission/i);
  assert.match(cameraFailure({ name: "NotFoundError" }), /No camera/i);
});

test("a stream granted after cancellation is stopped without playing or decoding", async () => {
  let grant: (stream: MediaStream) => void = () => {};
  const permission = new Promise<MediaStream>((resolve) => {
    grant = resolve;
  });
  let stopped = 0;
  let played = 0;
  let decoded = 0;
  let disposed = 0;
  const track = {
    stop: () => {
      stopped++;
    },
  };
  const stream = { getTracks: () => [track] } as unknown as MediaStream;
  const video = {
    pause() {},
    srcObject: null,
    play: async () => {
      played++;
    },
  } as unknown as HTMLVideoElement;
  const events = new EventTarget();
  const documentEvents = Object.assign(new EventTarget(), { hidden: false });
  const stop = startCamera(
    video,
    {
      onCode() {
        decoded++;
      },
      onError() {
        throw new Error("Late failure");
      },
      onReady() {},
    },
    {
      getStream: () => permission,
      loadDecoder: async () => ({
        decode: () => null,
        dispose: () => {
          disposed++;
        },
      }),
      page: events,
      document: documentEvents,
    },
  );
  await Promise.resolve();
  stop();
  grant(stream);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(stopped, 1);
  assert.equal(played, 0);
  assert.equal(decoded, 0);
  assert.equal(disposed, 1);
});

for (const interruption of ["decoded", "pagehide", "hidden", "ended", "timeout"] as const) {
  test(`camera releases resources before reporting ${interruption}`, async (context) => {
    context.mock.timers.enable({ apis: ["setTimeout"] });
    let stopped = 0;
    let disposed = 0;
    let reported = 0;
    const track = Object.assign(new EventTarget(), { stop: () => stopped++ });
    const video = {
      srcObject: null,
      pause() {},
      play: async () => {},
    } as unknown as HTMLVideoElement;
    const page = new EventTarget();
    const document = Object.assign(new EventTarget(), { hidden: false });
    const report = () => {
      assert.equal(stopped, 1);
      assert.equal(disposed, 1);
      assert.equal(video.srcObject, null);
      reported++;
    };
    const stop = startCamera(
      video,
      { onCode: report, onError: report, onReady() {} },
      {
        getStream: async () => ({ getTracks: () => [track] }) as unknown as MediaStream,
        loadDecoder: async () => ({
          decode: () => (interruption === "decoded" ? "089121288122" : null),
          dispose: () => disposed++,
        }),
        page,
        document,
      },
    );
    await new Promise((resolve) => setImmediate(resolve));
    if (interruption === "pagehide") page.dispatchEvent(new Event("pagehide"));
    if (interruption === "hidden") {
      document.hidden = true;
      document.dispatchEvent(new Event("visibilitychange"));
    }
    if (interruption === "ended") track.dispatchEvent(new Event("ended"));
    if (interruption === "timeout") context.mock.timers.tick(30000);
    stop();
    context.mock.timers.tick(60000);
    assert.equal(reported, 1);
    assert.equal(stopped, 1);
    assert.equal(disposed, 1);
  });
}

test("cancelled decoder loading never requests permission and disposes the late decoder", async () => {
  let ready: (decoder: { decode(): null; dispose(): void }) => void = () => {};
  let disposed = 0;
  let requested = 0;
  const decoder = new Promise<{ decode(): null; dispose(): void }>((resolve) => {
    ready = resolve;
  });
  const stop = startCamera(
    { pause() {}, srcObject: null } as unknown as HTMLVideoElement,
    {
      onReady() {
        assert.fail("cancelled");
      },
      onCode() {
        assert.fail("cancelled");
      },
      onError() {
        assert.fail("cancelled");
      },
    },
    {
      loadDecoder: () => decoder,
      getStream: async () => {
        requested++;
        throw new Error("Should not request");
      },
      page: new EventTarget(),
      document: Object.assign(new EventTarget(), { hidden: false }),
    },
  );
  stop();
  ready({
    decode: () => null,
    dispose: () => {
      disposed++;
    },
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(requested, 0);
  assert.equal(disposed, 1);
});
