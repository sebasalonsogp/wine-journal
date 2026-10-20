# Barcode coverage checkpoint

October 20, 2026. The expanded set exposes a decoder miss and missing provider
data. **Do not adopt Open Food Facts as the primary wine-identification source.**
Keep curated text/manual capture available and pursue reviewed catalog barcode
associations as the next lookup design. R01b/R02 are still open; this is a failed
coverage gate with useful evidence, not a launched scanning feature.

## Inputs and provenance

[Ridge image manifest](../assets/evaluation/barcode-images-ridge.json) records
four independently reviewed rear-bottle images:

| Image | Producer source | Visible UPC | Reference |
| --- | --- | --- | --- |
| I004 | [2023 Geyserville](https://www.ridgewine.com/wines/2023-geyserville/?trade=1) | `744442301003` | W008 |
| I005 | [2023 Three Valleys](https://www.ridgewine.com/wines/2023-three-valleys/?trade=1) | `744442081004` | W014 |
| I006 | [2023 Estate Chardonnay](https://www.ridgewine.com/wines/2023-estate-chardonnay/?trade=1) | `744442479009` | W006 |
| I007 | [2023 Monte Bello](https://www.ridgewine.com/wines/2023-monte-bello/?trade=1) | None visible in this image | W002 |

The linked pages supply the rear-image URLs recorded in the manifest. The image
server initially returned 403 with the default client; it served the assets to
the identified WineJournalEvaluation client. Printed digits were read before
decoder/provider evaluation and checksum-validated. A misread Chardonnay digit
failed checksum validation and was corrected by inspecting the original pixels,
not by copying a provider answer. All labels show 750 ml and a 2023 vintage;
bottling dates in 2024/2025 are separate facts. No physical bottle or distribution
market was verified. No barcode in one image does not prove none exists elsewhere
on the bottle or its packaging.

Original images were 16–20 megapixels. To retain the existing four-million-pixel
decoder limit, whole images were reduced to a 2500-pixel long edge with Pillow
12.3.0 `thumbnail((2500, 2500), Image.Resampling.LANCZOS)`, then saved as JPEG,
quality 90, subsampling 0, with no copied metadata. The manifest records original
dimensions/hash, the exact transformation and the committed derivative hash.
These are explicitly derived producer assets, not camera photographs or generated
barcodes. No cropping or geometry correction was applied to the test inputs.

Combined with the earlier Seven Oaks set: **seven images, five offerings, two
producers, four distinct visible UPCs, two no-barcode views, zero physical-camera
observations**. This small convenience sample is not representative market coverage.

## Measured outcomes

[Decoder report](../assets/evaluation/barcode-decoder-ridge-results.json):
Geyserville and Chardonnay decode correctly after a quarter turn; Three Valleys
does not decode in either orientation. Monte Bello correctly yields no result.
There are no incorrect decoded codes or network requests. Two of three positive
images succeed in this batch; this is not a population success rate. Tilt,
curvature and downsampling may contribute to the miss, but this experiment does
not isolate the cause. The CLI exits nonzero for that miss; its expected UPC was
not removed or changed to make the run pass. CI continues to run the original
supported set, not this explicitly failing research batch.

[Provider report](../assets/evaluation/barcode-probe-ridge-results.json): three
bounded public GETs, separated by the existing quota delay, all returned explicit
NOT_FOUND (500, 125 and 125 ms). The [input observations](../assets/evaluation/barcode-observations-ridge.json)
were supplied directly, independently of the decoder miss. No images, journal
data or credentials were transmitted. No retries or further provider requests
were made. These are single-call timings, not latency percentiles.

Across both provider batches, four unique codes yielded one unverified product
and three misses; **zero confirmed wine releases**. A provider miss does not mean
the wine is invalid or absent from our curated catalog. Conversely, one source
image linking a code to 2023 does not prove the code uniquely identifies 2023.

## Reproduction and next decision

From `apps/web`:

```text
npm run evaluate:barcode -- --manifest barcode-images-ridge.json
```

Expected current exit: **1**, with a JSON report marking I005 as failed. The
original `npm run evaluate:barcode` remains green. Manifest selection is confined
to named files under evaluation assets, capped at 64 KiB; image bounds and hashes
remain unchanged. Reports now include the manifest filename and hash.

From `apps/api`, offline preflight makes no provider requests:

```text
uv run --locked python ../../scripts/evaluate_barcode.py ../../assets/evaluation/barcode-observations-ridge.json
```

Only add `--live` deliberately to repeat the three quota-limited public reads.
Preserve historical reports rather than silently replacing them.

Next: design a curator-controlled barcode association import with provenance,
package size and offering-level ambiguity; unknown codes must fall back to
text/manual capture. Never publish provider responses or infer the latest vintage.
Before camera rollout, compare close-up/framing behavior on independent inputs,
include EAN/non-vintage/out-of-catalog examples and test a physical iPhone over a
secure origin, including denial, cancellation, track cleanup and manual recovery.
No paid-provider commitment or production integration is introduced by this result.

Verification: all 43 barcode unit tests, backend Ruff/mypy, frontend lint and the
original offline decoder check pass. The new offline preflight retains source
identity without network requests or release confirmation. The expanded decoder
gate fails honestly on I005. Production code, dependencies and schema are
unchanged; the previous build and 34-browser-journey evidence is retained.

## C04a import foundation — October 20

[ADR 0008](../docs/decisions/0008-curated-barcode-evidence.md) now implements the
curated association decision. Migration 0026 adds public offering-level evidence
with no release/year binding. The [reviewed seed](../assets/catalog/README.md)
contains five observations for four codes; source URLs, retrieval dates, package
sizes and original image hashes retain provenance. Two Seven Oaks observations
remain independent sources for the same offering across different vintages.

The offline CLI defaults to preview, rejects conflicting or invalid batches and
serializes imports with bounded locks. Repeated/concurrent imports preserve IDs
and insert each observation once. No private records, network requests, new
environment variables or dependencies are introduced. Runtime can only read;
provider-managed roles have no access. Populated evidence prevents downgrade.

Verification: all **485 API tests** pass with disposable Postgres, real local
Storage and Docker-isolated photo decoding, including 22 new import tests. Fresh
migration/metadata/downgrade checks, CLI error redaction, atomic rollback,
normalized duplicates, conflicting sources and role grants pass. An inverted
apply guard fails the preview-write assertion (five stored rows instead of zero);
byte-for-byte restoration passes the same test. Ruff, formatting, mypy and backend
package build pass; regenerated OpenAPI is unchanged.

Local migration/import: preview 5 observations/4 codes, apply 5/4, repeat 0/0.
Journal, catalog-release and media counts plus unsettled holds are unchanged.
C04a completes only the import foundation. C04b still needs the bounded lookup
contract, source revalidation, explicit correction/retraction and release
confirmation. C05 still requires physical-camera evidence and UI. Parent task
completion remains 31/59; the existing frontend development audit blocker remains.
