# Wine identity and browsing: research and product decisions

Research date: September 13, 2026. Status: product discovery draft. This document informs [story-map.md](story-map.md) and [occasion-journeys.md](occasion-journeys.md); it does not prescribe a database schema or start development.

## What the user clarified

Distinct wines, years, and releases must retain their identities. The user cited Calculated Risk Cabernet Sauvignon and requested research into how its offerings are separated. My Wines should organize those records intuitively and offer sorting/filtering. The user did not select a mandatory one-card-per-family or one-card-per-vintage layout.

The established rating behavior still applies: one current personal score for the wine being rated, with past scores and change dates. Our working interpretation is to apply this to each identifiable vintage/release. Grouped browsing must not silently combine those ratings. This is a product recommendation derived from the uniqueness requirement, rather than an industry-mandated rating policy.

## What the producer sources show

Calculated Risk lists the following separately in its [official catalog](https://calculatedriskwinery.com/collections/all). This is a sample of its offerings, not an exhaustive historical catalog.

| Brand | Named offering | Origin on listing | Vintage | Product interpretation for this app |
| --- | --- | --- | --- | --- |
| Calculated Risk | Cabernet Sauvignon, Barrel Selection | Napa Valley | 2023 | One identifiable release |
| Calculated Risk | Cabernet Sauvignon, Barrel Selection | Napa Valley | 2024 | Another vintage of the same named offering |
| Calculated Risk | Cabernet Sauvignon, Reserve | Sonoma County | 2023 | A different offering, even though the brand, grape, and year can overlap |
| Calculated Risk | Cabernet Sauvignon | Howell Mountain | 2023 | Another separately marketed offering |

Individual producer pages: [Barrel Selection 2023](https://calculatedriskwinery.com/products/2023-cabernet-sauvignon-barrel-selection-napa-valley), [Barrel Selection 2024](https://calculatedriskwinery.com/products/napa-valley-barrel-selection-cabernet-sauvignon-2024), [Sonoma County Reserve 2023](https://calculatedriskwinery.com/products/2023-cabernet-sauvignon-reserve-sonoma-county), and [Howell Mountain 2023](https://calculatedriskwinery.com/products/howell-mountain-cabernet-sauvignon-2023).

The producer also organizes [trade resources](https://calculatedriskwinery.com/pages/trade) by offering and vintage. The linked 2023/2024 Barrel Selection PDF downloads were not retrievable in this research pass; the examples above rely on the readable product pages. Prices and stock status are not necessary to determine identity and are not recorded as current offers here.

Three further distinctions matter:

1. **Vintage describes harvest year.** It is separate from when the wine was purchased, released for sale, or drunk. The US TTB explains vintage and origin as distinct label information. This is useful terminology evidence, not a universal global catalog schema. [TTB: Anatomy of a wine label](https://www.ttb.gov/regulated-commodities/beverage-alcohol/wine/anatomy-of-a-label)
2. **A year alone cannot describe every release.** Krug Grande Cuvee has numbered editions made from multiple harvest years. Its 173rd edition includes wines from 13 years. A base harvest year must not be substituted for a declared single vintage. Our identity model therefore needs room for explicit editions and non-vintage/multi-vintage wines. [Krug: Grande Cuvee 173rd edition](https://www.krug.com/en-int/champagne/krug-grande-cuvee-173eme-edition)
3. **A barcode alone does not always resolve the vintage.** GS1 Slovakia illustrates both different GTINs for different vintages and a shared GTIN qualified by a consumer product variant. A barcode lookup may identify the named wine while leaving its vintage unresolved. [GS1: Wine products](https://dl.gs1sk.org/standard/wineProducts)

## Recommended conceptual distinctions

These are app design concepts inferred from the sources and journal requirements. They are not a claim that every winery uses identical naming rules.

| Concept | Meaning in this product | Example / boundary |
| --- | --- | --- |
| Brand / producer | The identity under which a wine is marketed, with producer information where known | Calculated Risk; avoid assuming brand, bottler, and producer are always the same entity |
| Named wine | The particular offering, using its name/designation and distinguishing origin, vineyard, or style where applicable | Napa Valley Barrel Selection Cabernet Sauvignon; Sonoma County Reserve remains separate |
| Identifiable release | A particular vintage and any explicitly distinguished edition/release | Barrel Selection 2023 versus 2024; numbered editions can exist without one declared vintage |
| Bottle format / package | Size and packaging associated with a product | Proposed default: a size change alone does not create another personal wine rating; preserve format if useful |
| Drinking entry | The user's encounter with that wine/release, with consumed date, optional time/place, observations/media, and an optional occasion link | A sample and a glass at home retain two entries and one current personal score/history without requiring occasions |

Known years, explicitly non-vintage/multi-vintage wines, and unknown vintage information are distinct states. Unknown does not mean non-vintage. Explicit release/edition details can coexist with vintage information; a lot number or label redesign is not automatically a separate rated wine. Preserve useful evidence and refine exceptional cases when representative examples justify them.

Name, grape, region, barcode, and year are matching evidence. No single field or concatenated display name should be assumed to be a universal identifier. Similar text alone must not merge user records. Detailed catalog matching and schema constraints belong to the later architecture phase.

## Rating and occasion behavior

- Recommended: each identifiable release retains its own current personal rating and dated revisions. A 2023 rating does not change the 2024 score.
- Drinking the same release again creates another entry, optionally linked to an occasion; it does not require a new score or create a separate physical-bottle rating. Everyday entries require no occasion.
- Grouping several vintages for browsing must keep their ratings labeled. Do not invent a family-wide current rating by averaging revisions or selecting whichever vintage was rated most recently.
- Two different vintages can appear at the same dinner with separate observations. Both point to the same occasion scrapbook.
- If the named wine is known but the vintage/release is unresolved, the recommended quick-save route retains the date and known identity with a clear indication of what remains unknown. This differs from saving an entirely unidentified photo (EX-02).
- Any rating on an unresolved record stays attached to that unresolved personal identity; it must not become a rating for every known vintage. Correcting identity later preserves drinking entries, optional occasion links, and memories, and requires a deliberate resolution if the target already has a current rating. Exact correction interaction is still open.

## My Wines: recommended starting point for UX exploration

Keep recognizable wine records visible with enough information to distinguish what was drunk: label image when available, producer/brand, named offering, origin, vintage or edition, current personal rating, and last consumed date. Missing information should remain visible as unknown.

Start the first wireframe with distinct releases as individual items, sorted by most recently consumed. Show a related-vintages link or grouping option as an alternative to test. This is a proposed layout, not a selected user requirement. No final default card grouping has been chosen.

| Control | User outcome | Suggested initial scope |
| --- | --- | --- |
| Search within My Wines | Find a partly remembered bottle by name/producer/designation | MVP target |
| Sort | Reorder by most recently consumed, name, or current personal rating | MVP proposal for the exact options; configurable sorting is requested |
| Filter | Narrow by wine type, origin, vintage/edition, rating, or consumed-date range | MVP target for filtering; prioritize the exact set in UX review |
| Group related records | Browse a named wine's vintages together or organize by producer | UX proposal to test; identities and scores stay separate |
| Compare releases side by side | Explore how related vintages differ | Later opportunity; basic identity distinctions do not commit a comparison feature |

Sorting changes order; filtering changes which records appear; grouping changes presentation. None changes identity, rating scope, or optional occasion membership. Group totals should distinguish named wines, identifiable releases, drinking entries, and explicitly created occasions. Rating sorts need an explicit unrated placement; unknown filter values should remain recoverable. Save-view preferences and advanced combined filters are not yet scoped.

## Stories and review scenarios

Related stories: WC-01, WC-04, WC-06, WI-01 through WI-03, HB-01 through HB-03, HB-06, TP-04, TJ-05.

| Scenario | Expected product behavior |
| --- | --- |
| Search Calculated Risk Cabernet Sauvignon | Show distinguishing offering/origin/vintage information rather than one ambiguous result |
| Record Barrel Selection 2023 and 2024 | Preserve two releases and their independent current ratings/history under the working rating recommendation |
| Drink Barrel Selection 2023 three times | Preserve three entries, with or without optional occasion links; reuse that release's personal rating history |
| Add 2023 and 2024 to one dinner | Keep both wines/observations distinct and link both to the same scrapbook |
| Sort or group the library differently | Preserve the same entries, scores, and memories; grouped displays do not invent a combined score |
| Scan a code that identifies the offering but no vintage | Show known details immediately; allow clarification and the proposed save-with-unknown route |
| Identify Krug Grande Cuvee 173rd edition | Retain the edition and its multi-vintage character; do not label it simply as a 2017 vintage |
| Add an old drinking entry today | Order it by its consumed date; editing/uploading today or linking an occasion does not move the wine to the top unless warranted by its drinking history |

## Remaining decisions

- Validate the proposed initial list/grouping and smallest useful filter set through low-fidelity UX.
- Choose rating scale and accidental-rating correction/removal behavior.
- Resolve conflicts when correcting an unresolved or mistaken identity into an already rated release.
- Free-form notes plus optional beginner guidance are now MVP direction. [Tasting notes research](tasting-notes.md) proposes prompts and remaining UX choices.
- Keep advanced bottle/lot tracking, collection inventory, and global catalog curation outside the current MVP unless a concrete story changes that scope.
