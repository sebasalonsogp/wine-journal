# guides

Sourced beginner-friendly wine, region, pairing, and tasting guidance. Guide views do not imply a like or drinking event.

`guide-views.tsx` renders the public index, article and missing-guide views with
existing design tokens. Editorial content lives in `src/content/guides.ts`; thin
App Router pages provide static generation, metadata and unknown-slug handling.
Each guide includes a reviewed date, source and ordinary catalog search links.
There are no account writes, profile inference, runtime content fetches or CMS.

Browser coverage lives in `tests/e2e/guides.spec.ts`: guest/keyboard navigation,
direct article loads, sources, responsive layouts, accessibility, catalog
search recovery and missing-guide status.
