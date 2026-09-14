# Wine Journal — Stitch handoff

Snapshot: 2026-09-14, second UX walkthrough. All displayed journals, places, notes, and ratings are sample data.

## Import using the screen you showed

1. Under **Start with your design**, upload `DESIGN.md` or paste its full contents into the DESIGN.md field.
2. Under **Upload code, images, fonts and logos**, add selected PNG references from `screens/desktop` and/or `screens/mobile`. Start with 01 My wines, 02 Wine record, 03 Quick entry, 08 Create occasion, and 10 Occasion scrapbook. If you prefer source references, corresponding self-contained HTML snapshots are in `screens/html`.
3. Paste the contents of `STITCH-PROMPT.md` into **Additional instructions**.
4. Continue in Stitch, then refine one connected flow at a time. The ZIP is a transport bundle: unzip it first and choose the individual files rather than assuming Stitch imports ZIPs.

The interactive prototype is also provided as `walkthrough.html`. It runs locally without Codex or a web server. Screenshots/static HTML expose individual states for design ingestion; they do not reconstruct editable Figma components or promise a lossless import into Stitch.

## Files

- `DESIGN.md`: palette, typography, components, layout, responsive behavior, and product rules in Stitch's documented design-system format.
- `STITCH-PROMPT.md`: ready-to-paste design continuation brief.
- `SCREEN-MAP.md`: screen inventory, scope labels, and journeys.
- `walkthrough.html`: portable interactive reference; edits reset when reopened/refreshed.
- `screens/desktop/*.png`: desktop screenshots at 1024px wide.
- `screens/mobile/*.png`: mobile web screenshots at 390px wide.
- `screens/html/*.html`: static, self-contained screen snapshots; forms and buttons are visual references.
- `screen-index.html`: local visual index of the screen references.
- `THIRD-PARTY-NOTICES.txt`: license notice for included Lucide icons.
- `manifest.json`: source hashes and export inventory.

## Limits to preserve

The prototype simulates identification, sign-in, place suggestions, and community data. Only manual bottle covers are read locally for image preview; scrapbook photo/video uploads are filename placeholders. No live services, durable storage, user accounts, real recommendations, or purchase availability are included.

For you and Trending are later-feature concepts. Basic catalog browsing and a small guide collection remain MVP proposals. Calendar, collaboration, and publication are later work. The rating scale, occasion title requirement, and final mobile navigation still need design review.

The canonical design document for this snapshot is `.stitch/DESIGN.md` in the project. This folder contains its export copy. The project story map and `tasks/ux-review-02.md` retain the full discussion and open decisions.
