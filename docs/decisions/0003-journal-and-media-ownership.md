# ADR 0003: Independent entries, release ratings, and referenced memories

Status: Proposed technical design implementing confirmed product boundaries. Date: September 14, 2026.

## Context

One wine can be drunk repeatedly; one occasion can include several wines. A casual glass needs a date but no occasion. Personal ratings change independently of drinking. Both the wine view and occasion scrapbook should surface shared memories without duplicate wine sections or copied uploads.

## Decision

Distinguish catalog wine definition, release, personal wine record, drinking entry, optional occasion, rating revision, and media asset. An entry owns consumed context. Rating history belongs to the personal release record. Media retains an explicit entry/occasion/cover attachment; galleries compose authorized references at read time.

Create nested occasion/entry records in one database transaction. Uploads and processing have a separate staged lifecycle because object storage cannot participate in that transaction. Store durable media work in Postgres and process it with a worker from the same Python application when media ships.

## Alternatives and consequences

- Requiring an occasion for every drink simplifies one relation but misrepresents standalone glasses.
- Rating each entry or averaging revisions contradicts the chosen wine-level current rating/history.
- Copying media into every relevant view introduces duplicate storage and ambiguous edits/deletion.
- Processing media only inside a request risks losing work on restarts and blocking saves.

Queries and deletion rules require more care, but the model follows the user's actual concepts. Identity corrections and shared-occasion permissions still need explicit operations; this schema does not justify silent merges or automatic sharing. Details and example cases: [data model](../data-model.md).
