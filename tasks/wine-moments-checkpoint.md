# M07 — Moments with this wine

Status: implementation in progress, October 16, 2026.

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
