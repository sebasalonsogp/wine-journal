# Screen map

Desktop references are 1024px wide; mobile web references are 390px. Each state has a PNG and static HTML at both sizes.

| File prefix | Screen | Purpose / scope |
| --- | --- | --- |
| 01-my-wines | My wines | Primary private journal |
| 02-wine-record | Wine record | One release, repeated encounters, current rating |
| 03-quick-entry | Quick entry | Wine and consumed date only |
| 04-entry-new-occasion | Entry with new occasion | Create an occasion inline; preserve the entry |
| 05-find-barcode | Barcode lookup | Simulated capture; search/manual fallback |
| 06-photo-matches | Photo match candidates | Simulated recognition; distinguish releases |
| 07-manual-wine | Manual wine and cover | Personal identity and optional cover image |
| 08-create-occasion | Create occasion with new wine | Return from wine capture to the unsaved occasion |
| 09-occasions | Occasions | Secondary view of deliberate gatherings |
| 10-occasion-scrapbook | Occasion scrapbook | Several wines, notes, and memories |
| 11-browse-wines | Browse wines | Catalog exploration; MVP proposal |
| 12-for-you | For you | Future personalized-discovery concept |
| 13-trending | Trending | Future public-community concept; invented scores |
| 14-guides | Wine guides | Curated learning; MVP proposal |
| 15-tasting-guide | Tasting guide | Optional beginner learning |
| 16-rating-history | Rating history | Current opinion independent of encounters |
| 17-place-picker | Official or custom location | Sample places; custom label always valid |
| 18-sign-in | Sign in to save | Simulated account transition preserving the entry |

## Priority journeys

- Wine first: 01 -> 02 -> 03 -> 04 -> 10. Create an occasion inline only when wanted.
- Occasion first: 09 -> 08 -> 05/06/07 -> 03 -> 08 -> 10. Adding a wine returns to the parent draft.
- Learn and discover: 11 -> 14 -> 15 -> relevant catalog filter. 12 and 13 are later concepts.
- Rating update: 02 -> 16 -> 02. No new drinking entry.
- Guest save: 05/06 -> 02 -> 03 -> 18 -> saved entry.
- Optional location: 03 -> 17, or the corresponding control in 08.

## Next design coverage

Refine empty first-use states, identification correction, lookup failure, denied camera/location permissions, media upload progress/error, unsaved-change recovery, delete/unlink distinctions, and mobile navigation. Existing references show selected states rather than a complete production state machine.
