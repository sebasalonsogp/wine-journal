# Curated barcode lookup and confirmation

Both operations are guest-accessible, read-only POSTs under `/api/v1/identification`.
POST keeps scanned values out of URL/access logs. Responses are `Cache-Control:
no-store`; no tokens, private journal data, source images or codes are sent to a
provider. The Open Food Facts probe remains a separate evaluation tool.

## Contract

`POST /barcode-lookups` accepts `{"gtin":"089121288122"}`. Strict digit/checksum
validation normalizes GTIN-8, UPC-A, EAN-13 and leading-zero GTIN-14 equivalents.
UPC-E must be expanded by a supported decoder first; nonzero case indicators are
unsupported. Invalid/extra fields return 422 without echoing submitted values.

The response contains `gtin`, `status`, and `candidates`:

- `NEEDS_CONFIRMATION`: one or more offering candidates. Each includes
  `definitionId`, `name`, `producer`, `bottleSizesMl`, public `sources` (URL/date)
  and `releases` using the existing public catalog wine shape. A single release
  still needs confirmation. The catalog may not contain the bottle's year.
- `NOT_FOUND`: no usable curated evidence; offer text search/manual capture.
- `TOO_MANY_MATCHES`: bounded result exceeded; no partial candidates are returned.
  Offer text search rather than treating the first page as a unique match.

Candidates sort by producer/name/ID, releases by descending year then edition/ID.
Source and size lists are deterministic. Different offerings/sizes remain visible.
No automatic selection, confidence score, market availability or year inference.
An offering with no releases may still appear; it requires text/manual continuation.

`POST /barcode-confirmations` requires all five fields:

```json
{
  "gtin": "089121288122",
  "catalogReleaseId": "<selected release UUID>",
  "vintageStatus": "YEAR",
  "year": 2022,
  "edition": null
}
```

For `NON_VINTAGE`/`MULTI_VINTAGE`, pass `year: null` and the exact edition (or null).
Read current evidence again and require the release to belong to a candidate with
the same vintage status, year and edition. Missing, unrelated, private, retracted
or changed selections return 409 `BARCODE_SELECTION_CHANGED`. Successful selection
returns existing `CatalogDetails`, not a saved entry or persistent verification
token. Clients must ask the user to inspect the bottle, and never choose the first
release automatically. No API can prove the user physically checked the label.

The authenticated journal save continues to accept `catalogReleaseId` through its
existing catalog path and idempotency rules. This confirmation is not an auth
capability, nor does it prohibit deliberate text/manual catalog selection. A later
curator retraction does not rewrite already saved private snapshots.

## Bounds and operating assumptions

The guard runs before JSON parsing: 4 KiB actual body bytes (including chunked
bodies), 5 seconds to receive a body, 30 requests per observed network peer per
rolling minute, and 120 total per API process. Lookup and confirmation share limits;
invalid inputs count. Rate failures return 429 and `Retry-After`; oversized bodies
return 413, receive timeouts 408. Counters are locked, bounded to at most 120 active
peers, expire after a minute and reset on process restart. There is no persisted
IP/account history. Guests and signed-in callers use the same public allowance.

These are local process guards, not distributed quotas or account-specific limits.
Before public deployment, enforce shared ingress limits, request/header/connection
limits and trusted proxy configuration. Do not trust arbitrary forwarded headers.
Users behind the same NAT/proxy share a peer budget; web proxying must account for
this. Multiple workers multiply the aggregate allowance until ingress enforces it.

Database queries use a 3-second statement timeout and bounded reads: at most 100
source observations, 10 offerings and 240 total release options. Overflow asks for
text search. Lookup/confirmation use a read-only repeatable-read snapshot; a
completed retraction is seen on the next request, while an overlapping request may
complete on its earlier snapshot. Database failures return sanitized 503 with a
five-second retry hint. No request creates accounts, catalog rows or journal entries.

Stored evidence is revalidated against the importer rules, including safe source
URLs and dates, before use. Invalid observations are omitted; no source URLs are
fetched or claimed freshly checked. Source dates remain visible. The exact-match
curator retraction workflow is documented in [catalog](../catalog/README.md).

Browse Wines now uses these operations for guest barcode-number input and explicit
release confirmation. The browser calls the public API directly without session
credentials, respects Retry-After, and continues through existing catalog details
and deliberate journal capture. Camera UI, physical-device verification and
recognition outside the curated seed remain separate.
