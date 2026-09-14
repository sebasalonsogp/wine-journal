# Connected design walkthrough, v3

[Open the walkthrough](walkthrough.html). This is a responsive, local UX prototype using the imported Stitch direction and the previously agreed journal flows. No installation or server is needed. The original Stitch export remains unchanged.

## Try these journeys

1. Open **Barrel Selection 2023** from My Wines, choose **Log this wine**, and save with just the date. Open the new entry and add notes later: it remains one entry.
2. Log again, open **Add details**, choose **Create new occasion**, and save both. Add another wine directly from the resulting occasion scrapbook.
3. Start with **Occasions → New occasion** and add multiple wines, including one entered manually with a bottle cover. The new wines are staged until Save occasion.
4. Change **My rating** from the wine record. Past scores stay in Rating history; the number of drinking entries stays the same.
5. Add a local photo to an entry or occasion. Entry memories, occasion memories, and the personal bottle cover remain separate. Remove or replace them through their own controls.
6. Sign out through Account, look up a wine, and choose to save it. The simulated sign-in returns to the same draft. Use a dummy email address; nothing is sent.

## Design decisions in this version

- Burgundy actions, olive selection states, cream backgrounds, warm-white panels, and serif wine titles follow the Stitch direction.
- Navigation order is **Browse Wines / My Wines / Occasions / Guides** on desktop and mobile. My Wines remains the initial private-journal screen.
- Quick notes are visible immediately. Time, place, occasion, and memories remain optional details.
- Mobile wine cards show complete release names and vintages. Navigation appears at the bottom of the document on small screens; a persistent mobile app bar remains a later interaction decision.
- Ratings belong to the distinct wine release. Their history records rating changes independently of drinking occasions.
- Reference screenshots, unexplained catalog scores, and invented detailed wine specifications are excluded from these core screens.
- Each occasion has one card per distinct wine release, with a personal cover first, catalog bottle image second, and a neutral bottle placeholder if neither is available. Catalog lookup remains simulated.
- The scrapbook has one combined memory album. Photos/videos attached to individual wine entries appear there with a link to their source entry; the repeated “From your wine entries” section is removed.
- Wine records show **Moments with this wine**: up to three photo highlights from the wine's own entries and linked occasion albums, with an option to view all. Each photo links back to its source. Repeated occasion links do not duplicate photos. Covers are not automatically journal memories.
- Sample memories remain labeled placeholders; selecting local files shows previews. Highlights are omitted for wines without photos and for guests.

## Boundaries

All changes are held in memory and reset on reload. This is not an account-backed application. Camera recognition, barcode results, sign-in, and place suggestions are simulated. The sample catalog does not establish provider coverage, current prices, or availability. For You and Trending remain future concepts. Guides and basic Browse retain the earlier prototype behavior.

Media previews accept JPEG/PNG/WebP up to 8 MB and MP4/WebM up to 25 MB; these are temporary preview limits, not agreed production requirements. Video playback depends on browser codec support. There is no upload service, transcoding, persistence, or public sharing. Local selected files are read in the browser, not sent to a service.

## Editing and verification

- `refinements.js` and `refinements.css`: the authored changes to the earlier walkthrough.
- `baseline-v2.html`: preserved earlier prototype used by the build helper.
- `build.py`: assembles the inline fragment and portable standalone walkthrough. Its local dependency paths reflect this workstation.
- `fragment.html`: generated inline source; `walkthrough.html`: generated standalone version with locally bundled Lucide icons.
- `check-flows.cjs`, `check-inline.cjs`, `check-memories.cjs`: browser checks. Runtime paths reflect this workstation.
- [Flow results](checks/results.json) and [inline results](checks/inline-results.json); PNGs in `checks/` document the layouts.
- [Initial connected iteration](../../tasks/ux-review-03.md) and [navigation/memory refinements](../../tasks/ux-review-04.md).

The tests exercise actual UI actions and observed outcomes, including quick save, later edits, independent ratings, parent/child draft retention, manual covers, media errors/removal, guest resumption, and viewport fit. They do not constitute a production acceptance suite, complete accessibility audit, or usability study.

Impeccable's written guidance was applied. Its context engine could not initialize its local cache in this environment; no engine audit or hook execution is claimed. See `THIRD-PARTY-NOTICES.txt` for bundled icon attribution.
