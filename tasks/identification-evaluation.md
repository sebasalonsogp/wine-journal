# Wine identity evaluation checkpoint

October 19, 2026. **R01a is complete: a source-backed identity baseline. R01 remains open.** The [manifest](../assets/evaluation/manifest.csv) contains 30 reference identities across 16 named offerings from five producers. It contains no physical-bottle observations, barcodes or recognition images. No barcode/OCR provider has been evaluated and no public catalog has been imported.

## Scope and evidence

The baseline deliberately stresses identity distinctions: 13 pairs of different vintages, two editions of one multi-vintage offering, and two age-designated non-vintage offerings. These are reference identities, not 30 acquired bottles or independently distinguishable bottling lots. The sample is weighted toward California wines and producers with accessible archives; it is **not representative of retail coverage**. Initial retail market remains undecided. Every market is `UNVERIFIED`; an English-language page, producer address or export listing is not proof of stock in a particular country.

All sources are producer pages reviewed on the recorded date. Store factual identifiers, source URLs and retrieval dates; do not copy marketing descriptions into the fixture. The source review supports these names/vintages/editions, not recognition success, prices, availability, bottle sizes or artwork matches.

| Fixtures | Producer evidence | Identity distinction |
| --- | --- | --- |
| W001–W014 | [Ridge export archive](https://www.ridgewine.com/trade/export-releases/) | Seven offerings with 2022/2023 vintages. The archive's release-calendar headings differ from the vintages in its linked wine names. Use the latter. |
| W015–W020 | Individual J. Lohr vintage pages linked in the CSV; e.g. [2023 Seven Oaks](https://www.jlohr.com/wines/2023-seven-oaks-cabernet-sauvignon) | Seven Oaks, Riverstone and Los Osos each retain two vintages. Preserve the Estates range in the name. |
| W021–W026 | Individual Catena vintage pages; e.g. [Catena Malbec 2022](https://catenazapata.com/catena-malbec-2022/) and [Catena Alta Malbec 2022](https://catenazapata.com/catena-alta-malbec-2022/) | Malbec, Alta Malbec and Appellation Paraje Altamira Malbec are separate offerings, even with the same producer/grape/year. |
| W027–W028 | [Krug 171ème](https://www.krug.com/en-int/champagne/krug-grande-cuvee-171eme-edition), [172ème](https://www.krug.com/en-int/champagne/krug-grande-cuvee-172eme-edition) | Distinct editions; both blend multiple harvest years. The youngest/base harvest is not a single vintage for the wine. |
| W029–W030 | [Graham's 10 Years Old](https://www.grahams-port.com/wine/10-years-old/10), [20 Years Old](https://www.grahams-port.com/wine/20-years-old/11) | Distinct age-designated tawny offerings, described using average ageing. Normalize as NON_VINTAGE with no year; 10/20 are age statements, not vintage or edition numbers. This does not identify a bottling lot. |

An observed metadata conflict reinforces field-level provenance: the [English Catena Malbec 2023 page](https://catenazapata.com/catena-malbec-2023/) reports 13.5% alcohol, while the [Spanish page](https://catenazapata.com/es/catena-malbec-2023-es/) reports 13.7%. Identity agrees; ABV is deliberately absent. Do not average conflicting values or infer a different release without evidence. Calculated Risk, the original product example, is not included until its specific offering/year has a verified source.

## Manifest contract

- UTF-8 CSV. `fixture_id` is a stable evaluation reference; `definition_key` groups explicitly reviewed offerings. Neither is a barcode, provider ID or production database ID.
- Identity is `(definition_key, vintage_status, year, edition)`. Names alone never establish equality. Do not reuse a key for a different offering when correcting display text.
- `YEAR` requires a four-digit year. `NON_VINTAGE` and `MULTI_VINTAGE` have empty years; the two Krug records require distinct editions. Empty cells mean absent information, not zero or a wildcard that merges releases.
- `UNKNOWN` means the observed bottle's vintage is unresolved. It is not synonymous with non-vintage and is intentionally absent from this known-answer table. Missing-year inputs belong in the cases below, without creating fabricated public releases.
- `source_url` supports the recorded identity; `retrieved_on` records this review. Sources can change, so re-review before enriching or changing identity. `evidence_status=SOURCE_ONLY` explicitly excludes physical bottle/image verification.
- `market=UNVERIFIED` means no package/sales-market verification. It does not indicate worldwide availability. No price, barcode, image or purchase endpoint is implied by a row.

## Ambiguity cases to retain

These are **authored text scenarios**, not captured OCR output, provider results or additional bottles. Candidate lists below are relative to this baseline; they are not exhaustive answers for a global catalog. User confirmation is still required before saving.

| Input | Expected behavior |
| --- | --- |
| Ridge Monte Bello 2022 | Offer W001, keeping W002 separate. |
| Ridge Monte Bello; year unreadable | Show related vintage candidates; do not choose the latest. Manual continuation can retain UNKNOWN. |
| Ridge Cabernet Sauvignon 2022 | Incomplete offering name: request confirmation; do not assume Estate or Monte Bello. |
| J. Lohr Estates Seven Oaks 2023 | Offer W016; do not substitute W015 because bottle artwork looks similar. |
| Catena Malbec 2023; range text cropped | W022/W024/W026 must remain distinct possible offerings; seek missing range/designation. |
| Krug Grande Cuvée 172ème Édition; 2016 mentioned | W028, MULTI_VINTAGE; do not save YEAR 2016. |
| Krug Grande Cuvée; edition unreadable | Preserve edition ambiguity between W027/W028 and potentially others; no default edition. |
| Graham's 20 Year Old Tawny | W030, NON_VINTAGE; do not parse 20 as a vintage or conflate with W029. |
| Ridge Monte Bello 2024 | Absent from this baseline; no exact local result. This is not evidence that the wine does not exist. |
| Unreadable label or unrecognized barcode | No confirmed identity; retain entered notes/date and offer search/manual entry. |

## R01b: remaining input collection

Before R02/R03 coverage claims, extend the same evaluation set with independently checked physical-bottle or traceable label/barcode assets. Obtain a bounded collection rather than searching indefinitely for a universal free catalog. Keep these requirements open:

1. Record a sample ID, linked expected fixture(s), observed package market (or explicit unknown), bottle size if known, capture/source date, asset path and SHA-256. A package code may identify several vintages; record candidate sets rather than forcing one release.
2. Preserve printed barcode digits as strings, including leading zeroes, and record symbology where verified. Check a decode against visible digits independently. A valid checksum alone does not prove wine identity. Producer-specific IDs such as [Krug iD](https://www.krug.com/en-us/krug-id) are not automatically UPC/EAN codes.
3. Include clear images and observed glare, skew, blur, partial label/year, barcode missing/unreadable, and a genuine out-of-catalog case. Label deliberately transformed images as synthetic variants of their source; do not present them as real-camera evidence. Separate expected answers from provider outputs.
4. Include unknown-year observations and known non-vintage examples. Do not change ground truth to match a provider. Account for multiple photos of one bottle when reporting denominators.
5. Use bottle-only, non-personal fixtures and remove location metadata before committing. Private journal photos are not evaluation data. Do not commit credentials or signed media URLs.

R02 additionally needs a physical iPhone camera test; R03 needs measured provider/OCR output, latency, limits and recovery. None of these checks has run. No new provider dependency, paid account, image download or runtime configuration was introduced here.

## C01 handoff and verification

The manifest can support **curated text-catalog** implementation independently of camera feasibility. This explicitly splits R01's dependency: C01 consumes R01a; R02/R03 still need R01b. It does not complete C01, R01, or the lookup coverage/market gate. Build a controlled import with separate public identities and provenance; never turn the existing owner-scoped `WineDefinition`/`WineRelease` rows public merely by clearing an owner field. Keep price/artwork/availability unknown until separately sourced. A later catalog import should not overwrite the frozen evaluation answers using provider output.

Next C01 acceptance: validate input before writes; import twice without duplicates; retain source/retrieval metadata; distinguish vintage/edition keys; reject invalid or conflicting rows without a partial batch; prove a journal client cannot publish private wine records. Then C02 can expose guest text search/details without recording a drinking event.

Validation for this baseline: manually reviewed the linked producer evidence; parsed all 30 CSV rows; checked unique fixture and release identities, stable producer/name per definition, year/edition rules, HTTPS source URLs, dates and evidence/market markers. Counts: 16 definitions, 26 YEAR, 2 MULTI_VINTAGE, 2 NON_VINTAGE; zero barcode/image observations. This is a data/documentation change, so application tests were not rerun locally. Parent task counts remain 28/59 complete.
