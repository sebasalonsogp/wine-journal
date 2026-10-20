# capture

The shared wine-first and occasion-first draft workflow: identify or manually enter a wine, save its consumed date, and optionally enrich it. Preserve staged wines and inline occasion drafts until save.

Implemented: manual name/date capture, optional producer/vintage/edition, repeat capture from an existing release, and tab-scoped drafts. Guest input survives sign-in; owned drafts are not restored for another identity. An uncertain save freezes its fields and keeps the original key through retry/reload. Validation failures permit correction. Explicit discard warns when an entry may already have committed.

Catalog details now offer “I tried this wine.” The server resolves the public
selection before opening capture; the client keeps its release ID and identity
display with date/notes through sign-in. Saving requires an account and sends
only `catalogReleaseId`, never browser-supplied catalog facts. The API reuses the
owner's linked wine for repeats.

An existing draft takes priority: the user may continue it or explicitly discard
it for the selected catalog wine. A draft with an uncertain save cannot be
replaced through this choice. Owned drafts stay hidden while signed out and are
cleared on account changes. The narrowly allowed `/capture?catalog=<UUID>` auth
return retains an incoming selection when an owned draft requires sign-in.
Older stored drafts remain readable, and absent catalog fields preserve old
request/receipt hashes. New personal covers for a catalog wine can be managed
after saving, so a repeat capture never accidentally replaces its cover.

The occasion batch composer currently accepts manual and already-owned wines;
it rejects catalog-selection draft payloads rather than dropping their identity.
Catalog capture itself supports selecting or creating an occasion inline.

O02 adds quick wine notes and `capture-occasion.tsx`: a paginated existing-occasion picker and inline `OccasionFields` reuse. Nested context lives inside the bounded capture draft; cancellation keeps wine/date/notes. A new occasion starts with the wine's date and can diverge. Saving sends one entry request with either `occasionId` or `newOccasion`; no child is saved separately. A missing existing target or validation failure unlocks correction; uncertain saves keep their original key and locked fields. Blocked session storage stops the request before submission. Saved entry history links to its occasion.

The inline entry editor adds date, optional local time/timezone, custom place and plain-text notes to the same entry. Its draft key includes the verified owner and entry ID; sign-out clears the shared private-draft prefix. Conflicts show the latest record alongside the retained draft and require an explicit choice. Successful changes invalidate wine/list/history queries. Offline sync, occasion-first batch capture and uploads remain future work.

The separate deletion control is available outside edit mode. A native confirmation dialog names the selected entry and freezes its version until confirmation. Cancel restores trigger focus; a completed deletion refreshes affected lists and focuses the history heading. The personal wine record remains even after its final entry is deleted.

`entry-wine-move.tsx` handles one saved entry correction from the wine detail
screen. Search/page an existing owned wine or reuse `CaptureFields` for a new
manual identity (`showDate=false`, scoped IDs). Review the source/destination
before confirming. Saved entry context and photo references remain intact;
ratings and covers stay with each wine. Pending photo selections/captions block
moving so a history refresh cannot discard them.

The correction panel is mounted outside individual history rows, so it remains
available after a successful move removes that row. Uncertain responses read
the current entry and wine; stale versions require explicit review and a second
confirmation. A changed wine is linked for inspection rather than creating a
second manual destination. Selections live in page state and clear on account
changes. Success invalidates affected owner-scoped journal/gallery queries.
