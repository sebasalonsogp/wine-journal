# M06 — Occasion scrapbook

Status: M06a backend and M06b browser behavior implemented October 12, 2026.
Functional acceptance passes; parent closeout remains pending the documented
development dependency audit blocker. M07 wine highlights is the next product slice.

## Slices

1. **M06a — attachment and album contracts:** migration 0016 and OccasionPhoto model;
   occasion attachment service/routes; deduplicated album and paginated source reads;
   generated OpenAPI/client types; disposable Postgres tests. Verify exact asset
   membership, ownership, caption/retry rules, concurrency, unlink/deletion and
   rollback before committing.
2. **M06b — scrapbook controls:** occasion uploads, private processed previews,
   caption/removal controls for occasion-owned references, source navigation for
   inherited entry photos, bounded pagination and polling. Reuse media upload,
   thumbnail and session/navigation behavior. Verify real upload/retry, membership
   changes, sign-out, desktop/mobile appearance and accessibility before checking M06.

M06b implementation was split into shared upload/caption/removal support and its
album UI consumer. Concrete files: media/photo-upload, photo-selection, photo-card,
occasion-album and album-sources; occasion-views, wine-detail, globals.css; unit
upload retries and the occasion-album browser suite. No backend migration was needed.

## Contract and ownership

Occasion-owned references are independent of entry photos and wine covers. A
same-owner composite foreign key protects each parent and asset. References have
captions, optimistic revisions and removal tombstones. Mutations serialize through
account then occasion locks, including capacity checks (24 active direct photos).
Pending/processing/failed images remain visible as metadata, using the same private
upload and decoder pipeline; originals and signed URLs are absent from album JSON.

The album includes active direct references plus active photos on entries currently
linked to that occasion. It deduplicates by asset ID before pagination and orders
by upload creation time descending, then asset ID ascending. A scoped cursor binds
to the owner and occasion. Each card contains its source count and a representative
source: occasion first, otherwise the entry with the lowest UUID. That ordering is
stable, not a claim about the relative importance of entry captions. All captions
and source IDs remain accessible through a separate paginated source endpoint.

Sources carry kind, parent ID, optional user-wine ID, caption and revision. The
browser can navigate to the source without receiving unrelated notes or paths.
Source pagination is a live offset list ordered by kind priority and parent ID;
clients reload it after link changes. Album pages default to 20, maximum 50.

Unlinking entries changes album membership without changing their attachments.
Deleting an occasion cascades only its direct reference rows; entry photos and
assets remain. Existing occasion deletion unlinks entries first. Physical storage
cleanup/reservation release remains M08, and no new album route deletes storage.
Cover-only assets and unlinked-entry photos are excluded. Deliberately attaching
the same owned asset as both cover and memory is still an explicit separate action.

## Verification

Seven focused Postgres tests passed: reference idempotency and stale captions;
same-owner constraints/grants; migration rollback; exact multi-entry/shared-asset
album fixture before/after unlink/deletion; scoped pagination and account isolation;
concurrent last-slot capacity; shared-reference removal and cover exclusion.
The full API suite passed all 300 tests with real Storage and the isolated Docker
decoder enabled. Frontend verification passed 28 unit tests, typechecking, lint,
formatting and a production build. API lint, formatting, strict typing and package
build passed. Existing OpenAPI paths/methods remain available. The built browser
assets contained no generated private credentials.

Local migration 0016 preserved entry, occasion, wine and asset counts. CI results
are linked from the pull request after publication.

## M06b browser acceptance

Saved occasions now display a single album with direct uploads, private processed
thumbnails, direct-photo caption editing/removal and paginated original sources.
Inherited entry photos are read-only here; source links open the precise entry in
its wine record, including entries beyond the first history page. The record checks
wine membership and offers a return to the full history. Selected files remain only
in memory, with the shared navigation guard and sign-out cleanup. Pending photos
poll every five seconds for at most 60 successful query updates; errors stop polling
and Reload album can request a fresh read. Album and source pages contain 20 items.

All 32 unit tests passed, including four additional occasion retry cases. All 24
browser scenarios passed across the full regression run and focused rerun: the
first full run passed 23 cases; the new long-history fixture initially used the
wrong request field, corrected to releaseId, and both album cases then passed.
The real Storage/Docker journey covers upload failure/retry without recreating an
occasion, stale caption drafts, two ready assets with three shared references,
standalone-photo exclusion, real API pagination, removal falling back to entry
sources, unlink/deletion preservation, exact source navigation and sign-out.

Desktop (1440px) and phone (390px) captures were visually inspected; overflow and
axe WCAG A/AA checks passed. Images in screenshots are synthetic pipeline fixtures,
not representative photography. Impeccable's detector returned no findings. Lint,
formatting, strict typing, production build and browser-secret checks passed.
Production npm audit reports zero vulnerabilities. Physical iPhone acceptance and
video remain future verification/work; the full development audit is still blocked
as documented below, so neither merge readiness nor complete CI success is claimed.

## Dependency audit follow-up (October 12)

The first CI run passed API checks but exposed new web dependency advisories.
Next.js and its matching lint configuration are patched from 16.3.6 to 16.3.8;
the lockfile now uses sharp 0.35.5 and source-map-js 1.2.2. Web lint, formatting,
typechecking, all 28 unit tests and production build passed again after updating.
The production dependency audit reports zero vulnerabilities.

The full audit still fails on [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm):
development-only `eslint-config-next -> @next/eslint-plugin-next -> fast-glob ->
micromatch -> braces@3.0.3`. The advisory has no published patched version; even
eslint-plugin-next 16.4.0 retains this chain. It concerns deeply nested glob input
in tooling, not journal input at runtime. Five audit package findings trace to
this one advisory. The existing full audit gate remains unchanged and blocking;
there is no blanket suppression or forced downgrade to Next.js 14 lint tooling.
Recheck for an upstream patched dependency before merge/deployment.

Patch references: [Next.js](https://github.com/advisories/GHSA-3w37-wq28-93x7),
[sharp](https://github.com/advisories/GHSA-wq5f-xc86-pv6w),
[source-map-js](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).
