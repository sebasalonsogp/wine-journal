# J06: Entry enrichment

## Planned slices

1. J06a — migration `0004_entry_details`, journal models/schemas/routes and `edits.py`, generated contracts, API edit tests. Verify omitted versus cleared values, stale versions, ownership, backdating, timezones, concurrency and upgrades with existing entries.
2. J06b — an entry editor inside wine history, bounded field styles and browser regression tests. Verify save/reload keeps the entry ID, conflict review keeps the draft, and unrelated/private account data stays isolated.

## Contract

The calendar date is the date reported by the drinker. Optional local time and IANA timezone are stored together, without conversion to a UTC instant. Unknown time remains null. Civil time is descriptive: even a daylight-saving overlap is retained as entered; this journal does not infer a unique instant. A date remains unchanged when viewed while traveling.

PATCH requires the version read by the editor. Omitted fields stay unchanged; explicit null clears optional fields. Date cannot be cleared. An atomic version predicate rejects competing edits with 409. The browser must show the latest record alongside the retained draft before the user chooses to replace it. Notes are plain text (10,000 characters); custom place labels are limited to 200. Google Places remains the separate R06/O-series integration.

## API verification

57 API tests pass against disposable Postgres, including omitted/null updates, owner isolation, two simultaneous writers, the midnight/date-line case, daylight-saving overlap, and downgrade/upgrade of existing entries. Runtime UPDATE permission is restricted to editable columns and version. Type checking, formatting, lint and the dependency audit pass. The local Docker database has received the additive migration.

## UI direction

Operate mode; extend the existing wine history. Each dated row exposes Edit entry inline, using the existing cream, burgundy and olive palette and labelled form controls. Keep the date first, optional time alongside it on desktop, and place/notes below. Conflict review shows the saved fields beneath the unchanged draft, with explicit keep-latest or replace actions. No modal or new navigation section. Check both phone and desktop layouts and keyboard/accessibility states in one bounded inspection.

## Browser verification and verdict

The editor passes reload/draft retention, two-tab stale editing with explicit replacement, the unchanged entry ID, clearing optional fields, and recovery after a PATCH commits but its response is dropped. The seven existing browser journeys remain green; the editor adds the eighth. Eleven web unit tests pass. Type/lint/format/build checks pass, and axe reports no violations on the populated conflict form.

Phone (390 px) and desktop (1440 px) screenshots were inspected in one batch. The correction pass aligned desktop form rows and clipped the unfocused skip link correctly on long pages; a second batch confirmed both. No new visual world or raster assets were introduced. Existing design tokens and bottle placeholders are preserved. Verdict: J06 complete. J07 removal is next; official-place lookup, ratings, guided tasting and media remain their own planned tasks.

Edit drafts are tab-scoped, keyed by verified owner and entry ID. When browser storage is blocked the editor warns to save before leaving/switching tabs; full offline sync is not implemented. No passwords, keys, real notes or inbox contents are retained in test artifacts. Secret and browser-bundle scans gate publication.

References: [Pydantic explicit-field serialization](https://docs.pydantic.dev/latest/concepts/serialization/) supports omission handling; [Python IANA timezone support](https://docs.python.org/3/library/zoneinfo.html) explains the cross-platform tzdata dependency.
