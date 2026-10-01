# my-wines

The primary private journal, organized by distinct wine releases. Owns screens for repeated entries, current rating with change history, and eligible photo highlights.

Search/filter/sort state is parsed from bounded, allowlisted URL parameters by `wine-filters.ts`. `WineFilterBar` applies the form explicitly, and list queries include the account and all applied options in their cache key. Cards carry the same options to detail so Back to My Wines restores the view. Pagination restarts when options change; current-rating invalidation still targets the account-specific wine-query prefix. Filtering never merges releases or exposes private data to guests.

Implemented: real owner-scoped cards, release detail, paginated history with optional time/place/notes, inline entry editing/deletion, current ratings and paginated rating revisions, empty/error/loading states and entry points to manual/repeat capture. Queries use the shell's typed API transport and account-specific keys. Successful capture navigates to a new document to drop prior read caches before loading persisted data. Rating drafts retain their original version across reloads/focus checks and stay scoped to the account/wine; conflicts require review. Memory highlights remain a future slice; no sample journal data or fabricated ratings are displayed.
