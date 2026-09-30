# occasions

Optional occasions that group multiple wine entries and a combined scrapbook. Standalone drinking entries remain valid without an occasion.

O01 implements an owned occasion list, creation and detail/edit screens. `occasion-views.tsx` owns read queries; `occasion-editor.tsx` owns save/retry/conflict behavior; `occasion-fields.tsx` renders the shared form; `occasion-draft.ts` validates account-scoped session drafts. App Router files stay thin.

Date is required; title is optional with a date fallback. Time/timezone, a custom place label and general notes can be added later. Creation uses a persisted idempotency key; full-context PUT edits require the viewed version and explicit resolution of conflicts. Sign-out clears drafts through the shared journal session boundary.

Wine-first selection and inline occasion creation are implemented by the capture feature, reusing this feature's fields/draft serialization. O03 adds `occasion-composer.ts` for bounded parent/child draft state, `staged-wines.tsx` for staging manual wines and repeated glasses, and `occasion-wines.tsx` for grouped saved cards and transactional additions. An unfinished child never becomes an API record until the final save. Old drafts and retry keys remain readable.

Each batch allows 20 total entries. Per-entry dates and notes are independent; time/place enrichment uses the existing entry editor. The API also accepts owned releases; the new staged-wine UI currently enters manual identities. Changing existing links, official venue lookup, albums and participants remain later slices. See [O01](../../../../../tasks/occasion-checkpoint.md), [O02](../../../../../tasks/occasion-capture-checkpoint.md) and [O03](../../../../../tasks/occasion-wines-checkpoint.md).
