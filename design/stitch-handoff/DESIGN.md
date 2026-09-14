---
name: Wine Journal
colors:
  background: '#f7f3eb'
  on-background: '#332c28'
  surface: '#fffdf8'
  on-surface: '#332c28'
  on-surface-variant: '#70665c'
  surface-container: '#ebe6da'
  outline-variant: '#ddd5c9'
  primary: '#722c40'
  on-primary: '#fffdf8'
  primary-container: '#f1e4e7'
  on-primary-container: '#722c40'
  secondary: '#555e3f'
  on-secondary: '#fffdf8'
  secondary-container: '#e9edde'
  on-secondary-container: '#555e3f'
  tertiary: '#795f4b'
  on-tertiary: '#fffdf8'
  error: '#722c40'
  on-error: '#fffdf8'
typography:
  display-lg:
    fontFamily: Georgia
    fontSize: 40px
    fontWeight: '400'
    lineHeight: 44.8px
    letterSpacing: -1.1px
  headline-md:
    fontFamily: Georgia
    fontSize: 27px
    fontWeight: '400'
    lineHeight: 33.75px
    letterSpacing: -0.4px
  title-sm:
    fontFamily: Georgia
    fontSize: 21px
    fontWeight: '400'
    lineHeight: 26.88px
  body-base:
    fontFamily: Segoe UI
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 23.25px
  input:
    fontFamily: Segoe UI
    fontSize: 16px
    fontWeight: '400'
  label:
    fontFamily: Segoe UI
    fontSize: 12px
    fontWeight: '500'
  overline:
    fontFamily: Segoe UI
    fontSize: 11px
    fontWeight: '500'
    letterSpacing: 1.8px
rounded:
  input: 6px
  button: 7px
  panel: 8px
  wine-card: 9px
  preview-shell: 14px
spacing:
  control-gap: 8px
  compact-gap: 12px
  field-gap: 16px
  card-gap: 19px
  section-gap: 24px
  page-padding-desktop: 34px
  page-padding-mobile: 18px
---

# Design System: Wine Journal

Exported 2026-09-14 from the second interactive UX walkthrough. Working product name and design direction; no Stitch project ID has been created. These are design references for continued exploration, not a completed application or approved implementation specification.

## 1. Visual Theme & Atmosphere

A warm, personal wine journal that feels approachable to someone learning about wine and useful to an enthusiast. Light cream paper, burgundy headings, olive details, and warm brown accents evoke a notebook beside a bottle of wine. The palette is an explicit user preference. Keep generous light surfaces and clear text hierarchy as the design evolves.

Wine record keeping is the primary experience: recognizable bottles, distinct vintages, current personal ratings, and a useful history. The secondary occasion experience can become more expressive, with photographs, captions, videos, and short written memories arranged like a scrapbook. Preserve the practical clarity of wine records while giving memories room to breathe. The current silhouettes and photo/video blocks are wireframe placeholders.

## 2. Color Palette & Roles

### Primary foundation

| Name | Hex | Role |
| --- | --- | --- |
| Cream paper | #F7F3EB | Main canvas |
| Warm white | #FFFDF8 | Cards, inputs, menus, and form surfaces |
| Warm stone | #EBE6DA | Capture placeholders and supporting panels |
| Parchment line | #DDD5C9 | Quiet boundaries and dividers |

### Accent and interactive

| Name | Hex | Role |
| --- | --- | --- |
| Wine burgundy | #722C40 | Primary actions, links, main headings, personal rating emphasis |
| Burgundy wash | #F1E4E7 | Subtle selected capture state |
| Grape-leaf olive | #555E3F | Guidance, overlines, secondary emphasis |
| Olive wash | #E9EDDE | Selected wine summary, prompts, confirmation messages |
| Branch brown | #795F4B | Scrapbook detail and secondary decoration |

### Text hierarchy and functional states

Warm ink #332C28 is the main reading color. Muted brown-gray #70665C supports labels and secondary metadata. Burgundy buttons use warm-white text. Olive panels keep sufficiently dark text. The existing prototype reuses burgundy for error messages and olive for confirmations; communicate these states with explicit words and icons too. A complete production status palette is still to be designed.

Cream is the reference surface. A clean white variation is a legitimate design alternative. Avoid replacing the requested palette with dark wine-cellar styling or giving every panel a saturated background.

## 3. Typography Rules

### Hierarchy and weights

Use Georgia or a comparably restrained editorial serif for wine names, occasion titles, and headings. Pair it with Segoe UI, falling back to Arial/sans-serif, for navigation, body copy, labels, and controls. These are system-font references; no font files are included.

The current desktop page heading is 40px, regular weight, with a compact line height and slightly tight tracking. Section headings are 27px; smaller headings 21px. Wine-card names are 23px. Ordinary text is 15px with a relaxed 1.55 line height; editable fields are 16px. Small metadata and labels are 12px. Overlines are 11px, olive, widely tracked, and used sparingly.

### Spacing principles

Use clear spacing between producer, wine name, grape/style, vintage, and region. Important identity information must wrap rather than be cut off. Current mobile headings reduce to about 34px, wine-detail titles to 28px, and card titles to 21px. Typography sizes are starting values to refine for readability, not a reason to shrink essential content to fit.

## 4. Component Stylings

### Buttons

Primary burgundy buttons have gently rounded 7px corners, approximately 10px vertical and 17px horizontal padding, and a minimum 44px height. Secondary buttons are warm white with a thin parchment border. Text actions are burgundy and clearly labeled. Navigation selection has a pale surface and burgundy underline. Retain visible keyboard focus; final hover, pressed, disabled, and loading behavior needs refinement. Motion should be brief, purposeful, and respect reduced-motion preferences.

### Wine cards and wine records

