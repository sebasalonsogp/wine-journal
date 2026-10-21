"use client";

import { useEffect, useRef, useState } from "react";
import { startCamera } from "./camera-session";

export function BarcodeCamera({
  onDetected,
  onStart,
}: {
  onDetected(code: string): void;
  onStart(): void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const stop = useRef<(() => void) | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => () => stop.current?.(), []);

  function begin() {
    if (stop.current || !video.current) return;
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setMessage(
        "Camera scanning needs a supported browser on HTTPS (or localhost). Enter the barcode number below.",
      );
      return;
    }
    onStart();
    setRunning(true);
    setMessage("Allow camera access to scan the barcode. You can cancel at any time.");
    stop.current = startCamera(video.current, {
      onReady: () =>
        setMessage("Point at the barcode and hold steady. Scanning stops after 30 seconds."),
      onCode: (code) => {
        stop.current = null;
        setRunning(false);
        setMessage("Barcode found.");
        onDetected(code);
      },
      onError: (message) => {
        stop.current = null;
        setRunning(false);
        setMessage(message);
      },
    });
  }

  return (
    <section className="barcode-camera" aria-label="Camera barcode scanner">
      <p className="catalog-caption">
        Scan the barcode with your camera. Video stays on your device; only the barcode number is
        looked up.
      </p>
      <video
        ref={video}
        muted
        playsInline
        aria-label="Live barcode camera preview"
        hidden={!running}
      />
      <p role="status">{message}</p>
      {running ? (
        <button
          type="button"
          className="button button-secondary"
          onClick={() => {
            stop.current?.();
            stop.current = null;
            setRunning(false);
            setMessage("Camera stopped. You can scan again or enter the number below.");
          }}
        >
          Stop camera
        </button>
      ) : (
        <button type="button" className="button button-secondary" onClick={begin}>
          Scan with camera
        </button>
      )}
    </section>
  );
}
