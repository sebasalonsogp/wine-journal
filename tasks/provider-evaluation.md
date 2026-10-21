# Barcode evaluation checkpoint

October 20, 2026. **R02a is complete: bounded package-code preflight and a public
product-data probe. R01, R02 and C04 remain open.** No camera control, production
lookup endpoint, automatic catalog match or journal mutation is added.

## Independently sourced inputs

[Two web-text observations](../assets/evaluation/barcode-observations.json)
refer to one normalized package code, not two independently scanned bottles:

| Observation | Evidence | Expected reference |
| --- | --- | --- |
| B001 | [Producer's Seven Oaks product sheet](https://sites.salsify.com/ac717bbc-c69e-474f-ba68-2f08ae725959/cfdbf0ab-2c72-459e-b846-5473ab4b1d68/product/CSES2375/J--Lohr-Estates-Seven-Oaks-Cabernet-Sauvignon/): 2023, 750 ml, UPC `089121288122` | W016 |
| B002 | [Retailer's Seven Oaks listing](https://www.thefreshgrocer.com/sm/pickup/rsid/486/product/j-lohr-2022-seven-oaks-paso-robles-cabernet-sauvignon-750-ml-id-00089121288122): 2022, 750 ml, code `00089121288122` | W015 |

Both normalize to `00089121288122`. The listings associate the same code with
different vintages; they do not establish which bottle a person currently holds.
The retailer page is a historical listing, not evidence of current stock or
price. These are source claims, not photographed/physically verified bottles.
At this initial text checkpoint, market remained UNVERIFIED, symbology had not
been observed, and no source image had been downloaded or decoded. The image
checkpoints below and [expanded coverage report](barcode-coverage-checkpoint.md)
record subsequent evidence. Expected fixture IDs remain separate from
provider output and are checked against the existing identity manifest.

## Observed provider result

[Recorded result](../assets/evaluation/barcode-probe-results.json): one bounded
Open Food Facts API v3 request returned in **453 ms**, with product name
`Cabernet Sauvignon`, brand `J. Lohr`, and no quantity. The provider normalized
the code to its equivalent 13-digit representation. Outcome:
`PRODUCT_FOUND_UNVERIFIED`; **zero confirmed wine releases**. The result does
not supply the Seven Oaks designation or a verified vintage.

This is one package-code observation, not a coverage percentage, latency
percentile or recommendation to adopt the provider. Two public read requests
were made during this work: an initial protocol inspection and the recorded
tool run. Neither posted images or journal data. Automated tests use synthetic
transport responses and never depend on provider availability.

The current [provider documentation](https://raw.githubusercontent.com/openfoodfacts/openfoodfacts-server/main/docs/api/index.md)
specifies 15 product reads/minute/IP, a custom User-Agent, unauthenticated public
reads, and no guarantee of completeness. The [v3 product contract](https://openfoodfacts.github.io/documentation/docs/Product-Opener/v3/products/get-api-v3-product-code/)
supports selecting returned fields. Recheck these limits before any application
integration. Use the documented staging environment for general integration
testing; the explicit live option here measures public-catalog observations.

## Repeat the experiment

From `apps/api`, using the locked development environment:

```powershell
uv run --locked python ../../scripts/evaluate_barcode.py ../../assets/evaluation/barcode-observations.json
uv run --locked python ../../scripts/evaluate_barcode.py ../../assets/evaluation/barcode-observations.json --live
```

The default validates and groups inputs without requesting the provider. `--live`
performs public reads only. Output goes to stdout; preserve an existing measured
report deliberately rather than overwriting the expected answers. Operational
outcomes are data in the report; exit zero means the report was produced, not
that recognition succeeded. Invalid input exits two without printing its contents.

- Input: at most 64 KiB, ten source observations and five distinct valid codes.
  Duplicate sample IDs, unknown expected fixtures, credentials in source URLs
  and future evidence dates are rejected. Source URLs are provenance, not fetch
  targets. The provider host is fixed.
- GTIN: ASCII digits stored as text, lengths 8/12/13/14, alternating check-digit
  weights and zero-padding for comparison. Reject all-zero placeholders, bad
  checksums, numeric values, whitespace, punctuation and Unicode lookalikes.
  A valid checksum is not proof of assignment or identity. A decoder must
  distinguish EAN-8 from compressed UPC-E before using the GTIN-8 branch; QR
  codes, UPC-E expansion and producer-specific identifiers are not implemented.
- Network: ten-second asynchronous deadline, five-second phase timeout, no
  redirects/retries, no environment credential/proxy inheritance, identity
  transfer encoding and a 64 KiB response limit before JSON parsing. Unknown
  fields are discarded, product text lengths are bounded, and both returned
  code fields must normalize to the requested code.
- Quota: deduplicate normalized codes within a run and space requests by at
  least 4.2 seconds. Stop the batch on timeout, rate limit or unavailability;
  report attempted and unattempted code counts. This is a single-process
  experiment, not a shared per-user/IP production rate limiter. Do not run
  concurrent live probes against the same provider quota.
- Outcomes distinguish unverified product facts, explicit no-match, malformed
  response, quota, timeout and service failure. Provider strings never create
  catalog records, infer a vintage or become bottle artwork.

GTIN rules follow [GS1's check-digit method](https://www.gs1.org/services/how-calculate-check-digit-manually)
and [leading-zero equivalence guidance](https://support.gs1.org/support/solutions/articles/43000734386-are-all-gtins-unique-numbers-).

## Remaining gate and next slice

R01b still needs independently reviewed label/barcode assets, real-camera
conditions, package/market observations, non-vintage and missing-year examples,
and out-of-catalog bottles. The two text observations do not complete that set.
R02b must choose/evaluate a browser decoder on those assets and a physical iPhone,
then measure lookup coverage and recovery across the set. C04 must add shared
request budgets, provenance and server-validated candidate selection only after
that evidence supports a viable route. Text/manual capture remains usable.

Verification: 42 focused tests cover GTIN variants/invalid inputs,
equivalent provider codes, mismatches, malformed and oversized JSON, compressed
responses, redirects, missing products, quotas, a true asynchronous deadline,
offline behavior and batch early stop. All **462 backend tests passed** with
disposable Postgres, local Storage and isolated photo decoding. Ruff, formatting,
mypy and the backend package build pass; exported OpenAPI is unchanged. An
inverted checksum guard failed the known-code tests as expected; restoring the
source byte-for-byte restored all 42 passing focused cases. The web was unchanged,
so the previous 35 unit/34 browser journey evidence was retained rather than
rerunning it. No dependency, secret, environment variable, database migration
or web route is introduced.

## R02b first image checkpoint — October 20

The [image manifest](../assets/evaluation/barcode-images.json) freezes three
producer-hosted assets with source URLs, byte hashes, dimensions and independently
read expected digits. These are two labels and one bottle rendering for **one
offering / one code**, not three bottles. Original downloaded bytes total about
482 KiB; reviewed metadata contains color profiles but no EXIF/XMP location data.
They are evaluation fixtures, not published catalog artwork or private photos.

The producer page identifies 2023 (W016), but none of these images visibly shows
a vintage. Image-only vintage remains UNKNOWN; the code's existing baseline
candidates remain W015/W016, without claiming those are the only possible years.
The front image is a genuine no-barcode input, not an out-of-catalog wine.
Package size is 750 ml; sales market remains UNVERIFIED.

The [offline Chromium report](../assets/evaluation/barcode-decoder-results.json)
tests `@zxing/browser` 0.2.1 with `@zxing/library` 0.23.0. These are pinned dev
dependencies, bundled from the lockfile with the existing esbuild version now
declared explicitly. The [upstream browser API](https://github.com/zxing-js/browser)
supports canvas decoding and camera controls; this experiment exercises only
canvas decoding. Production bundles do not import the evaluation modules.

| Input | Original orientation | Quarter turn | Expected result |
| --- | --- | --- | --- |
| I001 flat back label | No result | UPC-A `089121288122` | Printed digits agree |
| I002 full bottle back | No result | UPC-A `089121288122` | Printed digits agree |
| I003 front label | No result | No result | No barcode present |

The allowlist is UPC-A/EAN-13/EAN-8, excluding adjacent QR codes and unsupported
UPC-E/case formats. EAN support is configured, **not demonstrated by this UPC-only
set**. Each image is tested at 0° and 90° in memory, with a white background for
transparency. Rotation is a deterministic test transform, not a new camera sample.
Both positive inputs required rotation despite TRY_HARDER. Recommendation: keep
ZXing as a candidate and carry orientation recovery into the next experiment;
do not infer that arbitrary skew, blur or glare is solved.

In this desktop run the two attempts totalled about 73–74 ms per positive image;
these are single-run decode timings, excluding loading/drawing, not mobile or
end-to-end latency guarantees. There were zero network requests and zero resolved
wine releases. No provider calls, camera permissions or journal saves occur.

Reproduce from `apps/web` after `npm ci` and `npx playwright install chromium`:

```text
npm run evaluate:barcode
```

The fixed local manifest allows at most ten assets, 4 MiB and four million pixels
per asset; filenames, hashes and decoded dimensions are checked. A fresh offline
browser context blocks requests and service workers, with a 20-second browser
deadline. No account state is loaded. The script prints JSON and exits nonzero
for an unexpected code, missed positive, false positive, changed bytes or browser
failure. CI runs it after Chromium installation. It does not overwrite the frozen
report. To record a deliberately reviewed new measurement, run the Node script
directly and capture stdout without npm's banner.

Negative verification: altering a fixture hash, supplying a different expected
GTIN, and removing the quarter-turn pass each failed as expected. Sources were
restored byte-for-byte. Broader independent bottles, non-vintage inputs, actual
glare/skew/blur and a physical iPhone permission/cancel/retry test remain required.
R01b, R02, C04 and C05 remain open; parent progress stays **31/59**.

Verification for this slice: the restored offline decoder run, all 35 frontend
unit tests and all 34 browser journeys passed. Formatting, lint, types and the
production build pass. The built browser scripts contain no evaluation-module
markers; the private-value scan checked 20 scripts successfully. Production npm
audit reports zero vulnerabilities, and staged Gitleaks reports no secrets.
The backend is unchanged, retaining the previous 462-test evidence. Full web
audit still reports the existing development-only blocker below; no gate was
removed or relaxed.

## Dependency audit recheck

The October 20 recheck still reports five affected dependency nodes through
Next's lint plugin → fast-glob → micromatch → braces. The
[advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) still lists no patched
braces version; registry latest is 3.0.3. No forced framework downgrade,
dependency override or audit suppression was applied. This remains independent
of barcode feasibility and blocks merging the existing PR.
The prior correction commit `a117f13` passed API, browser and secret CI jobs;
its web job failed only at the full npm audit gate.
