# capture

The shared wine-first and occasion-first draft workflow: identify or manually enter a wine, save its consumed date, and optionally enrich it. Preserve staged wines and inline occasion drafts until save.

Implemented: manual name/date capture, optional producer/vintage/edition, repeat capture from an existing release, and tab-scoped drafts. Guest input survives sign-in; owned drafts are not restored for another identity. An uncertain save freezes its fields and keeps the original key through retry/reload. Validation failures permit correction. Explicit discard warns when an entry may already have committed.

O02 adds quick wine notes and `capture-occasion.tsx`: a paginated existing-occasion picker and inline `OccasionFields` reuse. Nested context lives inside the bounded capture draft; cancellation keeps wine/date/notes. A new occasion starts with the wine's date and can diverge. Saving sends one entry request with either `occasionId` or `newOccasion`; no child is saved separately. A missing existing target or validation failure unlocks correction; uncertain saves keep their original key and locked fields. Blocked session storage stops the request before submission. Saved entry history links to its occasion.

The inline entry editor adds date, optional local time/timezone, custom place and plain-text notes to the same entry. Its draft key includes the verified owner and entry ID; sign-out clears the shared private-draft prefix. Conflicts show the latest record alongside the retained draft and require an explicit choice. Successful changes invalidate wine/list/history queries. Offline sync, occasion-first batch capture and uploads remain future work.

The separate deletion control is available outside edit mode. A native confirmation dialog names the selected entry and freezes its version until confirmation. Cancel restores trigger focus; a completed deletion refreshes affected lists and focuses the history heading. The personal wine record remains even after its final entry is deleted.
