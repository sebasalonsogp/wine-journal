# Wine Journal API contracts

Status: liveness, accounts, manual entry capture, My Wines/detail/history, entry editing/deletion, ratings/history/erasure, occasion creation/editing/deletion, grouped wine capture, entry link/unlink commands, private photo uploads/status/viewing and entry-photo associations are implemented under `/api/v1`. Remaining product routes below are planned. Use the generated OpenAPI snapshot for currently working endpoints. [Architecture](architecture.md) and [data model](data-model.md) define access and ownership.

### Implemented entry photos (M04a)

`GET /entries/{entry_id}/photos` returns `{items: [...]}` for at most 12 active associations, ordered by attachment creation time then asset ID. Each item includes `entryId`, `assetId`, `caption`, `version`, `state`, generic `errorCode` and READY dimensions. This fixed-size collection needs no cursor. It never includes object paths, originals or signed links. Use `POST /media/{asset_id}/view` separately for a READY derivative.

`PUT /entries/{entry_id}/photos/{asset_id}` with `{}` attaches an owned asset in any processing state. The same entry/asset pair replays the current association without overwriting captions. Both IDs must belong to the active account. Database composite foreign keys independently enforce this boundary. Concurrent additions cannot exceed 12 active photos; upload quotas still apply separately. These routes need the database, not an available Storage provider.

`PATCH /entries/{entry_id}/photos/{asset_id}` requires `{version, caption}`. Captions allow 500 characters, reject NUL and normalize blank text to null. A successful edit increments only the attachment revision. An exact retry at the immediately subsequent revision returns that result; other stale writes return 409 `PHOTO_CONFLICT`.

`DELETE /entries/{entry_id}/photos/{asset_id}?version=<positive integer>` removes the association and clears its caption. A repeated removal succeeds with `{assetId}`; stale active revisions return 409. A tombstone prevents delayed PUT retries from resurrecting a removed association (409 `PHOTO_REMOVED`). Missing/foreign parents or assets return 404; disabled accounts return 403. All responses are no-store. Mutations lock account then entry, with a three-second lock timeout using the existing 409 `UPLOAD_BUSY` response.

Entry deletion cascades associations, including tombstones, while preserving assets, other references and reservations for M08 cleanup. No media operation changes the entry's version or replays entry creation. Save text first and attach independently: photo failure must not roll back wine/date/notes. The browser controls and complete phone journey remain M04b.

### Implemented occasions (O01)

`POST /occasions` requires a UUID `Idempotency-Key` and `occasionDate`. Optional fields are `title`, `localTime`, `timezone`, `locationLabel` and `notes`; title/place are limited to 200 characters, notes to 10,000. Blank titles/places normalize to null. Local time and IANA timezone must be supplied or cleared together; time has minute precision and no UTC offset. Untitled occasions display their date. No wine entry is created implicitly.

Creation returns 200 with the context, `id`, `version` and `createdAt`. A transactional receipt replays the original response for the same normalized body/key; changed input returns 409 `SAVE_CONFLICT`. A three-second lock timeout returns 409 `SAVE_BUSY` and `Retry-After: 3`. Receipts persist; occasion deletion now tombstones their private content without releasing the key claim. Future account deletion must also remove private receipt content without allowing resurrection.

`GET /occasions` accepts `limit` (1–100, default 20) and an owner/route-bound cursor (maximum 512 characters). Sort is occasion date descending, ID ascending. It is a live paginated view; edits can move records between pages. `GET /occasions/{id}` reads one owned occasion.

`PUT /occasions/{id}` replaces the editable context, requiring `occasionDate` and the positive integer `version` previously read. Omitted optional fields clear to null. ID/owner/creation timestamp are preserved; successful edits increment the version. Stale edits return 409 `EDIT_CONFLICT`; lock timeouts return 409 `EDIT_BUSY`. Clients keep their draft, read the latest context and require an explicit choice before replacing it. All routes require an active account, use no-store responses, and return 404 for absent/foreign occasions. Occasion deletion is described under O05 and entry association under O04; media remains planned.

### Implemented occasion removal (O05)

`DELETE /occasions/{occasion_id}?version=<positive integer>` requires the occasion version the user reviewed. Success returns 200 `{id}` with no-store headers. Missing/foreign occasions, including repeated deletion, return 404. Changed context returns 409 `DELETE_CONFLICT`; the three-second lock timeout returns 409 `DELETE_BUSY`. The browser requires confirmation, rereads stale context before a new confirmation, and treats 404 on a confirmed retry as already absent.

