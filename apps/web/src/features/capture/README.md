# capture

The shared wine-first and occasion-first draft workflow: identify or manually enter a wine, save its consumed date, and optionally enrich it. Preserve staged wines and inline occasion drafts until save.

Implemented: manual name/date capture, optional producer/vintage/edition, repeat capture from an existing release, and tab-scoped drafts. Guest input survives sign-in; owned drafts are not restored for another identity. An uncertain save freezes its fields and keeps the original key through retry/reload. Validation failures permit correction. Explicit discard warns when an entry may already have committed.

The inline entry editor adds date, optional local time/timezone, custom place and plain-text notes to the same entry. Its draft key includes the verified owner and entry ID; sign-out clears the shared private-draft prefix. Conflicts show the latest record alongside the retained draft and require an explicit choice. Successful changes invalidate wine/list/history queries. Offline sync, occasion capture and uploads remain future work.
