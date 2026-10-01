# M04: Entry photos

M04a delivered, October 1, 2026. M04 remains open until the M04b browser journey passes.

## Delivery slices

1. **Complete:** Owned entry/asset associations, captions, removal and generated API contracts.
   Verify cross-account combinations, concurrent/replayed writes, stale changes,
   database constraints and entry deletion against disposable Postgres.
2. Shared photo controls in capture and existing entries. Files can be selected
   before saving; saving text never waits for uploading. Keep the saved entry ID
   while retrying photos. Show pending, processing, ready and failed states.
3. Verify the phone-sized save/failure/retry/reload/remove journey and desktop
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

## Next: M04b browser slice

Keep selected files in memory and the photo component mounted when text save
returns an entry ID. Reuse that ID on every attachment retry; never re-POST the
entry. Store no photo bytes or signed URLs in draft storage. Fetch READY
derivatives without caching, use temporary blob URLs, and revoke them when the
gallery/account unmounts. A failed decoder result needs replacement, not another
entry or an automatic retry of a terminal processing job.

Capture currently navigates immediately after saving text. It needs an explicit
saved-entry state when photos are selected. JournalShell currently unmounts its
children during focus rechecks: preserve upload state during a same-account
recheck without exposing an old account's data, and test the file-picker/focus
round trip. Guest capture remains usable without photos before sign-in.

The frontend source and visual design were inspected, but upload controls were
not implemented or visually verified in this slice. Impeccable context loading
was unavailable; the existing project design references remain authoritative.
