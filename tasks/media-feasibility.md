# R04: Photo conversion feasibility

Completed September 30, 2026. **Pillow 12.3.0 + pillow-heif 1.8.0 is the selected candidate for the photo worker.** The tested Windows wheel bundles libheif 1.23.4. The experiment is isolated in development tools; it does not enable uploads, read application credentials or add a production handler. Storage authorization remains M02 and production processing remains M03.

## Evidence

The [manifest](../assets/evaluation/photo-manifest.json) pins nine public upstream files by commit and SHA-256. Fourteen additional files are generated locally: eight JPEG orientations, one HEIC orientation, a synthetic 48 MP JPEG, byte/dimension violations, a disguised SVG and a deliberately truncated real HEIC. Inputs and derivatives stay in ignored `.tools/`; only source references and numeric results are committed.

**All 23 fixture outcomes matched expectations.** The full API suite passes **123 tests**, including 25 new cases: all eight rotations/mirrors for both JPEG and HEIC, GPS/XMP removal, invalid content, byte/pixel bounds, malformed profiles, truncated JPEG/HEIC and subprocess time/memory cutoff. Input fixtures deliberately contain synthetic GPS and descriptive metadata; tests verify it exists before conversion and disappears from both output formats. No real GPS coordinates are recorded in the report.

Measured on this Windows development machine with Python 3.12.14, one process per file, one HEIF decoding thread, and no warm process reuse:

| Input | Dimensions | Wall time, including process startup | Peak process-tree memory | JPEG + WebP bytes |
|---|---|---:|---:|---:|
| iPhone 8 Plus arrow HEIC | 3024 × 4032 | 828 ms | 166.5 MiB | 305,023 |
| iPhone 13 Pro pug HEIC, GPS present | 4032 × 3024 | 875 ms | 166.3 MiB | 294,652 |
| Sony rotated guitar HIF | 4672 × 7008 | 2,734 ms | 547.9 MiB | 171,782 |
| Synthetic 48 MP JPEG | 8064 × 6048 | 672 ms | 279.1 MiB | 50,171 |

The [complete results](../assets/evaluation/photo-results-windows.csv) include a 10-bit HEIF, a spatial photo's primary image, corrupt/truncated files and a rejected 200 MP image. Device labels above come from public fixture EXIF. The arrow, dog, guitar and synthetic rotated-chart derivatives were visually inspected. Pixel-corner assertions independently verify every synthetic orientation.

Memory sampling includes the Windows venv launcher's decoder child; measuring just the launcher incorrectly reported about 5 MiB and was discarded. Windows process high-water marks are included; other systems use 20 ms RSS samples, which can miss brief peaks. These figures are one-run observations, not production percentiles or hosting capacity guarantees. Removing redundant full-size copies reduced the synthetic 48 MP path from about 651 MiB to 279 MiB.

## Processing decision

- Identify content through a restricted decoder list: JPEG, PNG, WebP and HEIF. Filename/MIME claims do not establish validity. Keep libheif security limits and strict Pillow truncated-image behavior enabled; do not decode depth/auxiliary images or embedded thumbnails.
- Decode the selected primary still image fully. HEIF container rotation is handled by the plugin; apply EXIF transforms for other inputs without rotating HEIF twice. Live Photo motion, burst browsing and spatial/depth presentation are separate features.
- **Do not rely on `verify()` or successful decode alone.** The experiment found that libheif can conceal missing tiles in a truncated HEIC and still return pixels. Validate top-level ISO BMFF box lengths before decoding. The previously accepted truncated secondary-frame fixture is also rejected because its container is structurally incomplete. This is a structural truncation check, not proof that every possible damaged bitstream is detected.
- Convert a valid embedded ICC profile to sRGB, flatten alpha onto white, preserve aspect ratio and avoid upscaling. Produce a JPEG with a maximum 2048 px edge at quality 85 and a WebP thumbnail with a maximum 480 px edge at quality 80.
- Rebuild derivatives from pixel-only images. No EXIF, XMP, source ICC, comments, device details, timestamps or embedded GPS are copied. Application-entered location remains independent.
- Treat output as an ordinary 8-bit display image. The successful 10-bit fixture proves decoding, **not** perceptually accurate HDR tone mapping or every wide-gamut/NCLX profile. No HDR fidelity promise is made. Recheck a recent physical iPhone's upload/export behavior and color appearance when the UI exists.

