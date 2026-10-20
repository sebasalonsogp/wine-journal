import { BrowserMultiFormatReader } from "@zxing/browser";
import { BarcodeFormat, DecodeHintType, NotFoundException } from "@zxing/library";

// Evaluation only. No camera, provider requests, catalog writes or journal state.
window.evaluateBarcodeImage = async ({ dataUrl, width, height }) => {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  if (image.naturalWidth !== width || image.naturalHeight !== height) {
    throw new Error("Fixture dimensions changed");
  }
  const reader = new BrowserMultiFormatReader(
    new Map([
      [
        DecodeHintType.POSSIBLE_FORMATS,
        [BarcodeFormat.UPC_A, BarcodeFormat.EAN_13, BarcodeFormat.EAN_8],
      ],
      [DecodeHintType.TRY_HARDER, true],
    ]),
  );
  // A quarter turn is an in-memory experiment, not another camera capture.
  return [0, 90].map((rotation) => {
    const canvas = document.createElement("canvas");
    canvas.width = rotation ? height : width;
    canvas.height = rotation ? width : height;
    const context = canvas.getContext("2d");
    context.fillStyle = "white";
    context.fillRect(0, 0, canvas.width, canvas.height);
    if (rotation) {
      context.translate(height, 0);
      context.rotate(Math.PI / 2);
    }
    context.drawImage(image, 0, 0);
    const start = performance.now();
    try {
      const result = reader.decodeFromCanvas(canvas);
      return {
        rotation,
        status: "DECODED",
        text: result.getText(),
        format: BarcodeFormat[result.getBarcodeFormat()],
        elapsed_ms: Math.round((performance.now() - start) * 10) / 10,
      };
    } catch (error) {
      if (!(error instanceof NotFoundException)) throw error;
      return {
        rotation,
        status: "NOT_FOUND",
        text: null,
        format: null,
        elapsed_ms: Math.round((performance.now() - start) * 10) / 10,
      };
    }
  });
};
