type Decoder = { decode(video: HTMLVideoElement): string | null; dispose(): void };
type Callbacks = { onCode(code: string): void; onError(message: string): void; onReady(): void };
type Environment = {
  getStream(): Promise<MediaStream>;
  loadDecoder(): Promise<Decoder>;
  page: EventTarget;
  document: EventTarget & { readonly hidden: boolean };
};

export function cameraFailure(error: unknown): string {
  const name = error && typeof error === "object" && "name" in error ? error.name : "";
  if (name === "NotAllowedError")
    return "Camera permission wasn’t granted. Allow it in your browser settings, or enter the barcode number below.";
  if (name === "NotFoundError") return "No camera was found. Enter the barcode number below.";
  if (name === "NotReadableError")
    return "The camera is unavailable or in use. Close other camera apps and try again, or enter the number below.";
  return "We couldn’t start or read the camera. Try again, or enter the barcode number below.";
}

export function startCamera(
  video: HTMLVideoElement,
  callbacks: Callbacks,
  environment?: Environment,
): () => void {
  const env = environment ?? {
    getStream: () =>
      navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      }),
    loadDecoder: async () => (await import("./camera-decoder")).createFrameDecoder(),
    page: window,
    document,
  };
  let stopped = false;
  let stream: MediaStream | null = null;
  let decoder: Decoder | null = null;
  let frameTimer: ReturnType<typeof setTimeout> | undefined;
  const deadline = setTimeout(
    () =>
      fail(
        stream
          ? "No barcode found yet. Improve the light, hold the barcode closer and try again, or enter its number below."
          : "The camera didn’t start in time. Try again, or enter the barcode number below.",
      ),
    30000,
  );
  const interrupt = () =>
    fail("Camera stopped. Start scanning again when you’re ready, or enter the number below.");
  const hidden = () => {
    if (env.document.hidden) interrupt();
  };

  function stop() {
    if (stopped) return;
    stopped = true;
    clearTimeout(deadline);
    clearTimeout(frameTimer);
    env.page.removeEventListener("pagehide", interrupt);
    env.document.removeEventListener("visibilitychange", hidden);
    stream?.getTracks().forEach((track) => {
      track.removeEventListener("ended", interrupt);
      track.stop();
    });
    video.pause();
    video.srcObject = null;
    decoder?.dispose();
  }
  function fail(message: string) {
    if (stopped) return;
    stop();
    callbacks.onError(message);
  }
  function scan() {
    if (stopped) return;
    try {
      const code = decoder!.decode(video);
      if (code) {
        stop();
        callbacks.onCode(code);
        return;
      }
      frameTimer = setTimeout(scan, 350);
    } catch (error) {
      fail(cameraFailure(error));
    }
  }
  env.page.addEventListener("pagehide", interrupt);
  env.document.addEventListener("visibilitychange", hidden);
  void (async () => {
    decoder = await env.loadDecoder();
    if (stopped) {
      decoder.dispose();
      return;
    }
    stream = await env.getStream();
    if (stopped) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    stream.getTracks().forEach((track) => track.addEventListener("ended", interrupt));
    video.srcObject = stream;
    await video.play();
    if (stopped) return;
    callbacks.onReady();
    scan();
  })().catch((error: unknown) => fail(cameraFailure(error)));
  return stop;
}
