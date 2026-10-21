import { BrowserMultiFormatReader } from "@zxing/browser";
import {
  BarcodeFormat,
  DecodeHintType,
  NotFoundException,
  ChecksumException,
  FormatException,
} from "@zxing/library";

// Loaded on demand. Frames and the quarter-turn recovery stay in browser memory.
export function createFrameDecoder() {
  const formats = [BarcodeFormat.UPC_A, BarcodeFormat.EAN_13, BarcodeFormat.EAN_8];
  const reader = new BrowserMultiFormatReader(
    new Map<DecodeHintType, BarcodeFormat[] | boolean>([
      [DecodeHintType.POSSIBLE_FORMATS, formats],
      [DecodeHintType.TRY_HARDER, true],
    ]),
  );
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("Canvas unavailable");
  return {
    decode(video: HTMLVideoElement): string | null {
      if (!video.videoWidth || !video.videoHeight || video.readyState < 2) return null;
      const scale = Math.min(1, 1280 / Math.max(video.videoWidth, video.videoHeight));
      const width = Math.max(1, Math.round(video.videoWidth * scale));
      const height = Math.max(1, Math.round(video.videoHeight * scale));
      for (const rotated of [false, true]) {
        canvas.width = rotated ? height : width;
        canvas.height = rotated ? width : height;
        if (rotated) {
          context.translate(height, 0);
          context.rotate(Math.PI / 2);
        }
        context.drawImage(video, 0, 0, width, height);
        try {
          const result = reader.decodeFromCanvas(canvas);
          if (
            formats.includes(result.getBarcodeFormat()) &&
            /^(?:\d{8}|\d{12,13})$/.test(result.getText())
          )
            return result.getText();
        } catch (error) {
          if (!(
            error instanceof NotFoundException ||
            error instanceof ChecksumException ||
            error instanceof FormatException
          ))
            throw error;
        }
      }
      return null;
    },
    dispose() {
      canvas.width = 0;
      canvas.height = 0;
    },
  };
}
