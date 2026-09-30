# Wine Journal data model

Status: proposed logical model, September 14, 2026. This is not migration SQL. Exact fields are added with their feature slices. Identity examples and terminology follow [wine identity research](../tasks/wine-identity.md); architecture and access policy are in [architecture.md](architecture.md).

Implementation checkpoint, September 29: migrations 0002–0007 add private wine definitions/releases, personal wine records, entries with optional time/timezone/place/notes, versioned entry edits/deletion, transactional save intents, current ratings with revisions, and independently saved occasions. Occasions require a date and allow title, civil time/timezone, custom place and general notes; their owner/ID unique key prepares for future same-owner entry links. `occasion_saves` stores transactional creation receipts separately from entry receipts. Occasion edits use a version predicate; runtime grants allow only editable columns and no occasion deletion yet.

Migration 0008 adds nullable `drinking_entries.occasion_id`, an `(owner_id, occasion_id)` index and composite FK to the occasion owner/ID. Entry capture can select an owned occasion or create its context inside the same entry transaction. Separate entry and occasion dates/notes are retained. Ordinary entry edits cannot change this link; future explicit link/unlink commands need a deliberate grant/API extension.

All implemented wine identities require an owner; shared catalog ownership remains a future migration with explicit visibility rules. Optional catalog facts and media below remain proposed. Entry save intents commit with creation; deletion replaces the original receipt with a tombstone. A nested occasion is protected by its entry receipt, not a second occasion receipt. Future occasion deletion must redact both standalone and nested receipts as needed while preserving entry retry semantics. Runtime updates are restricted to editable columns; rating revisions can be inserted/read/deleted, never edited in place.

Rollback: migration downgrades remove feature columns/tables and destroy their data. They are verified only against disposable test databases. For a populated journal, roll back application code while retaining the additive schema; do not downgrade the database to undo a deployment. Earlier application code remains compatible with the additive schema. Local Docker/Supabase is running and has been upgraded without resetting existing journal data.

## Core relationships

```mermaid
erDiagram
    WINE_DEFINITION ||--|{ WINE_RELEASE : distinguishes
    WINE_RELEASE ||--o{ USER_WINE : recorded_as
    APP_USER ||--o{ USER_WINE : owns
    USER_WINE ||--o{ DRINKING_ENTRY : encountered
    USER_WINE ||--o{ RATING_REVISION : rated
    APP_USER ||--o{ OCCASION : owns
    OCCASION o|--o{ DRINKING_ENTRY : optionally_groups
    APP_USER ||--o{ MEDIA_ASSET : owns
    DRINKING_ENTRY ||--o{ ENTRY_MEDIA : attaches
    MEDIA_ASSET ||--o{ ENTRY_MEDIA : referenced_by
    OCCASION ||--o{ OCCASION_MEDIA : attaches
    MEDIA_ASSET ||--o{ OCCASION_MEDIA : referenced_by
    USER_WINE ||--o| WINE_COVER : has
    MEDIA_ASSET ||--o{ WINE_COVER : illustrates
```

A wine definition is a named offering, such as a producer's specific Cabernet selection. Its releases distinguish vintage, edition, or non-vintage batch where known. A **user wine** is one person's record of one release. A physical bottle or glass is not an inventory entity in this MVP.

## Principal records

| Record | Important fields and rules |
| --- | --- |
| `app_users` | UUID; unique `(auth_issuer, auth_subject)`; account state; display preferences. No passwords. Journal ownership uses this app ID. |
| `wine_definitions` | UUID; recognizable name; producer, country/region and style where known; controlled grape codes as an array initially; nullable `owner_id`. Null owner means approved shared catalog; otherwise owner-only provisional identity. |
| `wine_releases` | Definition FK; `vintage_status` (`YEAR`, `NON_VINTAGE`, `MULTI_VINTAGE`, `UNKNOWN`); year only for `YEAR`; optional edition/batch; sourced ABV and descriptive facts where available. Inherits definition visibility. |
| `user_wines` | Owner FK; release FK; unique `(owner_id, release_id)`; optional personal summary note; nullable current rating in integer half-star units; rating version; created/updated timestamps. Created on deliberate save, never on lookup. |
| `drinking_entries` | Owner; user-wine FK; required `consumed_date`; optional local time and IANA timezone; optional place fields; free text and optional guided descriptors; nullable occasion FK; revision/version. Same-date repeats are valid. |
| `occasions` | Owner; optional title; required occasion date as the proposed minimum for an explicitly saved occasion; optional time/timezone/place; general notes; version. Display a date-based fallback when untitled. |
| `rating_revisions` | Owner; user-wine FK; unique `(user_wine_id, version)`; nullable score; server change timestamp. Nullable score records clearing the current rating. Not a drinking entry. |
| `media_assets` | Owner; random storage keys; kind; detected MIME; byte size; dimensions/duration; processing state; derivative keys; timestamps. Store no expiring signed URL as permanent data. |
| `entry_media`, `occasion_media` | Typed foreign keys to parent and asset, owner, caption and ordering. Each parent/asset pair is unique. They identify context, not a copy of the stored object. |
| `wine_covers` | One row per user wine; asset FK; owner. It does not make the asset an album memory. |

