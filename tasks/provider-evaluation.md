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
Market remains UNVERIFIED, symbology has not been observed, and no source image
has been downloaded or decoded. Expected fixture IDs remain separate from
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

## Dependency audit recheck

The October 20 recheck still reports five affected dependency nodes through
Next's lint plugin → fast-glob → micromatch → braces. The
[advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) still lists no patched
braces version; registry latest is 3.0.3. No forced framework downgrade,
dependency override or audit suppression was applied. This remains independent
of barcode feasibility and blocks merging the existing PR.
The prior correction commit `a117f13` passed API, browser and secret CI jobs;
its web job failed only at the full npm audit gate.