Cards have a thin warm border, 9px corners, and very little elevation. A bottle image occupies the top portion, followed by producer, wine name, grape/style, distinct vintage/edition, and origin. The bottom row shows the current personal score and most recent consumed date. In My wines, default ordering is most recently tried.

Different releases keep separate identities and rating histories. Calculated Risk Barrel Selection 2023 and 2024, and Sonoma County Reserve 2023, are distinct sample records. Any related-vintage grouping must preserve these distinctions. The wine detail screen combines identity/specifications with a chronological entry history and a separate personal-rating panel.

### Navigation

Four destinations: My wines, Browse wines, Occasions, Guides. My wines is the default. Log wine is the persistent capture action. Account contains personal access controls. The desktop reference uses a brand/action row and a destination row. The current phone reference uses a two-by-two destination layout; refining mobile navigation is encouraged while retaining clear access to all destinations.

### Inputs and creation flows

Forms are calm and readable, with labels above full-width controls and a maximum content width of about 680px. Save the selected wine plus consumed date immediately; other details begin collapsed. Date is editable and backdating is supported. Time, location, notes, descriptors, photos/videos, rating, and occasion are optional for a drinking entry.

Location accepts a personal label such as Alex's house. Find a place opens an official-place search, with locality/address to distinguish similar names. Typing over a selected location clears its stale place association. Official lookup is a proposed Google Places integration; the reference uses sample suggestions.

An entry's occasion selector includes Create new occasion inline. That small form preserves the entry and saves both together. From a new or edited occasion, Add a wine opens barcode/photo/search/manual capture and returns to the same occasion. New entries are staged until that occasion is saved. A saved occasion accepts additional wine entries directly. Canceling a child flow keeps the parent draft and previous additions.

### Personal bottle covers and scrapbook media

Manual creation supports a recognizable wine name, optional producer/vintage, and an optional bottle-cover upload with preview/replace/remove. That image represents the user's wine record across encounters. It is separate from a recognition input, entry photos, and the occasion album; it is not automatically published to the shared catalog.

Occasion pages use a prominent title/date/place, readable written memories, linked wine entries, and a photo/video album. Warm-white photo mats, small captions, a subtle olive accent, and occasional slight rotation suggest a scrapbook. Avoid making controls or long text crooked. A memory without media still needs a useful layout. Video previews need an explicit play affordance.

## 5. Layout Principles

### Grid and structure

The reference fills its available web width. Desktop exports use 1024px; phone exports use 390px. The shell's 14px outline frames the mockup and is not a requirement for a production browser window.

My wines uses three columns on wide screens, two below approximately 780px. Detail pages have a main history column and a narrower specifications/rating column, collapsing to one column. Occasions and guides use two columns on desktop and one below approximately 500px. Media uses three columns, reducing to two on smaller screens. A list presentation for My wines is an existing design alternative.

### Whitespace and balance

Desktop content uses about 30–34px edge spacing, reducing to 18–25px on smaller screens. Fields commonly use 16px gaps, cards about 19px, and major sections about 24–28px. This is an observed spacing rhythm, not a fully normalized spacing scale. Align record metadata and actions; keep the scrapbook expressive within readable boundaries.

### Responsive behavior and accessibility

Support widths down to 320px without clipping. Long wine/occasion titles and file names must wrap. Keep comfortable touch targets, keyboard operability, visible focus, properly labeled inputs, and readable contrast. Preserve native date/file controls where useful. A phone-sized web design is not yet a native iOS design.

## 6. Design System Notes for Stitch Generation

### Language to use

Warm editorial wine journal; cream paper; burgundy primary actions; olive guidance; branch-brown details; approachable learning; distinct bottle identities; quick capture; private memories; gentle scrapbook treatment.

### Product rules to preserve

1. Guests can scan/photo/search and read wine details or guides. Sign-in is requested when saving a personal record, with the pending input preserved.
2. Looking up a bottle does not record drinking it. Saving a drinking entry needs only wine identity and consumed date.
3. A drinking entry stands alone. Occasions are optional, deliberate groups; several wines can belong to one occasion.
4. An entry retains its consumed date, optional time/location, notes, and media. Occasion date/time/location provides context and optional defaults; it must not overwrite existing entry details.
5. One current personal rating belongs to each distinct wine/release. Updating it retains previous values and change dates; it does not create a drinking entry or average past revisions into the current score.
6. Keep private notes, covers, locations, and memories private. Public reviews and ratings are a later, explicit publication path.
7. Browse has catalog, For you, and Trending directions. Basic browse can precede personalization. Recommendations and public trends are future concepts; sample public scores must be labeled as invented examples.
8. Guides cover tasting words, grapes/styles, pairings, and regions. Reading a guide does not imply liking or drinking a wine. Contextual learning can connect to the taste profile later.

### Component prompts

- Refine the My wines collection: clear bottle identity and vintage, current personal rating, most recent date, practical filtering, and warm editorial typography.
- Refine the entry form: wine and date first; optional enrichment; official or custom location; inline occasion creation that preserves every entered field.
- Refine the occasion scrapbook: several wines, notes and personal memories, with Add a wine available during creation and after saving.

### Incremental iteration

Begin with My wines, Wine record, Log entry, Create occasion, and Occasion scrapbook. Review both creation loops before polishing Browse and Guides. Calendar, participants/shared albums, a public feed, deep tasting assessments, and full recommendation infrastructure are later work. The 1–5 rating scale with half steps and optional occasion title are still design proposals.

Use the provided PNG and static HTML screens as references. Refine layout, spacing, and visual craft while preserving these product rules. Keep empty, loading, no-match, permission-denied, upload-error, and unsaved-change states in the next design pass. Do not treat this handoff as authorization to scaffold or implement the application.
