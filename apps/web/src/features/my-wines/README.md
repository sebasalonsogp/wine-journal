# my-wines

The primary private journal, organized by distinct wine releases. Owns screens for repeated entries, current rating with change history, and eligible photo highlights.

Implemented: real owner-scoped cards, release detail, paginated date-only history, empty/error/loading states and entry points to manual/repeat capture. Queries use the shell's typed API transport and account-specific keys. Successful capture navigates to a new document to drop prior read caches before loading persisted data. Ratings and memory highlights remain future slices; no sample journal data or fabricated ratings are displayed.
