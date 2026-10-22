# R03a — Local label OCR feasibility, October 21

**Decision: keep photo recognition out of the application for now.** Native
Tesseract is inexpensive to run locally, but this first unmodified-image baseline
retrieves the expected offering for only 2/7 inputs in each tested layout mode.
This is insufficient evidence for a reliable default photo-recognition flow.
R03, C06/C07 and the 31/59 parent completion count remain unchanged.

## Measured evidence

The seven existing, hashed producer assets represent **five offerings from two
producers**, not seven independently photographed bottles. They reuse the
[original](../assets/evaluation/barcode-images.json) and
[expanded](../assets/evaluation/barcode-images-ridge.json) image manifests.
Ground truth comes from those manifests and the 30-release identity baseline,
independently of OCR. The image bytes were not cropped or enhanced for this run.

| Image | Automatic layout (PSM 3) | Sparse text (PSM 11) |
| --- | --- | --- |
| I001 Seven Oaks flat back | Expected offering, both catalog vintages | Same |
| I002 Seven Oaks bottle back | Expected offering, both catalog vintages | No candidate |
| I003 Seven Oaks decorative front | No candidate | No candidate |
| I004 Geyserville rear | No candidate | No candidate |
| I005 Three Valleys rear | No candidate | Expected offering, both catalog vintages |
| I006 Estate Chardonnay rear | No candidate | No candidate |
| I007 Monte Bello rear | No candidate | No candidate |

[Automatic-layout results](../assets/evaluation/label-ocr-auto-results.json) and
[sparse-text results](../assets/evaluation/label-ocr-results.json) retain accepted
public-label text, word-confidence averages, candidate IDs, hashes and timing.
Automatic mode spans 547–984 ms per image (median 797 ms); sparse mode spans
531–1156 ms (median 656 ms), including container startup and cleanup on this
Docker Desktop machine. These are single-run observations, not latency percentiles
or hosted-service guarantees. Peak memory was not measured; a 256 MiB limit applies.

The experiment filters words below OCR confidence 60, then requires producer/name
or producer-domain evidence plus at least 80% of the catalog wine-name tokens.
This is a deliberately simple, uncalibrated candidate baseline. Word confidence
is **not** a probability that a wine identity is correct. Matching sees only OCR
text and the full catalog; it cannot read expected fixture IDs. It retains every
vintage for a matched offering, even when a year is detected.

Geyserville's sparse read sees **2025**, its bottling year, while missing the
visible 2023 vintage. Monte Bello yields 2022, 2023 and 2025 from its narrative.
The front label visibly says “Family owned since 1974”; the baseline misses that
text. These are reasons to preserve year observations separately from vintage
confirmation. Zero releases were automatically resolved or saved.

## Shortlist and access

| Route | Access and image handling | Evidence / decision |
| --- | --- | --- |
| Native Tesseract + local catalog | Local compute; no API account or per-call bill. Runtime network disabled; image bytes enter via stdin and container state is removed. | Two layout modes measured above. Keep as a baseline; insufficient recall for C06. |
| Tesseract.js | WebAssembly wrapper of Tesseract; can run in browser/Node. Local worker/model hosting needs explicit configuration. | Documentation comparison only. It does not independently establish better recognition; do not add a second runtime yet. |
| Google Cloud Vision text/web detection | Billing-enabled project and credentials required. Pricing documents a first 1,000 monthly units free per feature; subsequent use is billed. | Not called, no account enabled, no images uploaded. Text detection can feed matching; web detection returns entities/matching pages, not a verified wine-release contract. Accuracy and latency are unmeasured. |

Google documents in-memory image processing for synchronous requests, separate
temporary retention for asynchronous jobs, and temporary request-metadata logging.
A free allowance is not a hard spending cap. Cloud comparison remains an access
gap, not a measured failure or an approved integration.

## Reproduce and constraints

From the repository root, with Docker available:

```powershell
docker build --tag wine-journal-label-evaluation:v1 scripts/label-ocr
uv run --project apps/api --locked python scripts/evaluate_label.py --psm 11
uv run --project apps/api --locked python scripts/evaluate_label.py --psm 3
```

Use `--output <path>` to retain a report. Only the two fixed public fixture
manifests are accepted; image paths, hashes, byte size and declared pixel size are
checked. Pixel metadata is trusted for these reviewed hashes, not for arbitrary
uploads. This harness must not be exposed as a public image endpoint.

The Docker context contains only the Dockerfile. The existing pinned Python base
digest and exact Debian Tesseract/English model versions are recorded; transitive
OS packages are not fully snapshot-pinned, so reports retain the built image ID.
Build-time package downloads are distinct from network-disabled OCR execution.
The application dependency locks and API/web runtime images are unchanged.

Runtime uses a non-root, read-only container, no host mounts or injected secrets,
one CPU, 256 MiB memory/swap ceiling, 32 process limit, bounded tmpfs and disabled
container logging. Each OCR process has a ten-second limit. A fifteen-second host
deadline is followed by explicit removal with a ten-second cleanup deadline;
cleanup failure aborts the evaluation. These bounds do not yet satisfy an end-to-end
ten-second public request contract. No upload ingress, shared quota or persistence
implementation is claimed. The trusted-fixture harness validates captured output
after completion; a production adapter must also bound output while reading it.

Thirteen unit cases cover candidate ambiguity, unrelated years, low-confidence
words, malformed/oversized OCR responses, changed/outside fixtures, container
outcomes, timeout and unconfirmed cleanup. One real-container integration case
replays all seven images, a blank control and malformed input, then checks that
no evaluation container remains. The opt-in integration runs in CI after building
the isolated image. Blank input returns no readable text; malformed input is
rejected. Simulated timeout/unavailability tests are distinct from live OCR evidence.

## Next bounded experiment

Evaluate a fixed, documented crop/contrast strategy on these same originals plus
held-out physical-phone and out-of-catalog images. Preserve this baseline; do not
hand-tune each label against its answer. The current set lacks real glare/blur,
non-English labels, a non-vintage label and an out-of-catalog wine, so it cannot
measure general recall or false-positive rates. Compare a hosted route only if
access is deliberately configured. C06/C07 need a supported route and bounded
ingress/cleanup design before application integration.

## Primary sources checked October 21

- [Tesseract CLI and layout modes](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)
- [Tesseract image-quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [Debian engine package](https://packages.debian.org/bookworm/tesseract-ocr) and [English model package](https://packages.debian.org/bookworm/tesseract-ocr-eng)
- [Tesseract.js scope](https://github.com/naptha/tesseract.js) and [local installation](https://github.com/naptha/tesseract.js/blob/master/docs/local-installation.md)
- [Cloud Vision setup](https://docs.cloud.google.com/vision/docs/setup), [pricing](https://cloud.google.com/vision/pricing), [data usage](https://docs.cloud.google.com/vision/docs/data-usage) and [web detection output](https://docs.cloud.google.com/vision/docs/detecting-web)
