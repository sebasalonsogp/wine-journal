# First UX walkthrough

The next review is [UX review 02](ux-review-02.md), which responds to the user's feedback on location selection, inline occasion creation, adding new wines during occasion creation, manual bottle covers, Browse Wines, and Guides. This document preserves the first-pass context; its two-item navigation and missing nested creation controls are superseded by that revision.

Status: ready for a first user design review, not approved application design. The user explicitly requested UX/wireframing before application code, and selected a direction combining burgundy, olive, branch brown, and cream/white. The walkthrough is an in-conversation design prototype; no application scaffolding or backend has been created.

## What this pass should help us decide

- Can a casual user record a wine quickly and add details later?
- Is a wine record clearly different from a drinking entry and an optional occasion?
- Does wine-first browsing stay practical while the occasion view feels like a scrapbook?
- Can someone find guidance without being forced through a tasting form?
- Does the palette feel warm and readable on both desktop and phone-sized screens?

## Proposed visual direction

| Role | Initial choice | Purpose |
| --- | --- | --- |
| Main canvas | Cream, #F7F3EB | A light paper-like surface for long-form notes and browsing |
| Cards / form surfaces | Warm white, #FFFDF8 | Separate records and controls from the canvas |
| Primary accent | Burgundy, #722C40 | Primary actions, wine titles, personal rating emphasis |
| Secondary accent | Olive, #555E3F | Guidance, subtle labels, supporting context |
| Supporting detail | Branch brown, #795F4B | Warm details and scrapbook accents |
| Main / secondary text | #332C28 / #70665C | Readable text distinct from decorative color |

These are exploration values, not approved tokens. The prototype's design controls allow cream/white, color changes, web/phone size, and card/list library presentation. Contrast and responsive behavior should be reviewed again after any palette changes.

Typography direction: a restrained serif for wine and occasion headings, paired with a familiar sans serif for navigation, labels, and notes. Bottle art and media blocks are schematic placeholders; photography, brand identity, and detailed scrapbook composition remain later design work.

## Screen map and story coverage

| Screen / state | Main action or question | Stories represented |
| --- | --- | --- |
| My wines | Browse distinct releases; search, type filter, recent/name/rating sort | HB-01, HB-03, HB-06, WC-06 |
| Wine record | View details, all drinking entries, and current personal rating/history | WC-02, WC-05, HB-02, TP-04 |
| Find a wine | Text results, sample barcode match/failure, sample photo candidates, manual fallback | WC-01, WC-03, WI-01 through WI-04 |
| Quick entry | Save selected wine and date; other fields are collapsed initially | TJ-01, TJ-03 |
| Entry enrichment | Optional time/location, occasion link, notes, prompts, media affordance | TJ-04, TJ-07, OM-01, OM-02 |
| Rating history | Change this release's score without creating another drinking entry | TP-04 |
| Occasions | Browse deliberately created groups, create an occasion | HB-05, TJ-08 |
| Occasion scrapbook | Revisit notes, linked wines, general album, and entry-memory previews | TJ-05, OM-04 |
| Occasion editor | Title/date/time/location; link or unlink already saved entries | TJ-08, TJ-09 |
| Guest / sign-in transition | Read wine information as a guest; preserve the pending wine/date when saving | AC-01, WC-02 |

Primary navigation is My wines and Occasions, with Log wine always available. Account navigation is minimal. The taste-profile screen, public feed, collaboration, and calendar are not included in this first walkthrough.

## Review journeys

### 1. A quick glass at home

Open a wine -> Log this wine -> retain/change date -> Save entry. Do not create an occasion. Return to its wine record and confirm the new entry appears. Open the entry later, expand optional details, and add location or a short note.

Review: Is the minimum path obvious? Does the optional-details control conceal anything that should be easier to reach?

### 2. Learn to describe a wine

Open an existing entry -> Help me describe it -> choose or remove a broad descriptor -> read an optional term explanation -> write personal notes -> Save. Then open Rating & history on the wine record and change the rating separately.

Review: Does guidance feel useful and optional? Is the separation between observations from one encounter and the current opinion of a wine understandable?

### 3. Build an occasion after dinner

Open Occasions -> New occasion -> add title/date/location/time -> select existing entries -> Save occasion. Open the scrapbook, then an entry or wine record. The original drinking dates and notes stay intact.

Review: Can people distinguish event context from actual drinking details? Is the link between the practical wine record and the more expressive scrapbook clear?

### 4. Lookup without an account

Open Account -> Sign out -> Find a wine. Try text lookup, Use sample barcode, or Use sample label photo. View details without saving. Choose Log this wine -> date -> Sign in to save -> simulated sign-in -> saved entry.

Review: Is the sign-in request placed at the right point? Is it clear that lookup alone does not record consumption?

## Choices deliberately left open for review

- Distinct-release cards are the default; the design controls also offer a list. Related vintages remain separate records and can be reached through Other vintage.
- The illustrative rating input uses 1–5 in half-point steps; the user has not yet selected the final scale.
- An occasion title is optional in this pass, and an occasion can be created before linking wines. Those behaviors remain proposals.
- New entry details are initially collapsed; editing a saved entry expands them.
- The starting filter set is intentionally small: search and wine type, plus date/name/rating sorting. Additional origin, vintage, or date-range filters require prioritization.
- A newly logged entry can inherit occasion date/location when capture began inside that occasion. Exact drinking time remains unfilled.
- Changing occasion context or linking old entries does not rewrite their date, time, or location.
- General occasion memories and entry-specific memories are displayed in separate groups. Combined-gallery presentation is not yet decided.

## Prototype boundaries

The starting journal uses sample dates, ratings, notes, locations, and people. Bottle silhouettes are illustrative. Product identity examples come from the prior research, but this prototype is not a live catalog.

Navigation and sample edits are local to the walkthrough and reset when it is reloaded. Barcode/photo recognition and sign-in are explicitly simulated. The file controls record selected filenames/types for placeholder cards; no file contents are uploaded, persisted, or played. Media blocks represent layout and affordances, not actual photos or video playback. Producer links go to the actual producer pages previously researched.

This first pass is not a completed acceptance test or validated accessibility review. Later passes need unsaved-change recovery, mistaken identification corrections, deletion/unlink confirmation and undo, authentication failures, real media progress/error states, empty first-use states, and keyboard/focus review. A native iOS design is also separate from the phone-sized web layout.

## Next review output

Record feedback as a concrete change tied to a journey or screen: what was expected, what was confusing or missing, and what to try next. Update the story map when design reveals a product change. Do not treat visual polish or a clickable mock as authorization to implement the application.
