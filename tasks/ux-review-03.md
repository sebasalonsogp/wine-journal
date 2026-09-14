# UX review 03: connected Stitch iteration

Status: interactive design proposal ready for user walkthrough, 14 September 2026. Application implementation remains deferred.

[Open the prototype](../design/prototype-v3/walkthrough.html) · [Walkthrough instructions and limits](../design/prototype-v3/README.md) · [Stitch intake review](stitch-design-review.md)

## Result

The prior working prototype's journal flows now use a visual treatment drawn from the generated Stitch screens: warmer panels, editorial wine titles, simpler collection cards, a wine-record layout with current rating beside identity, and a framed occasion scrapbook. Original Stitch HTML and screenshots were preserved as references.

Quick notes moved into the minimum entry screen. Wine and consumed date remain the only required values. Optional details contain time, place, occasion, and media; guided tasting suggestions are available beside notes. Saving and later editing update the same entry. Canceling returns to the wine record or originating occasion.

Occasion creation remains inline within an entry. It preserves the entry's date/place when occasion details differ. The resulting scrapbook can immediately add another wine. Starting from a new occasion also works: child identification/manual-entry flows return to the parent draft, and new entries are committed with the final occasion save.

One current personal rating belongs to each wine release. Rating history retains previous scores and change dates; same-score saves do not create duplicate revisions. Updating a rating leaves entry counts unchanged. Sorting My Wines by current rating was corrected in the carried-forward prototype logic.

Photos selected locally now render as previews and remain associated with their entry or occasion. Invalid/oversized selections show recovery guidance. Bottle covers remain separate. Sample scrapbook memories are deliberately labeled placeholders rather than copied design screenshots or invented photographs.

## Verified behavior

Browser checks in headless Edge exercised:

- Wine/date-only save and later enrichment of the same entry.
- Current rating, retained revisions, repeated same-score save, and rating sort.
- Inline occasion cancellation and saving with independent entry dates/places.
- Adding a newly identified wine to an existing occasion and returning to its scrapbook.
- Multiple staged wines in a new occasion, including manual creation with a personal cover; parent data survives child cancellation and navigation guards.
- Photo validation errors, previews, retained entry media, and removal.
- Official-place sample selection and replacement with a custom private label.
- Guest lookup without visible personal history, returning from sign-in to the draft, and sign-in resumption.
- Browse, guides, related catalog filters, and separately labeled future discovery concepts.
- Nine screen states at widths 320, 390, 768, 1024, and 1440; no horizontal page overflow or controls extending beyond the viewport. Desktop and mobile core layouts were visually inspected.
- Inline sandbox form saving through buttons and Enter; rating updates leave entry counts unchanged there too. Phone/List presentation option fits.

Standalone checks recorded no page runtime errors or external network requests. Inline checks ran with optional remote helper assets blocked and local icons supplied for inspection. Existing native keyboard focus was retained and basic keyboard activation was checked. A complete keyboard/screen-reader audit and real-device testing remain outstanding.

## Questions for the next user walkthrough

These are review topics, not blockers or approved changes:

1. Does the collapsed entry screen feel fast enough, with quick notes immediately visible?
2. Is optional occasion creation discoverable inside Add details, or should it have a more prominent shortcut?
3. Does the balance between a compact wine record and the more expressive occasion scrapbook feel right?
4. After saving an entry with a new occasion, is landing on that scrapbook useful for adding the next wine?

Before application implementation, resolve the remaining screens and states identified in the Stitch intake review, agree production media limits, and evaluate wine-data/recognition providers. No backend, database, Google integration, authentication service, or public-feed implementation was added by this design iteration.