The implemented default score is 1–5 in half steps, stored as integers 2–10. This follows the prototype and the stated implementation assumption; the optional scale question did not receive a new preference. The API exchanges the displayed numeric score, not storage units. `null` means unrated, never zero. Free-text wine summary notes remain proposed; encounter observations live on entries.

Provisional wine identity requires only a recognizable user-entered name; producer, year, region, and other facts can be unknown. Manual creation makes an owner-only definition/release, even when a similar shared offering exists. This small amount of duplication avoids silently inserting incomplete claims into public catalog data. An unknown-vintage record is not the same as a verified non-vintage release.

## Identity, corrections, and sources

Use UUIDs for identity, not a name, barcode, or `(name, year)` key. Catalog source mappings can identify a definition or a release; one code can map to several candidates. Store normalized GTIN plus its provenance in a barcode mapping table with explicit definition/release targets and a constraint requiring exactly one target. Do not impose one globally unique release per barcode. Validate checksums/format separately from catalog matching.

Source references record provider, external ID, retrieval time, attribution, and the intended definition/release. Persist only permitted normalized fields; retain raw payloads only when licensed and operationally necessary, with expiry. If fields have different sources, preserve their provenance. Offers need amount, currency, source, market and observed time; unknown price/availability stays unknown. Personal label uploads are never silently republished as catalog artwork.

Correction cases must be separate commands:

1. **Edit private provisional facts:** validate ownership; affect only that owner's identity. Show when this identity has multiple entries.
2. **Move one misidentified entry:** select/create its correct user-wine target; preserve entry ID, consumed context, notes, attachments and occasion. Its old wine rating stays with the old user-wine record.
3. **Resolve an entire provisional record:** if no destination user-wine exists, retarget the personal record after explicit confirmation. If the owner already has the destination, preview a merge. Preserve entries and media; keep the source rating history available and require a choice of current rating. Do not combine histories into an invented chronological opinion or overwrite either current rating silently.

The full merge tool can follow initial correction support. Until then, offer entry-by-entry correction and keep a conflicting source record accessible. No auto-merge on a matching label/name and no public-catalog editing endpoint for ordinary users.

## Database invariants and query design

- Use foreign keys, required fields, check constraints, and explicit uniqueness. Validate release visibility when creating a personal record. Restrict delete of a release referenced by a journal.
- Duplicate owner IDs on child rows support authorization and **composite foreign keys** such as `(owner_id, user_wine_id)` and `(owner_id, occasion_id)`. Add the corresponding parent unique keys so mismatched-owner references fail in the database. Apply the same pattern to media attachments.
- Services also enforce owner scoping and catalog visibility. Database structural checks are not a substitute for access authorization.
- `created_at`/`updated_at`/rating-change timestamps use UTC-aware database timestamps. A consumed date is a calendar date, independent of when the record was saved. Unknown time remains null; a local date must not shift because a viewer travels to another timezone.
- Derive My Wines ordering from that owner's latest consumed date per user wine. Stable ties use IDs; same-day entries with unknown times must not imply exact chronological order. An old memory added today must not move a wine to the top on creation date alone. Records with no remaining entries can retain a rating; show them after consumed records with an explicit empty history.
- Begin with indexes on entries `(owner_id, user_wine_id, consumed_date DESC, id)`, entries `(owner_id, occasion_id)`, entries `(owner_id, consumed_date DESC, id)`, occasions `(owner_id, occasion_date DESC, id)`, and revisions `(user_wine_id, version DESC)`. Index attachment parent/asset FKs and catalog search fields as queries require. Verify plans before adding redundant indexes.
- Use indexed catalog/name search initially; add Postgres fuzzy/full-text search after measuring matching quality. Listing endpoints paginate. Fetch related counts/covers in bounded queries, not one query per card.

### Rating transaction

Lock the owner-scoped user-wine row with a three-second lock timeout, check the expected rating version, append the new revision, and update current score/version in the same transaction. Identical score submissions with the current version are a no-op. A stale version returns 409 even if its score matches; the browser reloads current state for review. The current score is the user's most recent choice; a revision does not create an additional public vote or drinking event.

Implemented removal behavior: clearing the current rating appends a null revision and preserves history. Clearing an already-unrated wine is a no-op. A separate confirmed “Delete rating history” operation removes all revisions and clears current score atomically. Erasure increments the version even when history is already empty; the counter never resets, so old tabs cannot reuse a pre-erasure version. A lost success response is reconciled by reading the latest state, never by silently overwriting it. Full account deletion will remove both when that feature lands.