The transaction locks the owned occasion, detaches its entries and increments their versions, redacts occasion receipts, then deletes only the occasion. Entry IDs, wine identity, consumed context, notes and ratings/revisions survive. Entry capture, batch additions and association commands take a compatible lock on their target occasion, so deletion cannot leave partial links or FK errors when they race. Concurrent occasion context edits remain version-checked.

Creation and addition receipts for the deleted occasion become `{deleted: true}` while retaining their key/hash claims. Replaying their original request returns 409 `OCCASION_REMOVED`. Surviving entry receipts have the removed `occasionId` cleared; replay still returns the original entry without recreating its inline occasion. Receipt versions remain original creation versions, as with ordinary entry edits; read the entry before changing it. Database failure rolls back deletion, detachment and receipt cleanup together. Media does not exist yet; occasion-owned attachment cleanup and its warning must be added and reverified with M06.

### Implemented manual-journal subset (J01–J03)

`POST /entries` requires a UUID `Idempotency-Key` header and `{consumedDate, manualWine}` or `{consumedDate, releaseId}`, exactly one wine selector. Manual wine requires `name`, with optional `producer`, `vintageStatus`, `year`, and `edition`. `YEAR` requires a year; all other vintage states forbid it. Existing releases must belong to the caller. A manual save creates a fresh private identity without matching by name. Repeating a known release reuses its personal wine record.

Successful creation and replay both return 200 with the original entry ID, personal wine ID, consumed date and creation timestamp. Changed input under the same key returns 409 `SAVE_CONFLICT`; a competing transaction that exceeds the three-second lock wait returns 409 `SAVE_BUSY` with `Retry-After: 3`. Retry with the same key. Save intents currently remain for the lifetime of the data (no 24-hour cleanup job); account deletion must include them when implemented.

My Wines and entry history accept `limit` (1–100, default 20) and `cursor`. Cursors are validated for the owner and route, not authorization credentials. My Wines defaults to latest consumed date descending, then ID ascending; empty histories follow dated wines. Additional sort/filter options are described below. Entry history uses consumed date descending then ID ascending. Date-only same-day entries have no inferred time. Lists are live views, not snapshots: concurrent edits may move records between pages. All responses are private/no-store and inaccessible IDs return 404.

Minimal capture still needs only wine/date. It creates no occasion unless explicitly requested, no rating or media, and returns no fabricated rating/cover data.

### Implemented wine-first occasion capture (O02)

`POST /entries` additionally accepts optional `occasionId` or `newOccasion` (the two cannot both be non-null), plus optional plain-text `notes` (10,000 characters maximum, NUL excluded). `newOccasion` uses the same title/date/time/place/notes schema as standalone occasion creation. The drinking date and notes stay independent from occasion context; selecting an occasion never rewrites them.

The entry, private manual wine if needed, optional new occasion and creation receipt commit in one transaction. Invalid nested context, inaccessible existing occasion (404) or database failure leaves no partial records. Existing occasions are read without modification; a same-owner composite FK enforces association ownership independently of route checks. One original entry save key protects the entire operation; there is no second occasion save request or receipt for nested creation. Concurrent retries return the same entry and occasion IDs.

Entry creation/detail/history responses include nullable `occasionId`. For requests without the new optional fields, hashing preserves the pre-O02 normalized payload, so old unconfirmed saves remain replayable. Old receipts without `occasionId` decode as null. Changing occasion selection or notes under an already claimed key returns `SAVE_CONFLICT`. In the browser, nested fields are frozen after an uncertain save; definitive validation/404 failures allow correction. Drafts retain only bounded product fields, and creation requires successful storage of its retry key before sending a request.

Ordinary entry PATCH editing does not change its association. Use the dedicated association commands below.

### Implemented entry association (O04)

`PUT /occasions/{occasion_id}/entries/{entry_id}` requires `{version, previousOccasionId}`. Version is a strict positive integer; `previousOccasionId` is required and may be null. Both must match the owned entry before changing its association. This makes moving from another occasion an explicit command. Repeating the current association at the current version is a no-op; a stale version still conflicts.

