# J08–J09: Current wine ratings and dated history

## Scope and decisions

One current private rating belongs to an owned wine release. Changing an opinion creates no drinking entry and never averages previous ratings. Default scale: 1–5 in half-star steps, consistent with the prototype and the stated assumption after the optional preference question. Stored units are integers 2–10; JSON/UI use 1–5; null means unrated.

Same-value updates with the current version are no-ops. Clear rating appends a null revision and preserves history. Delete rating history requires a separate confirmation and atomically removes the history and current score. Erasure always advances the version, preventing stale pre-erasure writes. Wrong-owner IDs return 404; stale versions return 409, including stale retries of a successful change. No operation implicitly creates an occasion or drinking entry.

## Implementation slices

1. **J08 storage:** journal models and migration `0006_ratings`; owner-scoped foreign key and database score/version constraints. Verify upgrade over existing wines, schema drift and restricted runtime grants.
2. **J08 API:** journal rating schemas, use case, routes, and current-score fields in the existing list/detail query. Verify ownership/release isolation, concurrent writers, rollback, no-op/clear/erase behavior, unchanged entry counts and stable bounded history pagination. Current score/version update and revision insertion share a row-locked transaction with a three-second lock deadline.
3. **J09 UI:** `wine-rating.tsx`, bounded account/wine-scoped `rating-draft.ts`, existing list/detail/CSS, and unit/browser coverage. Keep the cream/burgundy/olive design, a labelled native score selector, expandable history and browser-native destructive confirmation. Read dates in the viewer's local timezone. Do not average history or create fake community ratings.

## Recovery and privacy

Unsaved choices retain their original version through reload and session focus checks. When the version differs, show current/unsaved choices and require a deliberate keep-or-discard decision before saving. A dropped success response refreshes current/history state; it does not retry with a newer version automatically. Sign-out clears the existing private-draft namespace. No tokens or email codes enter draft storage.

Mutations invalidate current-wine, wine-list and rating-history queries. Taste-profile queries do not exist yet; their invalidation belongs to L03 when introduced. The browser fetches revisions only when expanded, 20 at a time. Current scores are selected with each wine card, avoiding per-card rating requests. No new dependencies or external integrations were added.

## Verification

- 64 API tests pass on disposable Postgres, including six new rating integration scenarios and migration upgrade/downgrade/schema checks.
- 13 web unit tests and all 10 real-browser scenarios pass against local Supabase/FastAPI.
- The rating browser scenario verifies 4 → 4.5, reload/history, two-tab draft conflict, explicit resolution, lost clear response, cancel/confirm erasure, unchanged entry count and empty history after reload.
- Phone (390 px) and desktop (1440 px) screenshots were inspected together; content fits both widths and the rating page passes axe WCAG A/AA checks. No additional visual correction was needed.
- API/web lint and type checks, formatting, generated contracts and production build pass. Browser and staged secret scans gate publication.

Local Supabase was upgraded additively, preserving existing records and ignored environment files. J08/J09 are complete; J10 search/filter/sort is next. Recognition, media, occasions and public ratings remain separate future work.
