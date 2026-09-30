# occasions

Optional occasions that group multiple wine entries and a combined scrapbook. Standalone drinking entries remain valid without an occasion.

O01 implements an owned occasion list, creation and detail/edit screens. `occasion-views.tsx` owns read queries; `occasion-editor.tsx` owns save/retry/conflict behavior; `occasion-fields.tsx` renders the shared form; `occasion-draft.ts` validates account-scoped session drafts. App Router files stay thin.

Date is required; title is optional with a date fallback. Time/timezone, a custom place label and general notes can be added later. Creation uses a persisted idempotency key; full-context PUT edits require the viewed version and explicit resolution of conflicts. Sign-out clears drafts through the shared journal session boundary.

Wine-first selection and inline occasion creation are implemented by the capture feature, reusing this feature's fields/draft serialization. O03 adds `occasion-composer.ts` for bounded parent/child draft state, `staged-wines.tsx` for staging manual wines and repeated glasses, and `occasion-wines.tsx` for grouped saved cards and transactional additions. An unfinished child never becomes an API record until the final save. Old drafts and retry keys remain readable.

Each batch allows 20 total entries. Per-entry dates and notes are independent; time/place enrichment uses the existing entry editor. The API also accepts owned releases; the new staged-wine UI currently enters manual identities.

O04 adds `entry-occasion.tsx` to wine drinking history for confirmed link/move/unlink commands. `occasion-select.tsx` shares the paginated picker with capture. The viewed entry version and previous association protect writes; stale or uncertain responses require a fresh read and explicit review. The in-memory choice is not a persisted draft. Entry mutations invalidate grouped occasion reads.

O05 adds `occasion-deletion.tsx`: a native confirmation dialog, version-checked removal, explicit stale-context review and safe same-version retry after response loss. Success clears this tab's occasion edit/add-wines drafts, refreshes entry/list reads and removes the deleted detail from the query cache. Entries and ratings remain in My Wines. Media cleanup will be integrated when albums exist.

Official venue lookup, albums and participants remain later slices. See [O01](../../../../../tasks/occasion-checkpoint.md), [O02](../../../../../tasks/occasion-capture-checkpoint.md), [O03](../../../../../tasks/occasion-wines-checkpoint.md), [O04](../../../../../tasks/entry-occasion-checkpoint.md) and [O05](../../../../../tasks/occasion-deletion-checkpoint.md).
