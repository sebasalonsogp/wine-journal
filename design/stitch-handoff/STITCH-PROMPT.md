Continue the design of Wine Journal from the attached DESIGN.md and reference screens. This is a private-first wine journal and a portfolio MVP, with room for future expansion. We are refining UX before implementation.

Preserve the warm cream, burgundy, olive, and branch-brown direction. Keep My wines as the primary record-keeping view and Occasions as the secondary scrapbook. Navigation also includes Browse wines and Guides.

Start with these five connected screens: My wines, Wine record, Log wine entry, Create occasion, and Occasion scrapbook. Produce responsive desktop and mobile designs. Improve hierarchy, spacing, navigation, and visual craft while preserving the existing behavior.

The important loops are:
- Wine first: identify -> view details -> log wine and date -> optionally create an occasion inline -> save without losing notes, date, or media -> add another wine from the occasion.
- Occasion first: title/date/place/notes -> add a newly identified or manually created wine -> return to the same occasion draft -> add more wines -> save the occasion and its new entries together.

An entry does not require an occasion. Its date/time/location and notes remain independent of occasion context. Location supports official-place suggestions and free text like Alex's house. Manual wine creation supports an optional personal bottle-cover image. A wine/release has one current personal rating with a history of earlier ratings, independent of drinking occasions.

Guests may browse, identify bottles, read details, and use guides; sign-in is needed to save. Photo recognition and barcode capture need clear no-match/manual fallbacks. Existing fields must survive those transitions.

In a second pass, refine Browse (catalog, future personalized suggestions, future trending/public ratings) and Guides (tasting words, styles, pairings, regions). Clearly distinguish private personal scores from future community aggregates. Keep sample data labeled; do not imply live recommendations, live prices, or Google integration.

Use the screenshot references to preserve the product's identity. They are wireframes: schematic bottle art and memory placeholders may be refined. Do not merge vintages, make occasions compulsory, expose private notes publicly, or add calendar/collaboration/checkout to the core MVP. Keep implementation and backend setup out of this design pass.