`DELETE /occasions/{occasion_id}/entries/{entry_id}?version=<positive integer>` unlinks only if the entry currently belongs to that occasion at the viewed version. Both commands return 200 with the current `EntryResponse` and no-store headers. A change increments the version and alters only the association; consumed context, notes, IDs, wine identity and wine ratings/history remain intact.

Missing/foreign entries or occasions return 404; mismatched versions/associations or competing writes return 409 `LINK_CONFLICT`; the three-second lock timeout returns 409 `LINK_BUSY`. These commands do not use creation receipts. After a conflict or lost response, read `GET /entries/{id}` and require an explicit choice before resubmitting with its current version/association. The browser confirms moves and unlinking. Old-version retries cannot silently overwrite a later decision.

### Implemented occasion-first capture (O03)

`POST /occasions` now accepts optional `wines`, an array of wine groups. Each group specifies exactly one of `manualWine` or an owned `releaseId`, and `entries: [{consumedDate, notes?}]`. A group has 1–20 entries; the entire request is limited to 20 entries across at most 20 groups. Names do not imply shared identity: multiple entries inside one group deliberately reuse its release, while separate manual groups create separate identities. Dates and notes belong to individual entries and do not inherit later occasion edits. Time/place can be added through the existing entry editor after saving.

The occasion, manual identities, personal wine records, entries and receipt commit in one transaction. Nested validation, ownership or database failures create no partial journal records. Creation/replay returns the occasion response. Empty or absent `wines` preserves old standalone creation hashes, allowing pre-O03 saves to replay unchanged.

`POST /occasions/{id}/wines` accepts `{wines: [...]}` with the same bounds and at least one group; it requires a UUID `Idempotency-Key`. It adds new drinking entries without changing occasion context/version. The operation and target ID are included in its receipt hash, so a key cannot silently target another occasion or command. It returns the original occasion snapshot for retries; the browser refetches the wine list. Missing/foreign occasions/releases return 404. Successful responses are no-store; lock waits use the existing `SAVE_BUSY` behavior.

`GET /occasions/{id}/wines` returns a `WinePage` with one card per personal wine/release. Here, `entryCount` and `lastConsumedDate` describe only entries linked to this occasion; current rating remains the user's wine-level rating. Pagination uses `limit` 1–100 (default 20) and a cursor bound to owner and occasion. Ordering is latest linked drinking date descending, then personal wine ID ascending. Other occasions and ungrouped entries never inflate the count. No album or fabricated bottle image is returned.

### Implemented My Wines search (J10)

`GET /me/wines` additionally accepts:

- `q`: at most 200 characters, NUL excluded. Case-insensitive literal matching across name, producer, edition and known year; each whitespace-separated word must match. `%` and `_` are escaped. No fuzzy or accent-insensitive matching is claimed.
- `sort`: `LAST_CONSUMED` (default), `NAME` (case-insensitive A–Z), or `RATING` (current score descending). ID ascending resolves ties; missing dates/unrated scores sort last.
- `rating`: `ALL` (default), `RATED`, or `UNRATED`.
- `vintage`: `ALL` (default), `YEAR`, `NON_VINTAGE`, `MULTI_VINTAGE`, or `UNKNOWN`.

Wine cursors are bounded to 2048 characters and bind the owner, normalized query and all filter/sort choices. Changing the options with an old cursor returns 422 `INVALID_CURSOR`; restart from the first page. The cursor stores the SQL-evaluated sort value so Unicode name comparisons use the same database collation across pages. No owner or private content becomes accessible through a cursor or shared filter URL. Pre-J10 wine cursors are invalidated; entry-history cursors keep their existing format. See [query measurements and browser evidence](../tasks/wine-search-checkpoint.md).

### Implemented wine ratings (J08–J09)

Wine list/detail responses include nullable `currentRating` (1–5) and integer `ratingVersion` (initially 0). `PUT /me/wines/{id}/rating` requires `{score, version}`: score is null or 1–5 in half-point steps, version is the nonnegative integer previously read. Extra fields and string/bool scores are rejected. Success returns `{score, version}`. Matching current score/version is a no-op; stale versions return 409 `RATING_CONFLICT` before comparing the value. Lock waits are capped at three seconds and return 409 `RATING_BUSY`. Clients refetch current state before explicitly choosing to retry; they must not automatically adopt a new version.

