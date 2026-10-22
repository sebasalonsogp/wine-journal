# R03b — Fixed preprocessing experiment, October 21

**Decision: reject this recipe as the default.** The same seven reviewed producer
images still yield expected candidates in only **2/7** cases. Both successes now
belong to Seven Oaks: coverage falls from two offerings to one of the five in
the set. Photo recognition remains disabled; R03/C06/C07 and the 31/59 parent
completion count remain unchanged.

## Fixed hypothesis and results

After EXIF orientation and white alpha compositing, images at least twice as tall
as wide are cropped to 5–95% width and 48–82% height. Other shapes remain whole.
The recipe converts to grayscale, inverts when median luminance is below 128,
applies 1% autocontrast, resizes by up to 2x with a 1800-pixel long-edge cap, and
adds a 12-pixel white border. These rules were fixed before the measured run;
there are no per-image crops, identity-driven branches or matcher adjustments.

The engine, English model, PSM 11 layout and candidate threshold are unchanged
from [R03a](label-recognition-checkpoint.md). Original fixtures and baseline
reports are preserved. The [new report](../assets/evaluation/label-ocr-preprocessed-results.json)
records source/transformed hashes, recipe parameters, Pillow version, accepted
OCR text, candidates, year observations and timings.

| Image | Original sparse baseline | Fixed recipe |
| --- | --- | --- |
| I001 Seven Oaks flat back | Expected offering | Expected offering |
| I002 Seven Oaks bottle back | No candidate | Expected offering |
| I003 Seven Oaks decorative front | No candidate | No candidate |
| I004 Geyserville rear | No candidate | No candidate |
| I005 Three Valleys rear | Expected offering | No candidate |
| I006 Estate Chardonnay rear | No candidate | No candidate |
| I007 Monte Bello rear | No candidate | No candidate |

Every matched offering retains both catalog vintages; no release is resolved.
Geyserville yields both 2023 and 2025, while Monte Bello yields three years.
Detecting a year therefore still cannot establish the vintage.

Preparation took 78–94 ms per image. Preparation plus OCR/container cleanup took
906–1750 ms (median 1235 ms) in this single local run. Baseline and new timings
were collected separately under uncontrolled machine load; these are observations,
not a comparative performance guarantee.

## Withheld-offering control and limitations

For each OCR result, remove every catalog release sharing its expected offering's
definition key, then rerun the unchanged matcher. All seven return no candidate.
Only the two positive reads, both Seven Oaks, make this control informative;
the other five already return no candidate against the full catalog. This is
not seven independent unknown wines or an estimate of general false-positive
rate. Expected identities are used only to construct the control and score
results, never to select positive candidates or preprocess images.

This set still lacks physical-phone images, glare/blur, non-English labels,
non-vintage labels and real out-of-catalog wines. Stop tuning these seven images.
The next evidence step needs held-out phone/unknown-wine samples or an independent
OCR/recognition engine with deliberately configured access, followed by the same
candidate/vintage checks. No paid service or external image upload was enabled.

## Reproduce and validation

With the R03a Docker image built, from the repository root:

```powershell
uv run --project apps/api --locked python scripts/evaluate_label.py --psm 11 --preprocess
```

Omitting `--preprocess` preserves the original default. Only hash-checked public
fixtures enter preprocessing, which runs on the host using the existing pinned
Pillow development dependency. JPEG/PNG, byte/pixel limits, minimum dimensions,
single-frame input and output limits are checked; metadata is removed. This is
not a sandbox for arbitrary public uploads. OCR retains its isolated container,
network denial, resource/time limits and explicit cleanup. No runtime dependency,
application API, upload policy or frontend behavior changes.

Twenty-one focused unit cases and two real-container integration cases pass.
They cover deterministic bounded output, EXIF rotation, malformed/oversized
inputs, removal of all releases in a withheld offering, both observed match
sets, vintage ambiguity, blank/malformed OCR input and container cleanup.

Primary guidance checked October 21:
[Tesseract image quality](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
and [Pillow ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html).
