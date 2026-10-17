# M05 — Personal bottle covers

Implemented October 1, 2026 in two increments:

1. M05a: additive migration 0015, owned/versioned cover operation, private wine
   projections and generated contracts. Tests cover ownership, concurrent writes,
   immediate replay, removal, pending-image rejection and reversible migration.
2. M05b: manual capture selection, saved-wine management, private thumbnail reuse
   and cover display in My Wines, wine detail and occasion wine cards. Real browser
   journeys cover interrupted uploads, retry, invalid replacement, stale removal,
   refresh, memory exclusion and sign-out.

## Behavior

A personal wine has one optional cover asset and an independent revision. Only a
processed READY asset owned by the active account can become its cover. Replacing
a cover leaves the old image in place until the new image is ready. A same-owner
database foreign key protects the reference; runtime UPDATE grants name only the
two new columns. Public provider roles have no access.

`PUT /me/wines/{wine_id}/cover` takes `{assetId, version}`; `assetId: null` removes
the personal cover. Immediate identical retries reconcile lost responses. A stale
write returns `COVER_CONFLICT`; it cannot resurrect a removed cover. Clients review
the current revision before explicitly retrying. Cover changes do not create
entries, revise ratings, modify catalog records or add gallery associations.

Manual capture stages the file in memory before the wine exists. The deliberate
entry save commits text first, then uploads/processes the selected cover. Upload
failure leaves text saved and exposes an independent retry. Later edits use Manage
bottle cover on the wine detail. The current processed thumbnail is the preview;
unprocessed originals are not rendered. Covers share existing file limits and the
private Storage/decoder pipeline. No new dependency or credential is needed.

The display falls back to the existing bottle placeholder when no personal cover
is available. Catalog artwork is not connected yet; no catalog image is fabricated
or fetched from an unconfigured provider. The future catalog integration supplies
the middle step of personal cover → catalog image → placeholder.

## Validation and limits

The API suite passed 284 tests; the nine opt-in Storage/decoder cases passed in a
separate enabled run (293 distinct cases total). Five new cover cases use real
disposable Postgres. The cover browser
journey uses real local Auth, private Storage and the isolated decoder; it proves
one text entry and no memory membership across retry/replacement/removal. Browser
screenshots use a synthetic white image, not real bottle artwork. Desktop and
390px layouts and axe checks passed. Frontend unit coverage is 28 cases, including
an explicit assertion that a cover upload never calls an entry/gallery mutation.

Migration 0015 was applied to local Supabase with entry, occasion, wine and asset
counts unchanged. Local API/web previews were restarted. All 22 browser scenarios
passed; the four media scenarios passed again after consolidating the leave-page
guard for simultaneous cover/memory selections. Lint, formatting, strict typing, production builds,
dependency audit and tracked/browser secret checks passed. CI results are recorded
in the PR before handoff.

Files remain memory-only until upload; leaving/reloading requires choosing them
again. Sign-out clears the selection without blocking navigation. Replaced and
removed assets retain their storage reservations until M08 safe cleanup. Physical
iPhone photo-picker acceptance remains outstanding. Occasion albums (M06) are next.
