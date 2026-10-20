# Private journal

Journal workflows combine owner-scoped identities, drinking entries, ratings
and optional occasions in local database transactions. `service.py` captures a
wine/date with retry receipts; `edits.py` and `deletion.py` protect saved entries
with optimistic versions. Occasion and rating workflows have their own explicit
versions and ownership checks.

## Correct the wine for one entry

`PUT /api/v1/entries/{entry_id}/wine` is implemented in `entry_wines.py`. Submit
`version`, `previousWineId` and exactly one of `wineId` (an existing owned journal
wine) or `manualWine`. Source and destination are private; public catalog IDs
are not accepted in this contract.

A successful change returns the entry with a new `userWineId` and incremented
version. Its ID/context/occasion/photos are retained. Ratings and bottle covers
stay with their wine records. A new manual destination is created in the same
transaction; failure rolls it back, and names never imply a merge.

The source/version UPDATE predicate prevents overwriting concurrent changes.
An uncertain response requires GET `/entries/{entry_id}` and a deliberate
review of the current wine. Reusing the old version returns 409 after success
without producing another wine. A same-wine current-version request is a no-op.
Original capture receipts are updated atomically so a capture retry points at
the corrected wine.

Migration 0024 adds only the required column UPDATE grant. Owner FKs, denied
identity UPDATEs and public catalog read-only grants are unchanged. Rollback
revokes the capability without rewriting journal history.

See the [C03a checkpoint](../../../../../tasks/entry-wine-correction-checkpoint.md)
for verification and the pending browser move/review flow.
