# Wine identities and curated catalog

`WineDefinition` and `WineRelease` remain owner-only provisional identities used by the journal. `CatalogDefinition`, `CatalogRelease` and `CatalogSource` hold operator-reviewed public facts. No query or ordinary journal payload promotes one into the other. See [ADR 0007](../../../../../docs/decisions/0007-public-catalog-boundary.md).

## Guest reads

`GET /api/v1/catalog/wines` accepts `q` (at most 200 characters), `limit` (1–48,
default 24), and `offset` (0–10,000). Space-separated terms must each match the
name, producer, edition or year. Matching is case-insensitive and SQL wildcard
characters are literal. Ordering is producer/name, newest vintage, edition, then
release UUID. The response includes `items` and `nextOffset`; offset paging is
appropriate to this small curated catalog and is not a snapshot across imports.
Search indexing/keyset pagination should be revisited if the catalog grows.

`GET /api/v1/catalog/wines/{release_id}` returns that exact public release and
up to 20 distinct source references with their latest retrieval dates. URLs are
validated again before returning them; invalid references are omitted. A source
reference is not a purchase offer or a claim of verified specifications.

Both endpoints are anonymous, bounded, read-only and `no-store`. Their explicit
response schemas contain only public identity/source fields. Queries never join
owner-scoped tables. The Next server calls this API without forwarding cookies or
authorization, through the existing configured API origin and a five-second
timeout. No new environment variables or provider keys are needed.

## Capture a public release

After migration 0023, `POST /api/v1/entries` accepts `catalogReleaseId` as an
exclusive alternative to `manualWine` or the existing owned `releaseId`. The
ordinary authentication, date, optional notes/occasion and idempotency rules
apply. A public UUID is never accepted as a private `releaseId`.

The first save creates an owner-scoped identity snapshot linked to that public
release; repeats reuse it. An account row lock is taken before occasion/wine
locks, and a unique `(owner_id, catalog_release_id)` constraint protects against
concurrent duplicate identities. NULL links preserve all existing manual wines.
Matching names never merge manual wines or different releases. Catalog facts
changing later do not silently rewrite personal history.

The link is inserted with the private release. Existing runtime permissions
still forbid release UPDATEs, and public tables remain SELECT-only. Missing
catalog selections roll back the new occasion, identities, entry and receipt
together. Downgrade is refused while catalog links exist; retain the additive
schema if rolling back application code.

## Import a reviewed batch

From the repository root, after applying migration 0022:

```powershell
uv run --project apps/api --locked python scripts/seed_catalog.py assets/evaluation/manifest.csv
uv run --project apps/api --locked python scripts/seed_catalog.py assets/evaluation/manifest.csv --apply
```

The first command previews counts; only `--apply` commits. Use the existing ignored `apps/api/.env.migrations` (`WINE_JOURNAL_MIGRATION_DATABASE_URL`) or an environment-injected value. Never pass a connection string on the command line or place migration credentials in web/runtime configuration. The command validates the database role and emits aggregate JSON, or a sanitized error class with exit status 1. No credentials, input values or driver error messages are printed.

`definitions`, `releases` and `sources` count **new** rows, with `applied` indicating whether they were committed. A repeat of an unchanged batch returns zero new rows. Preview counts are a point-in-time plan; apply revalidates against the database. No deletes, updates, source fetching or publication of private data occur. A conflicting definition key/name/producer aborts the entire batch and requires curator review; do not change the key just to bypass a conflict.

The [fixture contract and source review](../../../../../tasks/identification-evaluation.md) describe the accepted UTF-8 CSV columns. Limits are 1 MiB and 1,000 rows. Reject duplicate fixture/release identities, inconsistent definition names, malformed years, future retrieval dates and credential/query-bearing source URLs. All supplied fields are validated before database access. The CSV fixture IDs are evaluation references and are not stored as catalog IDs. Identity UUIDs remain stable across imports; source evidence is retained by release/URL/date. R01a only establishes identities, not full specifications, current stock, prices, artwork or recognition accuracy.

Imports run in one transaction with bounded table-lock acquisition. The API role may read these three tables but cannot write or truncate them. No endpoint invokes the importer. Migration rollback refuses populated catalog data; retain the additive tables when rolling back application code.

Tests use the disposable Postgres runner, including the standalone CLI:

```powershell
uv run --project apps/api --locked python scripts/run_api_tests.py tests/integration/test_catalog_import.py tests/integration/test_database.py -q
```

Guest browse/search and explicit catalog-to-private capture are C02 work. There is no UI change in C01.

## Reviewed barcode evidence (C04a)

After migration 0026, `CatalogBarcodeObservation` stores source-backed retail
GTIN associations to public **definitions**, not releases. The same code may
have several sources, sizes or offerings; later lookup must preserve ambiguity.
Even a single matching catalog release is not proof of barcode/vintage uniqueness.
See [ADR 0008](../../../../../docs/decisions/0008-curated-barcode-evidence.md).

From `apps/api`, using the existing ignored migration configuration:

```text
uv run --locked python ../../scripts/seed_barcodes.py ../../assets/catalog/barcode-evidence.json
uv run --locked python ../../scripts/seed_barcodes.py ../../assets/catalog/barcode-evidence.json --apply
```

The first command only previews. Output fields `observations` and `package_codes`
count new evidence rows and new distinct codes, not recognized wines. The reviewed
batch adds five observations for four codes; an unchanged repeat adds zero. Public
definitions must already exist with matching producer/name. No private wine or
new catalog identity can be created through this command. Migration credentials
remain server/operator-only, never command-line arguments or frontend variables.

Input is a UTF-8 JSON array capped at 64 KiB/100 rows. All fields are required:
`gtin`, `definition_key`, `producer`, `wine_name`, `bottle_ml`, `source_url`,
`retrieved_on`, `market`, `evidence_status`, `source_sha256`. Reject extra fields,
including year/release selection. GTIN is a string with a valid checksum and
normalizes to 14 digits. Leading-zero equivalents compare equally; nonzero
GTIN-14 packaging indicators are out of scope. Eight digits mean EAN-8, not UPC-E.
Source URLs use the existing HTTPS/credential/query restrictions and are never
fetched. Retrieval dates cannot be in the future. Market remains UNVERIFIED.
WEB_TEXT requires a null hash; PRODUCER_WEB_IMAGE requires the original source's
lowercase SHA-256, not a resized evaluation derivative's hash. The hash records
curator evidence; the importer does not independently verify the remote image.

The evidence key is `(gtin, definition, source URL, retrieval date)`. Conflicting
size/kind/hash under that key aborts the entire batch; it never overwrites stored
facts. Separate sources can disagree and remain separate evidence for future
candidate review. Duplicate normalized evidence within a batch is rejected.
Imports serialize with catalog changes using bounded locks and commit atomically.
Runtime has SELECT only; no public endpoint or scanner consumes this table yet.
Populated evidence prevents downgrade. Roll back application code while retaining
the additive schema; retraction/correction needs an explicit curator workflow.