`GET /me/wines/{id}/rating-history` accepts `limit` (1–100, default 20) and optional `beforeVersion` (positive integer, exclusive). It returns `{items: [{score, version, changedAt}], nextBeforeVersion}` ordered by version descending. Change timestamps come from the server. Pagination is scoped by the authorized wine, remains stable across new revisions, and is a live view when history is erased.

Clearing uses PUT with `score: null`, creating a dated null revision when previously rated. `DELETE /me/wines/{id}/rating-history?version=<current>` clears score and revisions together and returns `{score: null, version: <incremented>}`. Erasure never resets the version, even when already empty. The browser requires a separate explicit confirmation. Rating mutations do not add, edit or remove drinking entries. Responses are no-store; missing/foreign wines return 404. See the [rating checkpoint](../tasks/rating-checkpoint.md).

### Implemented entry enrichment (J06)

`GET /entries/{id}` returns the owned entry and its version. `PATCH /entries/{id}` requires the integer `version` read by the editor and at least one changed field: `consumedDate`, `localTime`, `timezone`, `locationLabel` or `notes`. Omitted fields stay unchanged; null clears optional fields. Date cannot be null. Time and timezone must be set/cleared together in the resulting record. Local time uses minute precision, with no UTC offset; timezone is an IANA identifier. They record civil context without deriving a unique instant, preserving unknown time and calendar dates while traveling. Labels allow 200 characters; plain-text notes allow 10,000.

Updates preserve the ID and creation timestamp, increment the version, and use an atomic version predicate. A stale write returns 409 `EDIT_CONFLICT`; a bounded lock timeout returns 409 `EDIT_BUSY`. Neither silently overwrites. Read the latest entry, keep the user's draft, and obtain an explicit replacement choice before retrying against its version. A lost success response is recovered through the same comparison flow. Read/write ownership and active-account checks remain mandatory; inaccessible entries return 404. Runtime SQL UPDATE privileges cover editable columns and version only.

The browser stores edit drafts under owner/entry-specific session keys, clears them on sign-out, and invalidates affected read models after success. Explicit clearing and an empty location/note input persist as null. Official venue lookup remains future work.

## Contract conventions

### Implemented entry removal (J07)

`DELETE /entries/{id}?version=1` requires the viewed version as a positive integer query parameter. Success returns 200 `{id}`. Missing/inaccessible entries, including a repeated deletion, return 404; a version race returns 409 `DELETE_CONFLICT` and a bounded lock wait returns 409 `DELETE_BUSY`. The caller must review and reconfirm after a conflict. The browser reconciles a 404 by refreshing history, allowing recovery after a lost success response.

Deletion removes only the owned entry. Wine identity and personal wine record survive, with `entryCount: 0` and `lastConsumedDate: null` after the last encounter is removed. Creation receipts for that entry are reduced to a deletion marker in the same transaction, retaining only the request-key claim/hash to prevent resurrection. Replaying that original create request returns 409 `ENTRY_REMOVED`; no deleted entry details are returned. This deletion transaction will own attachment-cleanup job creation when media is implemented.

### Shared conventions

- REST JSON under `/api/v1`. JSON uses `camelCase`, enums use uppercase values, UUIDs are strings. Python names remain `snake_case` via schema aliases.
- Required ownership comes from a verified bearer access token, never request `ownerId`. Guest endpoints return public catalog data only; private manual identities are accessed through owner-only routes.
- Dates use `YYYY-MM-DD`; optional local time and timezone are separate; server timestamps use ISO 8601 with UTC offset. `null` clears a nullable field; an omitted PATCH field stays unchanged.
- Use consistent errors: `{ "error": { "code": "VERSION_CONFLICT", "message": "This entry changed. Reload it before saving.", "fields": [], "requestId": "..." } }`. Normalize framework validation errors into this envelope. Use 401 for absent/invalid auth, 404 for absent or inaccessible private resources, 409 for conflicts, 422 for invalid input, 429 for limits, and 503 for temporary provider unavailability. Do not return provider secrets or internal SQL errors.
- Lists return `{ "items": [], "nextCursor": null }` with opaque cursors tied to sort/filter; default 20, maximum 100 as proposed initial bounds. Deterministic sort ties use stable IDs. Unknown/unrated records have explicit placement.
- Entry/occasion edits require a version or ETag precondition; stale edits fail visibly. Return the new version. Permit additive contract changes and document breaking changes before a native client ships.

