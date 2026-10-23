# L02 — Public Wine Guides, October 23

The Guides placeholder now opens four short original articles: first tasting,
wine styles and grapes, food pairings, and regions/labels. Each includes a dated
editorial review, a WSET source link, a journal reflection and catalog searches.
These are introductory guides, not a regional encyclopedia or personalized advice.

## Implementation and content boundary

Typed static content lives in `apps/web/src/content/guides.ts`. Server views in
`features/guides` use the existing burgundy, olive and cream tokens. Thin public
routes generate the four articles at build time, provide metadata and return a
404 with recovery navigation for unknown slugs. No CMS, new dependency, schema,
secret or external runtime fetch is required.

Reading does not save an entry, infer a preference or update a rating. Search
links use the existing catalog navigation helper and ordinary text queries;
they are not geographic filters or recommendations. Limited catalog coverage
is explained alongside the links, including searches with no current matches.

Source review on October 23 covered:

- [WSET tasting information](https://www.wsetglobal.com/knowledge-centre/blog/2019/november/how-to-build-your-wine-tasting-skills).
- [WSET wine types and styles](https://www.wsetglobal.com/knowledge-centre/blog/2023/october/03/how-many-wine-types-and-styles-are-there).
- [WSET pairing principles](https://www.wsetglobal.com/knowledge-centre/blog/2023/july/13/four-rules-to-masterful-food-and-wine-pairing).
- [WSET label features](https://www.wsetglobal.com/knowledge-centre/blog/2019/how-to-read-wine-labels-part-one-common-features-on-wine-labels).

## Verification

The new guest test first failed against the previous placeholder. Both new
browser journeys pass against local services: keyboard opening of all four
articles, direct reloads, active navigation, source/review details, catalog
search/back navigation, empty-result recovery, unknown-slug 404/noindex and no
journal API writes. Index/article axe checks pass; inspected 320px and 1440px
screenshots have readable wrapping and no horizontal overflow.

An intentional slug-comparison mutation served the wrong article and caused
the catalog-link journey to fail. The original source was restored afterward.

All 47 frontend unit tests, lint, formatting, production build/type checking
and the dependency audit pass (zero reported vulnerabilities). Independent
review found no blocking issue; the stale feature README was corrected.
Impeccable flagged the reflection's olive side rule as a visual heuristic;
it is retained as a restrained journal-prompt treatment after screenshot review.
These checks are not physical-iPhone or screen-reader user testing. Exact-head
CI remains required before merge. Taste-profile summaries remain L03.
