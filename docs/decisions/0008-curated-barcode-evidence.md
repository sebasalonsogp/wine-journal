# ADR 0008: Curated barcode evidence belongs to offerings

Status: accepted for the import foundation (C04a), October 20, 2026.

The [coverage checkpoint](../../tasks/barcode-coverage-checkpoint.md) found one
unverified product and three misses across four package codes. Codes can span
vintages, and a readable code does not prove a release. Use reviewed catalog
associations as the initial lookup source; do not publish external product results.

Store one evidence row per normalized retail GTIN, catalog definition, source URL
and retrieval date. Keep bottle size, evidence kind, unverified market and the
original image hash where applicable. Multiple sources/offerings for a code are
allowed: future lookup must retain ambiguity, not overwrite a previous mapping.
The association deliberately has no release/year column. A source image showing
2023 supports the offering association but does not prove barcode exclusivity to
2023. A candidate's vintage still needs confirmation, even if only one catalog
release is available.

A separate bounded JSON import uses existing migration credentials, defaults to
preview and commits atomically only with `--apply`. It requires existing public
definitions with matching producer/name, validates the whole batch, normalizes
leading zeroes and is repeatable. The same evidence key with conflicting size or
hash fails for curator review; imports never overwrite, delete, fetch sources,
create offerings, or touch private wine data. Separate sources may disagree and
remain separate evidence. Corrections/retraction require a future explicit curator
workflow before exposing this data in a production lookup endpoint.

API runtime receives SELECT only; provider-managed roles receive no new access.
The additive migration refuses downgrade once evidence exists. There is no new
environment variable, provider key, external request, endpoint or camera UI.

Scope split: C04a can prepare reviewed storage independently of the unfinished
physical-device gate. C04b still needs bounded guest/user lookup, response contracts,
source revalidation and server-side release selection. C05 requires actual camera
evidence. R01/R02/C04/C05 remain incomplete; this decision does not waive those gates.

October 20 follow-up: C04b now exposes curated lookup and explicit release
confirmation through the [identification contract](../../apps/api/src/wine_journal/identification/README.md).
It revalidates current evidence, preserves ambiguity, bounds requests/results and
never calls a provider or saves an entry. A preview-first exact-match `--retract`
operator workflow now fulfills the correction/retraction prerequisite above.
No schema, credentials or permissions change is required. Shared production
ingress quotas and camera/coverage validation remain deployment/product gates.
