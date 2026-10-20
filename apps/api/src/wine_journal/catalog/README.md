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

The first browser slice supports guest search/details. Catalog-to-journal saving
is a separate C02b step: never submit a catalog UUID as a private `releaseId` or
silently turn a public selection into a new manual identity.

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
