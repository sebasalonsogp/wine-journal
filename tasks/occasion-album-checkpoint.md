# M06 — Occasion scrapbook

Status: M06a backend implemented October 12, 2026; M06b browser work remains open.
The parent M06 task is not complete.

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
are linked from the pull request after publication. No album UI is claimed yet.