## Initial surface

| Intent | Proposed route | Access / behavior |
| --- | --- | --- |
| Browse/search catalog | `GET /wine-releases?q=&sort=&cursor=` | Guest; approved sourced records only |
| Read wine specs | `GET /wine-releases/{id}` | Guest; source/freshness, unknown fields and permissible outbound links |
| Identify barcode/photo | `POST /identifications` | Guest with rate/spend limits; bounded JSON barcode input or bounded multipart photo, discriminated by content type |
| Bootstrap own profile | `POST /me` | Implemented; auth; body `{}` only; atomically create/reuse identity, return `id`, `state`, `createdAt`; always 200 on success |
| Read own profile | `GET /me` | Implemented; auth; read only, 404 if no application account, 403 if disabled |
| My Wines | `GET /me/wines?sort=LAST_CONSUMED&cursor=` | Auth; latest consumed date, counts, current rating and cover |
| Personal wine detail | `GET /me/wines/{id}` | Auth; personal record plus bounded entry/gallery previews and source links |
| Save entry | `POST /entries` | Auth; catalog/personal selection or inline manual wine; optional existing/new occasion |
| Read/edit/delete entry | `GET`, `PATCH`, `DELETE /entries/{id}` | Auth; version checks on mutations |
| Entry history | `GET /me/wines/{id}/entries` | Auth; paginated by consumed date with stable ties |
| Change/read ratings | `PUT /me/wines/{id}/rating`, `GET /me/wines/{id}/rating-history` | Auth; expected rating version, current value/history |
| Delete rating history | `DELETE /me/wines/{id}/rating-history` | Auth; explicit erase action; clear score/history atomically |
| Browse/create occasions | `GET`, `POST /occasions` | Implemented context and staged new entries |
| List/add wines on an occasion | `GET`, `POST /occasions/{id}/wines` | Implemented grouped wine list and bounded transactional additions |
| Read/edit/delete occasion | `GET`, `PUT`, `DELETE /occasions/{id}` | Implemented; version-checked edits/deletion; deletion preserves drinking entries; albums planned |
| Link/unlink existing entry | `PUT`, `DELETE /occasions/{id}/entries/{entryId}` | Implemented; auth; version and prior-association checks; preserve consumed context |
| Full memory galleries | `GET /me/wines/{id}/moments`, `GET /occasions/{id}/media` | Auth; paginated eligible assets, captions, source date and source link |
| Upload initiation/completion | `POST /media/uploads`, `POST /media/{id}/complete` | Auth; per-account quota reservation, unique object key, owned staged asset |
| Asset status / viewing | `GET /media/{id}`, `POST /media/{id}/view` | Implemented; viewing only for ready, authorized derivatives |
| Entry photos | `GET /entries/{id}/photos`; `PUT`, `PATCH`, `DELETE /entries/{id}/photos/{assetId}` | Implemented owned links, independent revisions, captions and removal; fixed 12-photo collection |
| Occasion media | Parent-specific `/occasions/{id}/media` routes | Planned; typed links; deletion removes association, then conditional cleanup |
| Set/remove bottle cover | `PUT`, `DELETE /me/wines/{id}/cover` | Auth; owned image asset; separate from gallery membership |
| Correct private identity | `PATCH /me/wines/{id}/identity` | Auth; owner-only provisional data; shared catalog cannot be rewritten |
| Correct entry's wine | `PUT /entries/{id}/wine` | Auth; explicit target; preserve entry context/media, leave original wine rating alone |
| Official-place search | `GET /places/suggestions`, `GET /places/{providerId}` | Auth for MVP journal forms; bounded queries/session tokens and provider attribution |
| Private taste summary | `GET /me/taste-profile` | Auth; current scores and sample counts, no unsupported inference |
| Export/delete account | `POST /me/exports`, `DELETE /me` | Auth; durable jobs and explicit destructive-action UX before real-user launch |

Guides are initially build-time editorial content, so they need no API/CMS. Public reviews, feed, participants, and recommendation endpoints are intentionally unspecified until their product phase.

Account bootstrap is safe to retry because `(auth_issuer, auth_subject)` is unique and creation uses `INSERT ... ON CONFLICT DO NOTHING` inside a transaction. It does not use a caller-supplied owner or general idempotency-key table. Neither bootstrap nor GET reactivates a disabled account. Successful account responses and errors are `Cache-Control: no-store`; errors contain a generated `requestId` also returned as `X-Request-ID`. Missing/invalid tokens return 401; missing/unavailable identity infrastructure returns 503. Error payloads exclude raw validation input and internal SQL/provider details.

