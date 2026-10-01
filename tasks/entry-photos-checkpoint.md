# M04: Entry photos

M04 delivered, October 1, 2026. Backend associations and the browser photo journey are implemented and verified.

## Delivery slices

1. **Complete:** Owned entry/asset associations, captions, removal and generated API contracts.
   Verify cross-account combinations, concurrent/replayed writes, stale changes,
   database constraints and entry deletion against disposable Postgres.
2. **Complete:** Shared photo controls in capture and existing entries. Files can be selected
   before saving; saving text never waits for uploading. Keep the saved entry ID
   while retrying photos. Show pending, processing, ready and failed states.
3. **Complete:** Verify the phone-sized save/failure/retry/reload/remove journey and desktop
   layout; run regression, security and CI checks before closing M04.

## Boundaries

- Media owns attachments; journal owns entries. A same-owner foreign key protects
  each side. Entry deletion removes associations, not assets or quota reservations.
- An entry/asset pair is unique. Removed pairs retain a tombstone so a delayed
  attach retry cannot restore a removed photo. Caption/removal writes use their
  own revision and cannot overwrite entry text.
- At most 12 active photos per entry. Existing account storage reservations and
  two-in-flight upload limits also apply; M08 will reclaim storage safely.
- Files stay in browser memory during upload. No durable offline photo queue,
  original-file display, occasion albums, bottle covers or wine highlights here.
- Only processed private derivatives can be displayed. Do not persist signed
  URLs, credentials or image bytes in browser draft/query storage.

## Evidence

Migration 0014 adds composite owner constraints on entries and upload assets, plus
the media-owned entry_photos table. The API supports bounded listing, idempotent
attachment, versioned captions and removal. Runtime grants permit only the needed
mutable columns; anonymous/authenticated provider roles cannot read the table.
No provider calls or file processing happen inside attachment transactions.

The full local API suite passed 286 cases with real Storage and isolated Docker
processing enabled. The final focused attachment suite passed eight cases,
including two subsequently added concurrency/shared-reference cases. These cover
ownership combinations, disabled accounts, strict input validation (including NUL),
caption conflicts/replays, removal tombstones, entry deletion, shared assets,
concurrent duplicate attachment and last-slot enforcement, runtime grants and
migration downgrade/upgrade/model drift. All tests use disposable Postgres.

Ruff, formatting, mypy (105 files), API packaging, generated contract/type checks,
frontend lint/format/type checks and 21 frontend unit tests passed. Tracked-file
and browser-secret scans passed. Known non-failing warnings remain Starlette/httpx
deprecations and Windows pytest-cache permissions. CI evidence belongs to the PR.

Local migration 0014 preserved entry, occasion, wine and asset counts. Restarted
only the verified local API processes; liveness and My Wines returned 200, and the
new attachment route returned 401 without authentication. No database reset or
credential changes were needed.

## M04b delivered

Capture accepts photos in browser memory before text save. After the wine/date
save succeeds, the page retains that entry ID and uploads independently; it never
re-POSTs an entry to retry a photo. Existing entries expose a lazily loaded
Photos & memories section. Captions retain their starting version while editing;
removal affects only the current entry. Pending, processing, ready and failed
states are explicit, including replacement guidance for terminal decoder failure.

Upload retries keep the operation key and asset ID, check authoritative completion
before resending bytes, renew expired grants and never upsert. Storage requests
omit journal authorization and cookies. READY thumbnails are fetched without
caching and displayed through temporary blob URLs, revoked on unmount. Selected
files and capabilities are not persisted in draft/query storage. Polling is
bounded to five minutes with a manual refresh afterward. Guest capture remains
usable without photos before sign-in.

Session focus checks hide/inert the existing subtree while retaining same-account
work. A different account remounts it; sign-out clears media and bypasses unsaved
photo navigation guards. The local preview uses the production build. No new
migration or credential change was needed for M04b.

Verification: 27 frontend unit cases pass, covering failed/lost upload responses,
lost completion, expired grants, stable identities, aborts and file validation.
All 20 browser scenarios pass in the final full regression run. The new journeys
use real local Auth, API, private Storage
and the isolated decoder with synthetic images: phone text save during upload
failure, retry without a duplicate entry, caption persistence, reload/removal,
later attachments, decoder failure, visibility recheck and cross-tab sign-out.
Headless tab activation did not emit visibilitychange, so the regression test
explicitly drives that browser event and verifies an actual account recheck.

Desktop/390px visual inspection and axe checks passed after one correction batch
for caption borders and contained image sizing. Build, lint, formatting, TypeScript,
dependency audit and tracked/browser secret checks passed. Impeccable's unavailable
context loader was not retried; the incumbent design system was preserved.

Limitations: this is online capture with in-memory photo selections, not durable
offline upload. Account reservations still limit preview storage, and removing
a reference does not release storage until M08. Physical iPhone/HEIC browser UX
remains a device acceptance check; backend HEIC conversion is already tested.
M05 personal bottle covers is the next backlog task.
