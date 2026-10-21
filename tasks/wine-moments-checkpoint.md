# M07 — Moments with this wine

Status: implemented and functionally verified, October 16, 2026. Closeout awaits
the existing development dependency audit fix; M07 remains unchecked.

Backend slice verified: all 303 API tests passed with real private Storage and the
isolated Docker decoder enabled. Ten focused album/moments tests passed. Ruff,
strict typing (115 source files), package build and Python dependency audit passed.
OpenAPI and browser types were regenerated; this adds one private read endpoint
without modifying existing operations or database schema.

## Implementation slices

1. Add media/wine_moments.py, wine_moment_routes.py and router registration;
   generate OpenAPI/types. Test exact eligible assets, source dates/ties, repeated
   occasion links, backdating, pagination, ownership, unlinks and cover exclusion.
2. Add my-wines/wine-moments.tsx to wine-detail, reusing private photo rendering;
   verify three highlights, the full paginated gallery, source navigation, empty
   state omission, sign-out, desktop/mobile appearance and accessibility.

## Contract

GET /api/v1/me/wines/{wine_id}/moments is private and no-store. It selects READY
assets from active photos on this wine's entries and active direct photos on
occasions currently linked to this wine. Repeated links use EXISTS, so an occasion
reference contributes once. Other wines' entry-only photos are never included.
Assets currently used as a personal cover are excluded even when also attached
as memories. Removing a cover restores otherwise-eligible memory membership.

An asset's latest eligible source date determines its position and representative
source. Ties prefer entry sources, then source UUID ascending; cards sort by date
descending and asset UUID ascending. Source dates are consumedDate for entries
and occasionDate for general occasion photos. Deduplication precedes pagination.
The cursor is scoped to account and wine. Pages are live, not snapshots: changing
dates, links or references requires reloading from the beginning.

No new schema, storage copy, public endpoint, signed URL or original object path is
needed. The browser requests three items for highlights and 20 for the full gallery;
the API bounds pages to 50. Source links open the precise entry or occasion.

## Browser behavior and verification

The wine page shows three highlights and a View all memories link; the same route
expands with `?moments=all` and bounded Load more memories pages. Duplicate assets
are suppressed across live pages. Reload starts from the first page. Empty results
omit the section; errors retain a retry action. Focused entry links open only their
original entry, with a return to full history. Captions and processed thumbnails
reuse the existing private viewer. Guest views never mount the component.

Entry edits/deletion, occasion reassociation, cover changes and saved-entry photo
reads invalidate highlights. Quick capture's shared photo editor accepts an
optional change callback and does not require the private journal query provider.
This boundary was corrected after the full browser regression exposed an overly
broad cache hook; the final run passed all 25 scenarios.

The new real Storage/Docker journey covers empty omission, three ready photos,
shared references, other-wine exclusion, a new general occasion reference,
precise entry/occasion links, full-gallery pagination, network failure/recovery,
immediate entry-deletion refresh and guest/sign-out isolation. It requests smaller
real API pages for pagination; backend fixtures separately verify five eligible
assets and the exact three-item preview. Initial test setup errors were corrected
to await account initialization and respect removed-reference tombstones.

Desktop (1440px) and phone (390px) captures were visually inspected. These images
are synthetic one-pixel pipeline fixtures, not representative photography. No
horizontal overflow or axe WCAG A/AA violations were found. Impeccable's detector
reported no findings. All 32 unit tests, lint, formatting, strict types and the
production build passed. Staged-secret and built-browser credential checks passed.

## Remaining work

On October 16, production npm and Python audits reported no vulnerabilities. The
full npm audit still reports five development-package findings originating in
braces GHSA-vfj7-8cjw-p6xm, through Next's lint dependency chain. Its proposed forced
Next 14 lint downgrade was not applied; the full audit gate remains unchanged.
See the [earlier investigation](occasion-album-checkpoint.md#dependency-audit-follow-up-october-12).

M08 safe physical storage cleanup/quota release is next. Physical iPhone testing,
video, recognition and deployment remain separate planned work. No new dependency,
schema migration or environment setting was introduced for M07.
