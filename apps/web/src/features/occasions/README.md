# occasions

Optional occasions that group multiple wine entries and a combined scrapbook. Standalone drinking entries remain valid without an occasion.

O01 implements an owned occasion list, creation and detail/edit screens. `occasion-views.tsx` owns read queries; `occasion-editor.tsx` owns save/retry/conflict behavior; `occasion-fields.tsx` renders the shared form; `occasion-draft.ts` validates account-scoped session drafts. App Router files stay thin.

Date is required; title is optional with a date fallback. Time/timezone, a custom place label and general notes can be added later. Creation uses a persisted idempotency key; full-context PUT edits require the viewed version and explicit resolution of conflicts. Sign-out clears drafts through the shared journal session boundary.

Wine linking, inline occasion capture, official venue lookup, albums and participants are not implemented here yet. See [the checkpoint](../../../../../tasks/occasion-checkpoint.md).
