# Wine Journal API contracts

Status: liveness, `POST /api/v1/me` and `GET /api/v1/me` are implemented; other product routes below remain planned. The [phased implementation plan](../tasks/plan.md) sequences their delivery. Use the generated OpenAPI snapshot for currently working endpoints. [Architecture](architecture.md) and [data model](data-model.md) define access and ownership.

## Contract conventions

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
| Browse/create occasions | `GET`, `POST /occasions` | Auth; create can include staged new entries and selected existing entries |
| Read/edit/delete occasion | `GET`, `PATCH`, `DELETE /occasions/{id}` | Auth; occasion read groups wine cards and provides bounded album previews |
| Link/unlink existing entry | `PUT`, `DELETE /occasions/{id}/entries/{entryId}` | Auth; preserve consumed context; reject conflicting association unless deliberately re-linked |
| Full memory galleries | `GET /me/wines/{id}/moments`, `GET /occasions/{id}/media` | Auth; paginated eligible assets, captions, source date and source link |
| Upload initiation/completion | `POST /media/uploads`, `POST /media/{id}/complete` | Auth; per-account quota reservation, unique object key, owned staged asset |
| Asset status / viewing | `GET /media/{id}`, `POST /media/{id}/download-url` | Auth; viewing only for ready, authorized assets |
| Attach/remove media | Parent-specific `/entries/{id}/media` and `/occasions/{id}/media` routes | Auth; typed links; deletion removes association, then conditional cleanup |
| Set/remove bottle cover | `PUT`, `DELETE /me/wines/{id}/cover` | Auth; owned image asset; separate from gallery membership |
| Correct private identity | `PATCH /me/wines/{id}/identity` | Auth; owner-only provisional data; shared catalog cannot be rewritten |
| Correct entry's wine | `PUT /entries/{id}/wine` | Auth; explicit target; preserve entry context/media, leave original wine rating alone |
| Official-place search | `GET /places/suggestions`, `GET /places/{providerId}` | Auth for MVP journal forms; bounded queries/session tokens and provider attribution |
| Private taste summary | `GET /me/taste-profile` | Auth; current scores and sample counts, no unsupported inference |
| Export/delete account | `POST /me/exports`, `DELETE /me` | Auth; durable jobs and explicit destructive-action UX before real-user launch |

Guides are initially build-time editorial content, so they need no API/CMS. Public reviews, feed, participants, and recommendation endpoints are intentionally unspecified until their product phase.

Account bootstrap is safe to retry because `(auth_issuer, auth_subject)` is unique and creation uses `INSERT ... ON CONFLICT DO NOTHING` inside a transaction. It does not use a caller-supplied owner or general idempotency-key table. Neither bootstrap nor GET reactivates a disabled account. Successful account responses and errors are `Cache-Control: no-store`; errors contain a generated `requestId` also returned as `X-Request-ID`. Missing/invalid tokens return 401; missing/unavailable identity infrastructure returns 503. Error payloads exclude raw validation input and internal SQL/provider details.

## Wine-first capture example

```json
{
  "wine": { "kind": "CATALOG_RELEASE", "releaseId": "<uuid>" },
  "consumedDate": "2026-09-14",
  "consumedTime": null,
  "notes": "",
  "occasion": {
    "kind": "NEW",
    "title": "Dinner with friends",
    "date": "2026-09-14",
    "location": { "kind": "CUSTOM", "label": "Alex's house" }
  },
  "mediaIds": []
}
```

The wine/date alone is valid; omit `occasion` entirely for a standalone glass. Alternative wine selectors are `USER_WINE` and `MANUAL`; manual requires a name and explicit vintage status, with unknown facts allowed. An `EXISTING` occasion requires an accessible occasion ID. Schemas reject combinations such as both new and existing occasion data.

On submit, create/reuse the user-wine record, create any inline manual identity and new occasion, save the entry, attach owned staged/ready media references, and record the idempotency result in one SQL transaction. Return 201 with IDs, versions, and media processing statuses. If validation fails, no partial journal records remain. Creating this entry does not change a rating unless the user explicitly supplied a rating command in the flow; process that command with the same version rules and transaction when included.

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
