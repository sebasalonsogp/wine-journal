# capture

The shared wine-first and occasion-first draft workflow: identify or manually enter a wine, save its consumed date, and optionally enrich it. Preserve staged wines and inline occasion drafts until save.

Implemented: manual name/date capture, optional producer/vintage/edition, repeat capture from an existing release, and tab-scoped drafts. Guest input survives sign-in; owned drafts are not restored for another identity. An uncertain save freezes its fields and keeps the original key through retry/reload. Validation failures permit correction. Explicit discard warns when an entry may already have committed. Offline sync, occasion capture, notes and uploads remain future work.
