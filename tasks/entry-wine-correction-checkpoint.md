# C03a — Move one entry to the correct wine

October 20, 2026. C03a supplies the backend contract and C03b adds browser controls.
C03 remains open for C03c: editing provisional facts shared by a wine's entries.

## Contract and behavior

`PUT /api/v1/entries/{entry_id}/wine` requires authentication and:

- `version`: the entry version the user reviewed.
- `previousWineId`: its current private journal wine ID.
- Exactly one destination: `wineId` for an existing owned journal wine, or
  `manualWine` with the existing manual identity schema.

These are journal wine IDs, not public catalog or private release IDs. Both
entry and destination must belong to the current active account. Missing or
foreign objects return 404 without disclosing another account's record. Extra
fields and invalid destination combinations return 422.

Only `user_wine_id` and the entry's optimistic version change. The entry ID,
creation/drinking date, time, place, notes, occasion and photo attachments stay
intact. Existing ratings, rating history and bottle covers stay with their
original wines. Moving the last entry leaves the source wine accessible.
Matching manual names never merge records.

The owner/source/version predicate is checked before destination creation and
again in the UPDATE. A concurrent edit, move, occasion association or deletion
wins cleanly: a stale request gets 409, and any new destination identity is
rolled back with it. Lock waits are bounded to three seconds and return a
recoverable conflict. A current-version request to the same wine is a no-op.

## Retry contract for the browser follow-up

The move uses the entry's existing optimistic version rather than a separate
idempotency ledger. Replaying a successful move with its old version returns
409; it cannot create another manual wine. After an uncertain response, read
the entry and its current wine before offering another change. Do not silently
resubmit using a newer version or treat 409 as evidence that the move failed.

Capture receipts for the moved entry retain their key/request hash and receive
the corrected response in the same transaction. A retry of its original capture
therefore returns the corrected wine without creating another entry. Occasion
save receipts contain occasion responses and need no wine rewrite.

Gallery membership is derived from current entry/occasion associations. Entry
photos follow the corrected entry; occasion-wide photos remain accessible from
each wine still represented there. No assets, storage holds, quotas or jobs are
copied or changed by the move.

## Migration and verification

Migration 0024 grants UPDATE only on `drinking_entries.user_wine_id`. Composite
owner FKs stay in place; identity, owner and creation fields retain their denied
UPDATE grants. Downgrade revokes the capability without undoing corrections.
Local application preserved journal/catalog/media counts, reserved bytes and
unsettled grant/write totals.

The 40-case focused run passed. It includes new move/retry/ownership/validation
tests, a synchronized two-move race, changes between read and UPDATE, grant
roundtrips, and occasion/photo/cover membership regression coverage. Attachment
tests use real database rows and synthetic ready-asset metadata; they do not
claim to exercise a new decoder or real-phone workflow.

All 416 API tests passed with disposable Postgres, local Storage and the
Docker-isolated photo decoder. Ruff, formatting (162 files), mypy (132 source
files), backend package build, generated contracts and frontend types/lint
passed. The local preview serves Browse successfully and the API exposes the
new contract. No dependency, environment variable or external service is added;
the existing UI remains unchanged.

The prior C02b head's GitHub API/browser and secret-check jobs passed. Its web
job failed only at the existing full npm audit gate. That dependency blocker
remains enabled and unresolved; the PR remains unmerged.

## C03b — Browser move and review

Drinking history now offers **Move to another wine** per entry. One correction
panel at a time appears above history and receives keyboard focus. Existing
wines can be searched and paged; each option includes vintage/edition and
producer. A new manual wine reuses capture's identity fields without exposing
the entry date as an editable field. IDs are scoped so other forms stay valid.

The explicit review names source and destination and explains that other entries,
wine ratings/history and covers stay put. Cancel performs no mutation. File
selections, pending caption edits and photo mutations block moving that entry
until resolved, including work started after the correction panel was opened.

A successful move stays visible with a link to the entry under its destination.
The panel survives the source history refresh when the entry leaves the list.
Wine/history/occasion/gallery caches are invalidated by account. No automatic
navigation discards other pending media work.

An uncertain response offers **Check saved entry**, reading both the current
entry and wine. If it is still under the original wine, the user may explicitly
review a move using that version, then confirm again. If its wine changed,
the panel links to the current entry rather than creating another destination.
A stale response never silently substitutes the latest version.

Destination choices are temporary page state, retained through failed requests
and review, not offline-synced or persisted across reload/navigation. The private
shell clears/unmounts them on sign-out or account change. Saved moves remain
visible after reload. Shared provisional-fact editing and record merging are
not part of this slice.

The three new browser journeys cover failed/paginated/searchable selection,
cancel/confirm, real private photo upload and caption retention, pending-photo
guards, occasion membership, preserved ratings/other entries, a dropped committed
response creating exactly one new wine, stale-entry review and cross-tab
sign-out followed by another account. Desktop and 390px screenshots were inspected;
axe checks found no violations or phone overflow.

All 32 browser journeys and 35 frontend unit tests passed. Frontend lint/types,
formatting and production build passed; Impeccable reported no findings. The
browser secret scan checked 20 scripts without finding generated private values.
The prior C03a backend suite remains at 416 passing tests; API behavior,
database schema, dependencies and environment variables are unchanged in C03b.
