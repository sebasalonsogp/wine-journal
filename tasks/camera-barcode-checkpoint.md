# C05b — Camera barcode capture

Browse Wines → Look up a barcode now offers **Scan with camera**. A decoded
number enters the existing guest lookup flow; the camera stops before the request.
The user still selects and confirms the exact vintage/edition before viewing
details. Scanning never logs a drink. Manual numbers, name search and manual wine
capture remain available, including when the camera is denied or unavailable.

## Implementation boundaries

- ZXing browser 0.2.1/library 0.23.0 move from development to runtime dependencies
  without changing versions. Dynamic import loads the decoder on the scan action.
- Audio is disabled; the rear camera is preferred without requiring a specific
  device. The preview is muted and inline. HTTPS or localhost is required.
- Frames stay in transient browser canvases; only the decoded number is sent to
  the existing API. No new credentials, environment variables, persistent image
  storage, provider integration, database change or analytics are introduced.
- Scanning tries UPC-A, EAN-13 and EAN-8, with a quarter-turn recovery attempt.
  Each attempt bounds the longest frame edge to 1280 pixels; attempts are spaced
  by 350 ms and the session has a 30-second deadline, including startup/permission.
  QR, UPC-E and case codes are outside this camera slice; manual API capabilities
  are unchanged. Image decoding does not establish vintage identity.
- Tracks, preview and timers are released on success, stop, panel close, manual
  input, the name-search fallback, route unmount, page hiding, backgrounding,
  device interruption, failure or deadline. Permission granted after cancellation
  is immediately released. A cancelled module load never requests the camera.
- Small UI, session lifecycle and decoder modules keep browser hardware concerns
  separate from lookup/confirmation. There is no new service or API endpoint.

## Verification

Eight unit tests cover sanitized failures, late permission, late module loading,
success cleanup, page/visibility interruption, track ending and deadline cleanup.
An intentional inversion of the visibility condition fails its regression test;
the source was restored immediately afterward.

Five browser journeys use controlled camera responses. A real canvas MediaStream
of the reviewed Seven Oaks back label passes through the production video decoder,
including rotation recovery, then the local curated API and explicit 2023 choice.
The test asserts tracks are stopped before the single lookup request. Blank frames
produce no lookup; stop, collapse, manual input, fallback and guest route navigation
release the stream. Permission-denied, absent-device and busy-device cases recover
through real manual lookup. No test accesses a physical camera.

Accessibility checks and visual inspection cover the active preview at 320 and
1440 pixels. The Impeccable check reports no findings. The existing offline decoder
evaluation also passes all three reviewed image fixtures: two views of one barcode
and a negative front label. This is narrow fixture evidence, not a coverage claim.

Local closeout: all 47 frontend unit tests and 43 browser journeys pass. Lint,
formatting, type checks and the production build pass; npm reports zero audit
findings, and the generated-browser-credential scan passes. Exact-head remote CI
remains the merge gate. The decoder is a separate approximately 479 kB uncompressed
production chunk, requested only when starting the scanner; physical-device CPU
and decode latency still need measurement.

## Remaining physical-device acceptance

C05 and the broader R01/R02/C04 coverage gates remain open. Before claiming iPhone
support, record device model, iOS/Safari versions and HTTPS test origin; try real
bottles in varying light/orientation, deny then allow permission, background and
return, leave the page, and verify the camera indicator turns off. Measure time
to decode and UI responsiveness; verify failed/unknown scans preserve manual
recovery and capture drafts. Browser simulation does not replace these checks.

The scan still uses the small curated barcode library. Label recognition and
photo uploads for identification are separate future work.

## Sources

- [Media capture and permission requirements](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- [ZXing browser API](https://github.com/zxing-js/browser)
- Installed Next.js lazy-loading guide and pinned ZXing source, checked against
  the actual installed versions before implementation.
