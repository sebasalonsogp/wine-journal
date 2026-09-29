# J07: Safe entry deletion

## Implementation slices

1. API: `journal/deletion.py`, route/response schema, a migration granting DELETE on entries only, and regression tests. Require the viewed entry version; wrong-owner/missing IDs return 404 and stale edits return 409. Remove one entry without removing its wine identity. Replace its creation receipt with a deletion marker so an old create retry cannot resurrect it.
2. Browser: a separate entry deletion control with contextual confirmation, cancel, stale-version recovery and uncertain-request retry. Refresh history and wine summaries, clear the matching edit draft, and verify deleting one of two entries followed by the last.

The delete transaction is the future attachment-cleanup integration point. When media is implemented, enqueue cleanup in this transaction before removing references; do not perform remote storage calls during the transaction. No speculative worker/event system is introduced here.

Verification in progress.
