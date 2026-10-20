# C02a — Guest catalog search and details

October 20, 2026. C02 is split into public reading (C02a) and explicit
catalog-to-private capture (C02b). The parent task is not complete.

## Delivered behavior

- Browse Wines searches the 30 reviewed public releases by wine, producer, year
  and edition. Results have stable ordering and bounded 24-item pages.
- A release opens its own page; two vintages or editions keep different IDs.
  Returning to results preserves the query and page.
- Guests can read without an account. No read creates a drinking entry or
  exposes personal notes, covers, ratings, occasions or profile data.
- Detail pages show sourced identity and dated producer references. Missing
  origin/grapes, tasting notes, artwork and offers are clearly unavailable.
  No seeded recommendation, popularity, price or purchase availability is invented.
- Empty, malformed-query, missing-release and unavailable-service states offer
  recovery. Missing releases use Next's not-found/noindex handling.
- Existing manual capture remains available; a catalog selection is not
  silently copied into an unlinked manual wine.

## Boundaries and implementation

Public SQL reads only the catalog tables introduced by C01. Response schemas
explicitly allow identity/source fields. Search escapes SQL wildcards, bounds
query length/page size/offset, and sets a three-second statement timeout.
Detail references are deduplicated by URL using the latest retrieval date and
validated again at the public boundary; at most 20 are considered.

Next uses server rendering and a typed API client with a validated configured
origin, five-second timeout, no redirects, no-store and no forwarded credentials.
It does not query Postgres or reuse the authenticated journal transport.
The existing burgundy/olive/cream theme and primary Browse navigation remain.
No new dependencies, database migration, environment values or secrets.

Offset pagination is a deliberate small-catalog choice, not a snapshot while
operators import new rows. Large-catalog indexing/rate controls belong to scale
and deployment readiness. This change does not claim barcode/label recognition.

## Verification

- All 404 API tests passed with disposable Postgres, real local Storage and the
  isolated photo decoder. The public catalog adds ten cases; its import/read
  suite has 34 cases. A focused rerun also verifies that private release UUIDs
  return 404 at the public endpoint.
- All 34 frontend unit tests pass. Ruff, formatting, mypy, frontend lint/types,
  production build, generated API contracts and backend package build pass.
- The 25 existing browser journeys pass. The new guest catalog journey passes
  after correcting two test locator ambiguities during route/metadata streaming.
  Desktop/390px screenshots were inspected; list/detail axe checks have no
  violations, and the phone view has no horizontal overflow.
- Impeccable's detector reports no findings. The browser secret scan checked 19
  scripts and found no generated private values. Production npm audit reports
  zero vulnerabilities.
- Full npm audit still reports the existing braces advisory through Next's
  development lint chain (five affected package nodes). No forced Next 14 lint
  downgrade or suppressed audit gate. The previous head's API/browser CI jobs
  passed; its web job failed only at full npm audit.

Browser CI now seeds the same reviewed identities into its disposable database
before testing. Tests and screenshots use public references or synthetic private
records only. The PR remains unmerged while the full audit blocker is open.

## Follow-up: C02b (completed October 20)

The scope below is now implemented and verified in the
[catalog capture checkpoint](catalog-capture-checkpoint.md). C02 is complete;
C03 private identity correction is next. The earlier verification above records
the C02a implementation independently.

Add an explicit public-release link to an owner-scoped wine, preserving existing
owner constraints. Repeated saves of one catalog release should reuse that
owner's wine; different vintages must stay separate. Manual identities must not
be automatically merged by matching names.

Extend capture with an exclusive catalog selection and preserve it across
sign-in, existing-draft decisions, account changes and idempotent retries.
Absent new fields must not change hashes of existing save requests. Verify
guest lookup → capture → sign-in → save → repeat, two-account isolation and
two vintages before marking C02 complete.
