# O01: Create and revisit occasions

Implemented September 29, 2026. Date is required; title is optional and falls back to the occasion date. Local time/timezone, a custom place label and general notes are optional. Empty occasions are valid while planning. Ordinary wine entries never create occasions implicitly.

## Slices

1. Storage/API: journal occasion model and creation receipts, migration 0007, schemas, routes and use cases. Reuse civil-time validation; enforce active owner access, bounded pagination, transactional idempotent creation and version-checked edits. Verify title/date rules, two-account isolation, competing edits/retries, rollback, and upgrade/grants against Postgres.
2. Browser: replace the Occasions placeholder with a list, new-occasion route and detail/editor. Keep account-scoped drafts, lock uncertain creation input for safe retry, retain stale edit drafts for explicit resolution, and distinguish no occasions from failures. Verify titled/untitled creation, reload, secondary navigation, time/place/notes and stale edits.
3. Review desktop/phone layouts and accessibility, run regressions and secret checks, update the existing PR and local preview. Linking wines, inline occasion capture, media and shared participants remain O02 onward.

## Delivered behavior

- Journal module owns the occasion model, routes, schemas and use cases; migration 0007 adds `occasions` and `occasion_saves`. No new service or package dependency.
- GET/POST collection and GET/PUT detail use the active account and no-store responses. Pagination orders by date descending with stable ID ties and owner-bound cursors. Fields are bounded; title/date rules and civil-time validation are shared consistently with entries.
- Creation claims a UUID save key and stores its original response in the same transaction as the occasion. Changed input under one key conflicts; concurrent retries yield one record. Full-context PUT uses the original version; stale changes never overwrite silently.
- Browser list, creation and detail/editor routes use the existing session boundary. Drafts are account-scoped, survive reload in the tab and clear on sign-out. Creation refuses to proceed if the retry key cannot be retained. After an uncertain create, input is locked and Retry save reuses the original key. After an uncertain or stale edit, users review the latest saved context and explicitly keep it or replace it with their draft.
- Runtime database grants cannot alter occasion ownership or delete occasions. Migration upgrade preserved the existing local journal; rollback testing used only a disposable database.

## Verification

- 78 API tests passed, including title/untitled lifecycle, full-context clearing, foreign-account reads/edits, cursor scope, malformed input, concurrent create/edit, transaction rollback and migration/grant checks.
- 18 web unit tests passed, including bounded occasion draft parsing, original versions/save keys and allowlisted auth return routes.
- 13 real browser scenarios passed against local Supabase/FastAPI. New cases cover auth return to creation, reload drafts, dropped create/edit responses, safe retry, two-tab edit conflicts, titled/untitled lists, custom time/place/notes, independence from My Wines and second-account isolation.
- Desktop 1440px and phone 390px captures inspected. Tested form/list accessibility scans found no WCAG A/AA violations; viewport overflow checks passed. Screenshots contain synthetic data only and remain ignored local test artifacts.
- Production web build, ESLint, TypeScript, Prettier, Ruff and mypy passed. Browser bundle secret check passed for 19 scripts; tracked-file boundary checks passed. Staged secret scanning runs before each commit.

## Limits and next slice

O02 adds an optional existing/new occasion to wine-first capture; O03 adds new wines from an occasion; O04 links existing entries; O05 handles grouping/removal. Current occasions have no wine links, album, deletion, official venue search or participants. Future deletion must redact/tombstone occasion creation receipts so old retries cannot return removed details or resurrect records. Session drafts are interruption recovery, not background offline synchronization. The broader offline capture story remains separate.
