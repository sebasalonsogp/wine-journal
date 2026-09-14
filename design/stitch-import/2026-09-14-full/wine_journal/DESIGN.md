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
  surface-dim: '#e4d8d1'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fef1eb'
  surface-container-high: '#f3e6df'
  surface-container-highest: '#ede0da'
  inverse-surface: '#362f2b'
  inverse-on-surface: '#fbeee8'
  outline: '#857275'
  surface-tint: '#92465a'
  inverse-primary: '#ffb1c2'
  tertiary-container: '#563f2d'
  on-tertiary-container: '#cbab93'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffd9df'
  primary-fixed-dim: '#ffb1c2'
  on-primary-fixed: '#3d0318'
  on-primary-fixed-variant: '#762f43'
  secondary-fixed: '#dde7bf'
  secondary-fixed-dim: '#c1cba5'
  on-secondary-fixed: '#171e06'
  on-secondary-fixed-variant: '#414a2d'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#e1c0a8'
  on-tertiary-fixed: '#291808'
  on-tertiary-fixed-variant: '#594230'
  surface-variant: '#ede0da'
  cream-paper: '#f7f3eb'
  warm-white: '#fffdf8'
  warm-stone: '#ebe6da'
  parchment-line: '#ddd5c9'
  wine-burgundy: '#722c40'
  burgundy-wash: '#f1e4e7'
  grape-leaf-olive: '#555e3f'
  olive-wash: '#e9edde'
  branch-brown: '#795f4b'
  warm-ink: '#332c28'
  muted-ink: '#70665c'
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
    lineHeight: 24px
  label:
    fontFamily: Segoe UI
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  overline:
    fontFamily: Segoe UI
    fontSize: 11px
    fontWeight: '500'
    letterSpacing: 1.8px
    lineHeight: 14px
  display-lg-mobile:
    fontFamily: Noto Serif
    fontSize: 32px
    fontWeight: '400'
    lineHeight: 38px
    letterSpacing: -0.8px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 19.5px
rounded:
  input: 6px
  button: 7px
  panel: 8px
  wine-card: 9px
  preview-shell: 14px
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  control-gap: 8px
  compact-gap: 12px
  field-gap: 16px
  card-gap: 19px
  section-gap: 24px
  page-padding-desktop: 34px
  page-padding-mobile: 18px
  gutter: 1.1875rem
  gutter-mobile: 0.75rem
  margin: 2.125rem
  margin-mobile: 1.125rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.1875rem
  space-xl: 1.5rem
---

# Design System: Wine Journal

A warm, personal wine journal that feels approachable to someone learning about wine and indispensable to an enthusiast. Light cream paper, burgundy headings, olive details, and warm brown accents evoke a personal tasting notebook kept beside a bottle.

## 1. Visual Theme & Atmosphere
- Primary paper background: Cream paper (#F7F3EB) paired with warm-white surface cards (#FFFDF8).
- Typography: Classic, editorial serif (Georgia) for headings, wine titles, and occasion titles; clean, human sans-serif (Segoe UI / Inter) for interface elements, forms, and metadata.
- Tone: Thoughtful, quiet, tactile, personal-first. Not a cold cellar management database, nor a noisy public social feed.

## 2. Color Palette & Roles
- Cream paper: #F7F3EB (main page background)
- Warm white: #FFFDF8 (cards, modal panels, input fills)
- Warm stone: #EBE6DA (bottle silhouette backgrounds, secondary containers)
- Parchment line: #DDD5C9 (subtle dividers and card outlines)
- Wine burgundy: #722C40 (primary actions, brand accents, primary ratings)
- Burgundy wash: #F1E4E7 (active tab states, subtle highlights)
- Grape-leaf olive: #555E3F (metadata overlines, tasting guidance, positive tags)
- Olive wash: #E9EDDE (selected wine pills, status callouts)
- Branch brown: #795F4B (scrapbook accents, caption accents)
- Warm ink: #332C28 (primary body text, crisp reading contrast)
- Muted ink: #70665C (subtitles, secondary labels, timestamps)

## 3. Core Component Patterns
- Navigation: Persistent brand header with "Wine Journal" emblem, global "+ Log wine" button, and 4 primary sections: My wines, Browse wines, Occasions, Guides.
- Wine Card: Warm-white card with subtle warm border, schematic bottle art with vintage tag, producer, release title, grape/region, personal rating, and last tried date.
- Journal Entry Form: Minimal required state (wine + consumed date) with progressive disclosure for time, location, tasting notes, descriptors, and media.
- Occasion Scrapbook: Tactile, scrapbook-inspired arrangement with framed photo mats, memory notes, and connected wine cards.