## Proposed initial limits for M02/M03

| Boundary | Starting value | Rationale |
|---|---|---|
| Source bytes | 20 MiB | Covers the tested originals while bounding upload/staging costs. |
| Dimensions | 50 million pixels; no edge above 10,000 px | Admits ordinary 48 MP dimensions; rejects the 200 MP fixture before pixel decoding. |
| Worker | One image at a time; 20-second deadline; 768 MiB process budget | Accommodates the measured 548 MiB HIF case with headroom. Recheck on the actual deployment host. |
| Stored derivatives | 5 MiB JPEG + 512 KiB thumbnail maximum | Explicit output caps for noisy images; reject/retry with a smaller rendition if exceeded. These caps are proposed, not enforced by this experiment. |
| Account storage | 100 MiB; at most 100 photo assets | Conservative portfolio starting point, configurable. Staging, originals and derivatives all count until actually deleted. |
| In-flight reservations | Two photos per account | Reserve source allowance plus derivative allowance atomically before issuing upload permission. |

These are starting engineering defaults rather than a promise that every file under a limit will succeed. A complex 48 MP HEIC could exceed memory even though the synthetic JPEG did not. For free hosts with less memory, reduce the accepted pixel limit or use the local worker; do not silently remove the memory guard. The experiment's sampled kill guard is not a hard sandbox: M03 must use OS/container memory limits, bounded subprocesses and safe output publication. Native decoders must remain outside the API request process.

Recommended original-retention policy: keep staging private while processing; make only validated derivatives viewable; delete the original after successful publication unless a later explicit original-download feature needs it. Failed/cancelled and abandoned uploads need expiry and idempotent cleanup in M08. Persist journal text independently of photo success. Validate account/global quotas against the actual storage plan before a hosted demo.

Suggested recovery copy:

- Byte/pixel limit: “This photo is too large. Export a smaller JPEG or HEIC and try again. Your wine entry is saved.”
- Invalid/truncated/unsupported: “We couldn't read this photo. Try the original file or export it as a JPEG.”
- Profile/resource limit: “We couldn't process this photo. Try a smaller JPEG export.”
- Motion/spatial media: present only the primary still; never imply the associated motion or depth was saved.

## Reproduce

From the repository root, with the development dependencies installed:

```sh
uv sync --directory apps/api --locked
uv run --directory apps/api --locked python ../../scripts/prepare_photo_samples.py
uv run --directory apps/api --locked python ../../scripts/evaluate_photos.py
uv run --directory apps/api --locked pytest tests/unit/test_photo_evaluation.py
```

The preparation command downloads only checksum-pinned public upstream fixtures and creates synthetic cases. It requires a fresh output directory and never overwrites existing photos. For another run, use `--output` on preparation and matching `--samples` plus a new `--output` on evaluation. A mismatched expected outcome exits nonzero. Reports contain fixture IDs, dimensions, timings, memory and output byte counts, not file metadata or credentials. Native dependencies are currently development-only; promote the selected processing dependencies when M03 moves this proven path into the media module.

R04 resolves the decoder choice and establishes reproducible evidence. Windows results do not certify Linux resource limits, Safari file-picker behavior, recent iPhone HDR fidelity or storage integration. CI runs the generated functional cases on Linux; R07 and the media UI/device checks own those remaining operational/experience questions.

Sources: [upstream fixtures](https://github.com/bigcat88/pillow_heif/tree/b16be1196dfa465a342d68894696e685ca3655cb/tests/images), [HEIF orientation behavior](https://pillow-heif.readthedocs.io/en/stable/workaround-orientation.html), [decoder options](https://pillow-heif.readthedocs.io/en/stable/options.html), [Pillow image limits](https://pillow.readthedocs.io/en/stable/reference/Image.html), [ICC conversion](https://pillow.readthedocs.io/en/stable/reference/ImageCms.html).
