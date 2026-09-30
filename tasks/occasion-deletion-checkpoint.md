# O05: Remove occasions, retain drinking entries

Delivered September 29, 2026. Open an occasion and choose **Delete occasion**. The confirmation defaults focus to **Keep occasion**, supports Escape, identifies the saved context and explains what will be removed and retained.

## Behavior

- The occasion's title, date/time, place and general notes are removed. Its drinking entries become ungrouped, retain their own dates/timezones/places/notes and wine ratings, and advance their versions so stale edits cannot ignore the association change.
- An owned row lock and version check coordinate deletion with capture and association commands. All detachment, receipt cleanup and removal steps commit or roll back together. Migration `0010_occasion_deletion` grants only DELETE on the occasion table; the restrictive FK is unchanged.
- Occasion creation/addition receipts become deletion markers, preserving key claims and preventing resurrection. Surviving entry receipts lose the deleted occasion reference but remain replayable. No deleted occasion notes are returned by old retries.
- Stale context is reread and requires a new confirmation. A lost success response can retry the same version; 404 means the occasion is already absent. Successful removal clears this tab's occasion edit/add-wines drafts, refreshes entry/list reads and removes deleted detail caches.

## Verification

- **92 API tests, 21 web unit tests and 18 browser tests passed.** The browser uses real local Supabase and the production web build.
- API coverage compares all retained entry fields and rating history, rejects foreign/stale requests, checks receipt cleanup/replay, verifies concurrent capture outcomes, injects a failure after detachment to prove full rollback, and checks migration downgrade/upgrade grants.
- Browser coverage verifies three wine cards/four entries, cancellation/Escape/focus, another tab's edit, explicit reconfirmation, a dropped successful DELETE response, draft cleanup, retained entries/ratings and unavailable deleted detail.
- Phone (390 px) and desktop (1440 px) confirmation screenshots were inspected. Overflow and axe checks, lint, types, formatting, build, browser-secret and tracked-file checks passed.
- Local migration was applied without resetting journal data. Both preview services respond successfully.

### Dependency audit follow-up

The first CI run passed API/browser checks but flagged newly reported `brace-expansion` denial-of-service advisories in the lint/API-generation dependency tree ([nested recursion](https://github.com/advisories/GHSA-qhr7-859c-m2p7), [quadratic expansion](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr)). A targeted lockfile update moves the existing major-version lines to 1.1.21, 2.1.7 and 5.0.12. Package manifests and runtime dependencies are unchanged. Installation scripts were disabled for the frozen reinstall; `npm audit` reports zero vulnerabilities. The security follow-up reruns affected tooling/build checks and CI.

## Remaining scope

Media is not implemented. Occasion-owned attachment cleanup and its warning must be added and tested with M06; personal/catalog cover fallback must be rechecked with M08. Other browser tabs can retain unsaved local drafts until discarded or signed out, but the deleted occasion cannot be recreated by its old save key. Cloud deployment and real OAuth registration remain pending.

Next: M01 durable media jobs and R04 photo/storage feasibility, leading into private photos and connected scrapbooks.