## Wine-first capture example (implemented)

```json
{
  "manualWine": { "name": "Dinner wine", "vintageStatus": "UNKNOWN" },
  "consumedDate": "2026-09-14",
  "notes": "",
  "newOccasion": {
    "title": "Dinner with friends",
    "occasionDate": "2026-09-14",
    "locationLabel": "Alex's house"
  }
}
```

The wine/date alone is valid; omit `newOccasion` for a standalone glass. Select an owned existing release with `releaseId` instead of `manualWine`, and an existing occasion with `occasionId` instead of `newOccasion`. Schemas reject conflicting selectors.

On submit, create/reuse the user-wine record, create any inline manual identity and new occasion, save the entry and record the idempotency result in one SQL transaction. Return 200 with entry and user-wine IDs and entry version. If validation fails, no partial journal records remain. Upload bytes, processing and photo associations are separate requests; text save does not wait for a worker or an attachment. Rating changes use their separate versioned command.

## Occasion-first capture

`POST /occasions` accepts occasion fields, bounded `newEntries`, and `existingEntryIds` (proposed maximum 30 combined entries per request). Each new entry has its own consumed date and optional place; the UI may prefill them from the occasion. Inline manual identity is allowed inside each new entry.

Validate all referenced identities, assets and existing entries before committing. Reuse a personal wine by the `(owner, release)` unique key while still allowing several intentional drinking entries for it. Insert the occasion and new entries and link selected existing entries atomically. Reject entries already linked elsewhere with a clear conflict. Do not copy occasion date/location over existing entry fields. Cancelling the client draft abandons staged media but does not create an occasion.

To add a new wine to a saved occasion, use `POST /entries` with the existing occasion selector and return to its scrapbook. Shared capture form code supplies both directions; the API owns the transaction semantics.

## Identification contract

Return a result status such as `MATCH`, `NEEDS_CONFIRMATION`, or `NO_MATCH`, candidates, unresolved identity fields, permitted source metadata, and an expiring opaque selection token for provider candidates not yet saved locally. The token is server-issued and validated; the client cannot submit arbitrary provider fields to create public catalog data.

`MATCH` can open catalog details directly when the identity is sufficiently resolved; it never logs consumption. A clear named offering with an unresolved vintage requires confirmation or an owner-only unknown-vintage record on save. Candidate confidence is provider-specific; do not invent a universally meaningful percentage.

Recognize uploaded label images within a proposed 15-second overall request deadline; exact input size and service timeout are finalized in the feasibility spike. Enforce ingress limits before reading the whole upload and delete temporary images after the request. Do not retain label images in the journal without a separate user action. Paid providers receive only necessary image/text data; their retention terms must be checked. A timeout, denied camera, or no match leaves text/manual input intact.

## Retry, concurrency, and failure handling

Creation commands use an `Idempotency-Key` generated once per deliberate user submit and retained through network retries. Store a request hash and response metadata under unique `(owner_id, operation, key)`. Claim and write the result in the same database transaction as the business change. Concurrent claims serialize on that key; replay returns the original result, payload mismatch returns 409, and a wait timeout returns a retryable conflict with `Retry-After`. Propose 24-hour retention; deduplication is guaranteed only inside that window. A new intentional glass gets a new key even on the same date.

Do not retry validation/auth failures or blindly retry paid recognition POSTs. For recognition, permit explicit retry under the spend limiter, or add a bounded request-key cache once provider billing semantics are known. HTTP clients have explicit timeouts; only transient, safe requests get bounded retry/backoff.

Mutations invalidate affected My Wines, detail, occasion, rating-history and gallery query keys. Draft input stays intact on a failed save. Upload/processing status is independent, so an entry can be saved successfully while an attachment shows Retry. A missing or failed cover falls back without hiding wine identity.

Before calling this contract complete, implement tests for nested save rollback, concurrent retry, stale rating edit, cross-account nested IDs, ambiguous vintage, missing/late uploads, and deletion preserving unrelated memories. Contract snapshots and generated client drift are checked in CI; screen-specific components must not invent parallel transport models.
