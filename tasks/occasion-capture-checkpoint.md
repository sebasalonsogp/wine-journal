# O02: Occasion selection during wine capture

Implemented September 29, 2026. Wine capture may have no occasion, an owned existing occasion, or one staged new occasion. Drinking context stays independent from occasion context; a new occasion initially uses the entry date. A single save commits the manual wine (if any), occasion (if new) and entry atomically. Nested cancellation discards only staged occasion input.

## Implementation slices

1. Add a nullable same-owner occasion FK to entries, optional occasion selectors and quick notes to capture input, and expose the link in entry responses. Preserve existing creation-receipt hashes when new optional fields are absent. Verify rollback, ownership, mutually exclusive selectors, retries and migration compatibility against Postgres.
2. Extend bounded browser drafts and capture controls with existing-occasion pagination, inline occasion fields, cancellation and private quick notes. Keep nested input through reload/sign-in and lock all input after an uncertain save. Link saved entries to their occasion.
3. Exercise cancellation, navigation, nested validation, dropped responses and recovery in real browser tests. Review phone/desktop rendering and accessibility, run regression/secret checks, document and update the existing PR and local preview.

## Implementation evidence

- Migration 0008 adds a nullable same-owner occasion FK and lookup index. Upgrade preserved local records; downgrade/upgrade and Alembic drift checks ran against disposable Postgres. Ordinary entry edits receive no association-update grant.
- One entry receipt protects nested occasion/manual identity/entry creation. Legacy requests retain their old hash; legacy receipts decode the new nullable response field. Quick notes belong to the entry; general occasion notes remain separate.
- Nested input survives reload and guest sign-in. Existing-occasion choices paginate and can retry failed loading. Back navigation restores the selected ID even when it lies beyond the first page. Cancellation removes only staged occasion input. Uncertain saves freeze all submitted fields and reuse the key; blocked draft storage prevents submission.
- Entry history exposes View occasion. Occasion-first capture, grouped occasion wine cards, relinking and albums remain future work.

## Verification

- 82 API tests passed: nested validation, foreign-account selection rejection, actual database failure after nested inserts with complete rollback, concurrent retries, old receipt compatibility, FK enforcement and migration checks.
- 19 web unit tests passed, including bounded nested parsing, separate notes and upgrading older drafts without changing their retry payload.
- All 15 browser scenarios passed. New journeys cover cancellation, independent dates/notes, sign-in return, validation repair, reload, dropped response, one-entry/one-occasion retry, paginated selection, failed-list recovery, navigation, repeat capture and choosing no occasion.
- Phone 390px and desktop 1440px screenshots inspected; overflow and WCAG A/AA checks passed. Synthetic data only; no auth traces or recordings. Production build, lint/types/format checks and browser secret scan passed.

Next: O03, staging multiple wines from an occasion and adding a wine directly to a saved occasion. The API continues to use the existing cohesive Journal module; no new service or dependency was introduced.
