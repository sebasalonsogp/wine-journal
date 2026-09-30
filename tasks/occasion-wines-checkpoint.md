# O03: Add wines from an occasion

Implemented September 29, 2026. New and saved occasions can stage bounded batches of manual wines. The API also accepts owned releases. Each wine group contains explicit drinking entries with independent dates/notes; repeated glasses reuse that group's release. At most 20 entries commit per request. No automatic name matching.

1. API: reuse transaction-local entry creation; add batch schemas and receipt-protected creation/add commands, plus a paginated grouped occasion wine read. Preserve old occasion receipt hashes. Test three releases/four entries, rollback after partial inserts, retries, ownership, bounds and scoped cursors.
2. UI: persist a composer envelope with staged wines and unfinished child; stage/edit/cancel/remove child entries without creating records. Reuse capture fields; show grouped bottle cards and add-wines form on saved occasions. Lock uncertain saves and keep drafts across reloads.
3. Verify real browser capture loops, mobile/desktop and accessibility; run regression and secret checks, update documentation/PR and restore preview. Prior-entry relinking, deletion and media remain later slices.

## Delivered

- POST occasion creation accepts optional wine groups; POST occasion wines adds a nonempty batch to a saved occasion. Both use one transactional receipt and bounded lock wait. Empty creation batches preserve earlier receipt hashes; addition hashes include the target/operation. No new database migration or dependency.
- Transaction-local entry insertion is shared with wine-first capture. Repeated glasses within one group create one release/personal record and multiple drinking entries. Separate manual groups are never silently merged by name.
- Parent drafts retain staged wines and an unfinished child. Editing then cancelling restores the original staged wine; cancelling a new child preserves occasion context. Final submission is disabled until the child is kept or cancelled. Fields lock after uncertain submission and the original save key survives reload. Draft storage failure prevents saving.
- Saved occasion cards group by wine, show linked entry counts and a bottle placeholder, and link to the personal history. Photos/covers are still future work. Existing wine/list/history caches are invalidated after successful batches.

## Verification

- 85 API tests passed, including three releases/four entries, distinct entry notes/dates, nested validation and count bounds, failure after the second insert with complete rollback, concurrent retries, additions, owner isolation and occasion-bound pagination. Regression tests cover the original wine-first flow and migration/grant checks.
- 21 web unit tests passed, including legacy draft serialization, unfinished child restoration, explicit repeats and malformed/oversized batches.
- All 16 browser scenarios passed. The new dinner journey covers a cancelled child, three staged wines/four entries, child reload, cancelled staged edit, dropped create response/retry, grouped cards, later addition with another dropped response, and linked wine history. Desktop 1440px/phone 390px screenshots inspected; overflow and WCAG A/AA checks passed.
- Production build, web lint/types/formatting, API lint/types/formatting and browser secret scan passed. Screenshots use synthetic records and remain ignored local artifacts. Full regression and CI status are recorded on the PR.

## Remaining scope

O04 links/unlinks earlier entries with explicit re-link decisions. O05 adds safe occasion deletion; grouping is now available. Batch drafts capture per-entry date/notes, while time/place can be enriched after saving. The API supports owned release selection but this new composer starts with manual wines; known wines remain usable through wine-first repeat capture. Albums, official places, offline sync, participants and public reviews remain later work.
