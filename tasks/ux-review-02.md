# UX review 02: connected capture, discovery, and learning

Status: revised design walkthrough for discussion, not an approved application design. No application scaffolding, backend, provider configuration, deployment, or purchases. This pass responds to the user's six observations on the first walkthrough. Palette remains burgundy, olive, brown, and cream/white.

## Proposed navigation

My wines / Browse wines / Occasions / Guides, with Log wine always available. My wines remains the default private record; Occasions remains the secondary scrapbook. Browse and Guides are accessible as a guest. Account can eventually house the detailed taste profile; a separate fifth navigation destination is not assumed.

The phone-sized web mock uses a two-row navigation layout. Final mobile navigation and native iOS navigation still require design review.

## Changes and scope

| User observation | Revised behavior | Scope status |
| --- | --- | --- |
| Official places and personal locations | Type any label; Find a place opens suggestions with disambiguating locality. Select a result, replace it, or keep a custom label. | MVP target, Google integration feasibility pending |
| Create an occasion while logging | Inline occasion creation retains the wine entry. Save both together; cancel occasion creation without clearing the entry. | MVP target |
| Browse Wines | Separate catalog, For you, and Trending views. Catalog browsing never records consumption. | Basic browse is an MVP proposal; personalization and public trends remain later |
| Manual wine bottle photo | Select, preview, replace, or remove a cover; retain name/producer/vintage while doing so. | MVP target |
| Add new wines while creating an occasion | Search/scan/photo/manual child flow returns to the unsaved occasion. Add multiple wines, edit/remove staged entries, then save together. | MVP target; draft/commit interaction proposed |
| Wine guides | Dedicated learning section for tasting words, styles/grapes, pairings, and regions; related links into Browse. | Small curated set is an MVP proposal; breadth and personalized learning later |

## Journeys to try

1. **Wine first:** Log wine -> choose a wine -> date -> expand details -> Create new occasion -> title/place -> Save entry & occasion. The scrapbook can then accept another wine. Canceling the inline occasion keeps the original entry fields. Event edits do not overwrite the entry's own date/place.
2. **Occasion first:** New occasion -> title/date/location/notes -> Add a wine -> identify it -> date -> Add to occasion -> Add another, including manual creation -> Save occasion. New entries are staged until final save. Back to occasion cancels the current child flow while preserving the earlier wines and parent fields.
3. **Saved occasion:** Open scrapbook -> Add wine -> identify -> Save entry -> return to that scrapbook. Previously saved wines are unaffected by a failed or canceled addition.
4. **Location:** Try the two sample Bar Sol suggestions and inspect their locality labels; select one, then replace its text with a friend's house. The free label must not retain the previous place association. Repeat on the occasion form.
5. **Manual cover:** Enter wine fields, choose a JPEG/PNG/WebP, inspect its cover, replace/remove if needed, then save an entry. The cover appears on that personal wine. Occasion memories and encounter photos remain separate.
6. **Discovery and learning:** Open Browse -> For you / Trending; explore Guides -> Regions -> Champagne to return to a filtered catalog. Sign out and confirm lookup and guides remain usable, with a personal-history-free For you state.

## Location design and provider implications

Recommendation: an optional user-authored display label plus an optional provider/place identifier. Keep personal labels independent from the external search. Explicit Find a place opens the provider lookup, so an ordinary private label does not need to be sent to a geocoder. Camera or location permission must not be prerequisites for typing a location.

Google's Autocomplete returns place suggestions from typed text, and a selected place can be resolved through Place Details. That fits the proposed search-and-select interaction; a map is unnecessary for the minimum flow. [Google Autocomplete documentation](https://developers.google.com/maps/documentation/places/web-service/place-autocomplete)

The provider boundary needs a later cost/quota, field-selection, attribution, and storage review. Google permits indefinite storage of place IDs; other returned content is subject to its applicable storage rules. Google attribution is required when showing its Places content without a map. Do not assume all fetched venue metadata can be copied permanently into the journal. [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies)

The mock contains invented sample places with sample-prefixed IDs and explicitly labels them as samples. It makes no Google requests and does not use Google branding to imply the sample data came from Google.

## Wine cover versus memory

A bottle cover represents the user's wine record across encounters. It is optional and personal; it must not automatically replace shared catalog artwork or be added to every occasion album. A photograph used for recognition is another distinct input; a later explicit action could reuse it as a cover.

The walkthrough reads a user-selected cover locally for preview. It accepts JPEG/PNG/WebP under 8 MB for this demonstration; that is a preview constraint, not an approved production upload limit. Production needs retained upload status, validation, derived thumbnails, privacy controls, replacement/deletion behavior, and cleanup for abandoned drafts. Those implementation details are deferred.

## Browse, ratings, and profile boundaries

Catalog browsing is useful before recommendations exist. Personal suggestions should explain their connection to current ratings, explicit preferences, and supported wine attributes. Keep low-data uncertainty visible, allow exploration outside the dominant style, and consider dismissing suggestions later. Historical rating revisions are not extra votes.

Trending is a public-community feature: define the time window, qualifying public signals, minimum activity, and ranking before implementation. It should not quietly use private drinking entries. Show current personal rating separately from community aggregate/count. The sample trending tile is explicitly invented and is not attached to a real wine as a claimed public score.

Guides support learning; reading about a grape indicates interest, not necessarily liking it. A future guide can be relevant to a highly rated wine without silently changing the user's taste profile. No collaborative filtering, personalized ranking service, or public-review aggregation is implemented by the mock.

## Guide content direction

Start with a small editorial set and optional in-entry prompts. Articles may link to related catalog filters and producer/educational references. Full regional maps, encyclopedic coverage, lessons, and quizzes are separate scope decisions.

The walkthrough's short tasting/food examples use original paraphrases with links to WSET reading, not a reproduction of its tasting framework or training materials. See [WSET on training the palate](https://www.wsetglobal.com/knowledge-centre/blog/2026/how-to-train-your-palate), [food and wine pairing](https://www.wsetglobal.com/knowledge-centre/blog/2023/july/13/four-rules-to-masterful-food-and-wine-pairing), and [sweetness and pairing](https://www.wsetglobal.com/knowledge-centre/blog/2020/december/21/winter-wine-and-food-matching). Producer/region examples use the earlier [wine identity research](wine-identity.md).

## Prototype limits and verification

All journal edits are local and reset on reload. Barcode/photo recognition and sign-in remain simulated. Only the manual bottle cover reads image content for local display; scrapbook photo/video controls still show filename placeholders, with no upload or playback. Recommendation/trending panels are visibly future concepts. This pass adds an in-app leave-form guard; refresh recovery, durable drafts, upload failures, and full deletion/undo behavior remain future work.

Browser checks passed in headless Edge for: an occasion draft with two newly added wines (sample photo search and manual creation); local cover preview and preservation after saving; child cancellation and retention of parent notes/date/place; inline occasion creation preserving independent entry context; official-place sample selection and replacement with a custom label; in-app leave-form/keep-editing; guest lookup and sign-in resumption saving entry plus occasion; Browse, Guides, related-region filtering, and signed-out discovery state. Main destinations were checked at 320px for horizontal overflow. No application-script runtime errors occurred. Desktop and phone layouts were visually inspected.

The local preview could not load external helper assets because network access is restricted. Labeled controls and core flows were exercised with those optional assets unavailable; the Codex host supplies its own icon/design-control helpers. This is not a completed usability study, accessibility audit, or acceptance suite for the future application.
