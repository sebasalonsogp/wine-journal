# O04: Organize previously saved entries

Delivered September 29, 2026. In My Wines, open a wine and choose **Organize occasion** on a drinking entry. Select an existing occasion or **No occasion**. Moving an already linked entry or unlinking it requires confirmation.

## Behavior and boundaries

- Dedicated PUT/DELETE association commands change only `occasion_id` and the entry version. IDs, wine identity, consumed date/time/timezone, place, notes and wine ratings/history are preserved. No entry is copied.
- PUT requires the viewed version and explicit `previousOccasionId` (including null). DELETE requires the viewed version and the current occasion in its path. Competing edits or links return 409. An unchanged PUT at the current version is a no-op.
- Missing or foreign entries/occasions return 404. Migration `0009_entry_association` grants the runtime role UPDATE on only the newly editable association column; ownership remains protected.
- The existing paginated occasion picker is shared with capture. Entry edits, deletion and association changes invalidate grouped occasion reads.
- A stale response displays the latest entry and requires an explicit decision. A lost mutation response requires **Check saved entry** before another mutation. Selection survives this in-page review, but is not persisted across reloads; reload reads server state.

## Verification

- 88 API tests, 21 web unit tests and 17 browser tests passed against the local database and production web build.
- Association tests cover two entries, link/move/unlink, unchanged row counts and context, preserved rating/revisions, cross-account access, competing transactions, strict payload validation and migration downgrade/upgrade grants.
- The real-browser journey covers confirmation cancellation, two-tab stale edits, lost unlink response recovery and refreshed occasion cards. Phone (390 px) and desktop (1440 px) screenshots were inspected; overflow and automated accessibility checks passed.
- Ruff, mypy, ESLint, TypeScript, formatting, API generation, production build and browser/tracked-file secret checks passed.

## Next

O05: delete an occasion without deleting its drinking entries. Occasion-side bulk selection, official places, media and participants are not part of O04. Existing grouped wine cards already provide the first part of O05.