## How the two scrapbook views work

**Occasion:** group linked entries by release/user-wine and display one wine card per release. Keep all repeated entries available inside the card. Cover priority is personal cover → permitted catalog image → placeholder. “Little moments” combines directly attached occasion media and media on its linked entries. Deduplicate by asset ID; an entry attachment keeps its entry source link.

**Wine detail:** “Moments with this wine” combines ready photos on that user wine's entries and ready general photos from occasions linked by those entries. Exclude entry-specific images attached only to another wine at the same occasion. Deduplicate asset IDs and repeated occasion joins. Use source entry/occasion dates for sorting with a stable tie-break; if one asset has multiple eligible sources, choose the latest eligible source consistently. Return source metadata so the user can open the original context.

Initial highlights show three photos and a View all route when needed; the server can return a bounded preview and total count without sending the whole gallery. Hide the section when no eligible photos exist. Videos remain in entry/occasion albums initially. Guest catalog requests never return these private read models. Bottle covers do not enter gallery queries.

Media bytes live once in storage. Optional exact-content deduplication may operate **within an account**; different users must never learn another person's uploads through a shared hash lookup. Hash deduplication is not required for the first media slice; reference-level deduplication is.

## Drafts, transactions, and media lifecycle

Wine-first capture commits the entry, an optional new occasion, and any inline manual identity in one transaction. Occasion-first capture commits the occasion, bounded staged new entries/manual identities, and explicitly selected existing-entry links atomically. Existing entries are not rewritten with occasion defaults. An entry already linked elsewhere requires explicit re-linking, not silent reassignment.

Media can be staged before these saves without creating an entry/occasion. Attachment rows may refer to an owned pending asset; UI shows its processing state. Finalized journal data is valid even if its upload fails. Proposed asset states: `PENDING_UPLOAD`, `PROCESSING`, `READY`, `FAILED`, `DELETING`. Upload completion is idempotent and verifies the expected object; queueing occurs with the state transition transaction.

A small `jobs` table added with media holds kind, asset/reference ID, state, run-after time, lease expiry, attempt count, last safe error, and a unique operation key. Claim work in a short transaction; release the database lock before decoding/uploading. Reclaim expired leases, bound retries, and make output keys deterministic or safely replaceable by the worker. Cleanup rechecks references and pending upload capability expiry before deleting objects.

Application database commits and object uploads cannot be atomic together. Do not simulate rollback by losing the entry when storage fails. Reconcile abandoned objects and failed deletions with retryable cleanup.

## Removal and later sharing

| Action | Proposed behavior |
| --- | --- |
| Unlink entry from occasion | Set association to null; preserve entry context, notes, and entry media |
| Delete occasion | In a transaction, unlink entries and remove occasion-specific notes/attachments; keep entries and their media. Warn that its general album will be removed. Delete only assets with no remaining attachment/cover after the upload grace period. |
| Delete entry | Remove that entry and its attachments; keep occasion and personal wine/rating. Clean up unreferenced assets. |
| Replace/remove cover | Change cover reference; cleanup only if the old asset is otherwise unreferenced |
| Delete account | Disable app access immediately; queue removal of private rows/assets and auth identity with retries; record minimal job state until completion. Describe backup expiry and supply a practical export first. |

Later public reviews are separate deliberately published text/rating records with moderation state. Their queries never join private attachments for output. A private edit does not update a published copy.

Later shared occasions add memberships and contribution/sharing permissions through migrations. The present same-owner entry/occasion constraint will need deliberate evolution; sharing an occasion must not reveal all linked personal entries or media. Sharing requires explicit selection/copy or authorized contributions. Personal ratings continue to belong to individuals.

## Cases the implementation must prove

| Scenario | Expected result |
| --- | --- |
| One glass at home | One entry, no generated occasion; wine/date sufficient |
| Dinner with three wines, one repeated | One occasion; four entries; three wine cards |
| Same wine in 2021 and 2022 vintages | Distinct user-wine ratings/history and entries |
| Barcode known, year missing | Candidate definition with unresolved vintage; no fabricated release |
| Rating 4 → 4.5 without a new drink | Two rating revisions; unchanged entry count |
| Two entries from one wine link the same occasion | General album photos appear once in wine highlights |
| Another wine has an entry-specific photo | Excluded from this wine's highlights; included in the occasion album |
| Backdate an entry or unlink an occasion | Correct consumed-date ordering; memories keep their source ownership |
| Retry save or restart during media processing | One database save; media work resumes safely |
| Second account submits known IDs | Cannot read/change records, attach media, or obtain signed links |
