# C03a — Move one entry to the correct wine

October 20, 2026. Backend contract and transaction slice; C03 remains open.
The browser move/review controls are C03b, and editing provisional facts shared
by all of a wine's entries is C03c.

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

## Next slice

C03b should show the source and selected destination before saving, explain
that ratings/covers stay with their wines, and provide paginated existing-wine
selection plus manual entry. Preserve selection on errors; review the current
entry/wine after 409 or an uncertain response. Account changes must clear
private state. Refresh source/destination history, wine counts, occasion wines
and photo source links after success. Verify this through connected browser
journeys before marking the user-facing behavior complete.
