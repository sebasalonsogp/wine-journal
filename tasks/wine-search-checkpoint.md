# J10: Find a wine in a growing journal

Implemented September 29, 2026. Scope follows the announced defaults after no new preference arrived: search wine name, producer, edition and year; rating status and vintage-type filters; recently tried, case-insensitive name A–Z and highest-current-rating sorts. Different releases remain distinct cards.

## Slices and verification

1. API: `journal/wine_filters.py`, `queries.py`, `routes.py` and focused integration tests. Bound literal search, validate sort/filter options, bind keyset cursors to the owner and filter set, order unknown dates/unrated scores last and break ties by ID. Test all sorted/filtered page boundaries, wildcard literals, Unicode names, cross-owner cursor reuse, edited dates/deleted last entries and changed ratings.
2. Browser: existing My Wines list/detail plus focused filter controls and URL parsing helpers. Apply explicit filter choices into the URL, reset pagination when criteria change, preserve the list state on return from a wine, and distinguish an empty journal from no matches. Test reload/back navigation, a partly remembered label on mobile, error recovery and filtered pagination.
3. Measure query plans on a synthetic multi-account fixture with repeated entries and unknown fields. Compare default/search/name/rating paths; add an index only if measured behavior warrants it. Run regression, visual, accessibility and public-repository checks before publishing.

Queries are live views: changes between page requests can move a wine across a boundary. Stable pagination means deterministic order and no duplicates/skips for unchanged data, not snapshot isolation across edits. Filter URLs contain only navigation choices; every API request still checks ownership.

## Behavior and limits

Search is case-insensitive literal substring matching, requiring every whitespace-separated word to occur across the available label fields. `%` and `_` are ordinary characters, not user-controlled SQL wildcards. Search input is capped at 200 characters and rejects NUL. Unknown years are not fabricated. Accents and spelling are not normalized; fuzzy catalog matching belongs to identification work later.

All orders use ID ascending for ties. Unknown last-drunk dates and unrated scores sort last. A cursor contains the database-evaluated sort value, an ID and a digest binding its owner/options. It is pagination state, not an authorization token or encrypted payload. Changing filters starts a new first page. Pre-J10 wine cursors require a refresh; entry-history cursors are unchanged.

The browser applies search/filters together through a labelled form and stores applied choices in the URL. Reload, browser Back and the detail's Back to My Wines link preserve those choices. A rating cleared from a filtered detail disappears from Rated results on return. Empty search results offer a clear reset. API failures retain controls and offer retry. Private results are never encoded in URLs; a filter link cannot grant account access. Existing sign-in recovery returns to the allowed private pathname and does not retain filter query parameters across an expired session.

## Query evidence

`test_wine_query_plans.py` seeds a disposable database with five accounts, 1,000 wine records and 3,000 drinking entries, refreshes planner statistics, and explains the production queries. One isolated local run measured:

| Query | Rows returned | Execution time |
| --- | --- | --- |
| Recently tried | 21 | 1.367 ms |
| Search producer plus year | 21 | 3.047 ms |
| Name A–Z | 21 | 1.302 ms |
| Rated, highest rating | 21 | 1.143 ms |

These are local single-run planner measurements, not service latency guarantees or a large-scale benchmark. Small-table sequential scans/hashes were generally cheaper; the search plan also used `uq_user_wines_release`. No new index, extension or service is justified by these measurements. Reassess at larger account/library sizes before adding fuzzy/full-text indexing. Per-request wine reads still use one SQL query, including counts and current ratings. Synthetic reports live in ignored `apps/api/test-results/`.

## Verification and outcome

72 API tests, 15 web unit tests and 11 real-browser scenarios pass. New checks cover literal/Unicode search, input bounds, cursor owner/filter binding, all sort/filter page boundaries, entry/rating changes, query counts, URL encoding, filtered pagination, reload/back navigation and failed-request recovery. Desktop (1440 px) and phone (390 px) layouts were inspected together; one spacing correction and a bounded confirmation pass completed the visual review. Axe, type/lint/format, production build and generated-contract checks pass. Browser and staged secret scans gate publication.

No database migration or new dependency was required. J10 and the private manual-journal phase are complete. O01 introduces optional occasions next; photos, videos, recognition and public discovery remain later work.
