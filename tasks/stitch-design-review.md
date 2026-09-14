# Stitch export intake — 14 September 2026

Status: initial design review for the next UX iteration. The generated screens are visual proposals; they do not replace our agreed product behavior. No application scaffolding or production implementation was performed.

## Imported baseline

The updated `stitch_wine_journal_mvp_design_system.zip` contains 14 generated screens, each with `code.html` and `screen.png`, 18 original reference images, the three original handoff documents, and a generated `wine_journal/DESIGN.md`: 50 files total.

The export is preserved in [the screen index](../design/stitch-import/2026-09-14-full/README.md). Its manifest records the archive hash and each imported file's hash. The earlier single-image import remains separate. The generated design-system document is retained as a proposal; it has not been promoted over our existing product requirements.

All 14 generated screenshots were visually inspected. HTML was inspected for structure, external dependencies, and interaction hooks. This was not a browser interaction test or an accessibility audit. The HTML includes small demonstration interactions, many placeholder links, and external Tailwind/font/image references; it is not yet a connected application or a guaranteed offline walkthrough.

## Direction worth keeping

- The burgundy, olive, cream, and warm-brown palette fits the personal journal concept. Serif wine and occasion titles add character, while straightforward labels can keep the controls approachable.
- My Wines remains the primary collection with producer, release, vintage, current rating, and last-tried date. Separate releases retain separate cards.
- The occasion scrapbook successfully gives memories more visual space. Its desktop version distinguishes occasion photos from media belonging to individual wine entries.
- The entry form retains the wine-and-date minimum, optional details, custom place labels, a place picker, and inline occasion creation. The occasion draft retains an Add a wine action and a separate option to link existing entries.
- Photo matching asks the user to distinguish releases and vintages. Lookup screens explicitly state that identifying a wine does not create a drinking entry.

## First iteration priorities

| Priority | What the export shows | Proposed correction |
| --- | --- | --- |
| 1 | Several generated screens embed the original wireframe screenshots as bottle artwork, camera previews, guide illustrations, or “visual inspiration.” Mobile My Wines also includes an Editorial Blueprint Mode control. | Remove reference material and design-review controls from the product screens. Use a bottle cover, a neutral placeholder, actual selected-photo preview, or appropriate editorial artwork for each role. Keep demo controls outside the product experience. |
| 1 | The rating-history screen correctly describes one current rating per release, but calls revisions “logged sessions” and associates history with encounter dates. Wine-record copy suggests a score based on tastings. | Label the history as rating changes with change dates. Updating a rating must work without logging a new drink. An optional linked entry may explain a change, but is not required. Display the user's current selected score, never an average of revisions. |
| 1 | Browse adds a “Cellar Index” of 95 and other unexplained scores. Photo matching adds “98% conf” and “92 pts Cellar.” | Remove unsupported scores and confidence claims from the MVP design. Keep personal ratings explicit. Any later public or critic score needs a defined source, scale, and context; For You and Trending remain future concepts. |
| 1 | Wine example facts change between screens: the Barrel Selection occasion draft says Cabernet Franc, while the wine record says Cabernet Sauvignon; rating history adds Ribera del Duero/Tempranillo. | Use one consistent sample record per distinct wine/release throughout the walkthrough. Mark illustrative metadata as sample data. Added alcohol, aging, coordinates, and drinking-window claims need verification before being treated as real wine information. |
| 2 | Mobile cards and filter strips visibly clip some release names and controls. Some detail screens repeat back navigation. | Preserve enough title space to distinguish releases and vintages. Make overflow intentional and discoverable. Use one clear back action that returns to the originating flow. Check the layouts at actual phone widths rather than inferring viewport sizes from the resized export PNGs. |
| 2 | Save as draft, bookmarks, share icons, microphone input, weather companions, and specific upload limits appear without an agreed behavior. | Treat these as proposals, not new requirements. Prioritize quick saving and later enrichment. Keep persistent drafts, public sharing, and added discovery features outside this iteration unless separately scoped. |
| 2 | “Cellar,” “vault,” and “sensory ledger” are used throughout, including simple forms. The design system also contains overlapping palettes and multiple font families. | Prefer plain journal language in task controls. Retain expressive copy for scrapbook moments. Consolidate colors and typography before building reusable frontend components. |

## Connected flows still to validate

The export provides useful screen states, but these transitions and outcomes still need a connected walkthrough:

1. **Guest lookup to save:** search/barcode/photo -> verify the exact release -> inspect specs without logging -> choose Log wine -> sign in -> resume the same wine/date draft.
2. **Fast personal entry:** wine + date -> save with no occasion, rating, place, or media -> reopen and enrich later.
3. **Wine first, new occasion:** create an occasion inside the entry flow -> retain the entry's notes and location -> save both; cancel occasion creation without losing the entry.
4. **Occasion first, new wines:** keep the occasion draft while identifying or manually adding multiple wines -> return after each -> save once. Canceling a child flow preserves the parent; linking an existing entry preserves that entry's original date/time/place.
5. **Rating revision:** update the current release rating -> retain the old score and change date -> leave drinking-entry and occasion counts unchanged.
6. **Memory ownership:** distinguish personal bottle cover, recognition input, entry media, and general occasion memories; none become public implicitly.

There are no separate generated screens for the occasion index, guest sign-in/resumption, guide article, or collapsed minimal entry state in this export. Some exist as original references, and the generated form may contain related controls. Their final visual treatment and interactions remain to be designed. Recognition failure/permission states, empty states, and save/upload failure recovery also need walkthrough coverage.

Recommended next deliverable: a revised, connected design walkthrough using this visual direction and the existing [UX flow decisions](ux-review-02.md), beginning with My Wines -> Wine record -> Log entry -> optional new occasion. Finish validating these flows before application implementation.
