# UX review 04: wine covers and connected memories

Updated the [connected prototype](../design/prototype-v3/walkthrough.html) in response to the user's three observations. Application implementation remains deferred.

## Accepted refinements

1. **Browse Wines first:** desktop and mobile navigation now read Browse Wines, My Wines, Occasions, Guides. Moving the tab does not change My Wines as the initial private-journal screen.
2. **Condensed occasion:** each distinct wine release appears once, with its bottle cover beside its identity and current rating. Multiple drinking entries for that release remain available within that card. The cover preference is the user's bottle image, then a catalog image, then a placeholder. The prototype does not fetch Google or other catalog artwork.
3. **Wine photo highlights:** wine records now include “Moments with this wine” below the record, using the scrapbook styling. The initial gallery shows three photos; View all appears when there are more. Captions, dates, and source links lead back to the occasion or wine entry.

## Memory behavior

The occasion now has one “Little moments” album combining its own memories and the media of linked wine entries. The separate “From your wine entries” section was removed. Media attached to an entry retains its ownership and an Open wine entry link; combining the display does not copy it into the occasion's stored album.

Wine highlights use photos from that release's own entries and general albums of linked occasions. They do not include private entry-specific photos belonging only to another release at the same occasion. General occasion photos may naturally show the whole dinner. Bottle covers are identity artwork and are not automatically added to either memory collection.

Repeated links to the same occasion do not repeat its photos. Identical selected images are shown once, and repeat uploads to the same owner are ignored. Prototype identity matching uses exact local image content or known media/source identity; it is not perceptual duplicate detection. Newest source dates come first. Videos remain in the occasion album and entry editor; this initial highlights strip is for photos.

The highlights section is omitted when there are no photos, when signed out, and while identifying a wine inside an unfinished occasion capture flow. The latter keeps the user focused on adding a wine without introducing another route out of the parent draft.

## Verification

Headless Edge checks passed for both navigation orders; wine cover precedence; a single card for repeated wines within one occasion; unified media; duplicate suppression and removal; photo-gallery expansion and source navigation; isolation between releases; guest privacy; and desktop/mobile fit. The previous connected-flow checks also passed. The inline sandbox was checked for gallery-to-occasion navigation and bottle covers alongside its existing save/rating flows.

Desktop and phone screenshots were inspected. Photos in the initial sample journal remain labeled placeholders; local uploads render real previews. No catalog connection, persistent storage, or public-media behavior was added.
