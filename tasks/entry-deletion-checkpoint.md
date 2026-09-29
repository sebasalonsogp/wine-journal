# J07: Safe entry deletion

## Implementation slices

1. API: `journal/deletion.py`, route/response schema, a migration granting DELETE on entries only, and regression tests. Require the viewed entry version; wrong-owner/missing IDs return 404 and stale edits return 409. Remove one entry without removing its wine identity. Replace its creation receipt with a deletion marker so an old create retry cannot resurrect it.
2. Browser: a separate entry deletion control with contextual confirmation, cancel, stale-version recovery and uncertain-request retry. Refresh history and wine summaries, clear the matching edit draft, and verify deleting one of two entries followed by the last.

The delete transaction is the future attachment-cleanup integration point. When media is implemented, enqueue cleanup in this transaction before removing references; do not perform remote storage calls during the transaction. No speculative worker/event system is introduced here.

## UX contract

Extend the existing wine history using its cream, burgundy and olive tokens. Delete entry sits beside Edit entry when no edit form is open. A native dialog protects focus for this irreversible action, identifies the wine/date and any time/place/note excerpt, and defaults focus to Keep entry. Escape cancels. The confirmation uses the entry version originally shown, even if the underlying query refreshes. After a conflict the dialog closes and the updated entry must be reviewed and confirmed again.

Successful removal refreshes wine/history/list queries, clears the current tab's matching edit draft, and moves focus to the history heading. A 404 on retry means the entry is already unavailable; it is reconciled through a refresh. Other failures remain visible with retry. A last-entry deletion keeps the wine card with zero entries and an unknown last-drunk date.

## Verification

58 API tests pass, including deletion of one of two encounters and the last, stale versions, missing preconditions, wrong-owner requests, repeated deletion and an old create retry. The full migration upgrade/downgrade suite includes the new permission migration. All 11 web unit tests and nine browser scenarios pass. Web checks cover cancel/Escape/focus restoration, concurrent editing, dropped deletion responses, reloads, preserved wine cards, and axe. Type, lint, formatting and production-build checks pass.

Desktop (1440 px) and phone (390 px) screenshots were reviewed together. The correction pass put entry controls below date-only rows; the confirmation layout and correction were verified in a second bounded pass. The native dialog preserves the approved design without new dependencies or image assets. J07 is complete; J08 wine-level ratings are next. Browser-bundle and staged secret scans gate publication.
