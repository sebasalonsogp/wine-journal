# Media jobs

`photo_sandbox.PhotoSandbox` provides isolated conversion and `photo_processing.PhotoPublisher` publishes two verified private derivatives with fenced asset updates and retry recovery. Migration 0013 persists output metadata and fixed failure outcomes. The worker registers `process_photo` when media is enabled and checks private Storage and the decoder before claiming work. See [the processing checkpoint](../../../../../tasks/photo-processing-checkpoint.md) for limits and verification.

There are no public job routes. Unsupported kinds become terminal failures; no fake processing marks assets ready. A terminal `process_photo` failure also fails its matching owned asset if it is still PROCESSING. Already READY/FAILED assets are preserved.

`models.py` defines the queue; `jobs.py` implements transaction-aware enqueue, claiming, renewal and acknowledgement. `wine_journal.worker` is a separate process in this same Python project. It uses the restricted `wine_api` connection from the ignored API `.env` and the private Storage service credential from `.env.storage`; it never loads migration/admin credentials. No credential or application environment is passed into the decoder container.

## Running

After the usual local setup and current migrations, from `repo/`:

```sh
uv run --directory apps/api --locked python ../../scripts/configure_storage.py
uv run --directory apps/api --locked python ../../scripts/build_photo_decoder.py
```

Set `WINE_JOURNAL_MEDIA_UPLOADS_ENABLED=true` in the ignored `apps/api/.env`, then restart the API and start the separate worker:

```sh
uv run --directory apps/api --locked python -m wine_journal.worker --once
uv run --directory apps/api --locked python -m wine_journal.worker
```

`--once` checks/processes at most one job (or marks one exhausted lease failed) and exits. Polling defaults to two seconds; `--poll-seconds` accepts 1–60. Leases default to 60 seconds; `--lease-seconds` accepts 1–3600. Normal shutdown stops claiming, lets the current bounded handler return, then disposes connections. A forced stop leaves the lease for another worker to reclaim. A production process supervisor and media subprocess deadlines/resource limits belong to deployment and the processing slices; the runner does not forcibly interrupt a hung Python handler.

The worker requires Linux Docker and its prebuilt decoder image. The API does not need Docker access. With media disabled the worker exits without claiming work; with invalid Storage/decoder configuration it exits nonzero before claiming. The sample environment stays disabled by default. A deployed worker needs a process supervisor and hosting/cache verification under R07; a local background process is not a deployment setup.

## Private viewing

- `GET /api/v1/media/{asset_id}` returns owned status, generic failure code and ready dimensions. It requires an active account, returns no source/object paths and remains usable during Storage outages.
- `POST /api/v1/media/{asset_id}/view` accepts only `{"variant":"display"}` or `{"variant":"thumbnail"}`. It requires owned READY state before signing and rechecks account/state afterward. It returns `assetId`, `variant`, `viewUrl` and `expiresAt`. Unknown/foreign assets return 404, unfinished/failed assets 409 and provider failures 503. No original-file viewing is exposed.
- Both API responses use `Cache-Control: no-store`. Signed URLs are bearer capabilities: anyone who already holds one can read that exact derivative until the provider stops accepting it. Do not persist/log them or treat them as share links. Request a new link after expiry.
- The local provider signs for 120 seconds and returns an HTTP `Expires` deadline matching the token. Its signed route does not return the uploaded object's `no-store` directive; authenticated object reads do. Local tests warm a short-lived signed URL, wait for actual expiry and verify rejection. Account disablement prevents new links but cannot recall downloaded files or already-issued capabilities.
- Hosted Smart CDN may retain a cached response beyond token expiry. Verify the actual deployment's cache policy before enabling media; use an authenticated no-store proxy if a strict access-revocation deadline is required. See [Supabase signed URL caching](https://supabase.com/docs/guides/storage/cdn/smart-cdn#signed-urls-and-cdn-caching). The frontend should fetch private images without persistent caching and clear them on sign-out (M04).

## Retirement preview (M08a)

After migrations through 0020 and deployment of the updated API and worker, preview a bounded
batch from `repo/`:

```sh
uv run --directory apps/api --locked python -m wine_journal.media.cleanup --limit 50
```

The default performs no writes and reports aggregate counts only. `--apply` records
irreversible retirement timestamps for the eligible batch. It does **not** delete
Storage files or release quota. Deploy the new API/worker before using `--apply`;
older code does not enforce the retirement and write fences. Retirement and
physical deletion are separate commands so each batch can be inspected.

Retirement requires an unreferenced upload at least 24 hours old, no unresolved
signing or derivative-write attempts, no unexpired known upload link, no pending/running job (including
expired leases), and a state other than PROCESSING. Eligibility is rechecked under
the same account lock used by attachments and covers. An old operation key receives
409 UPLOAD_RETIRED; status, completion, viewing and new references receive 404.
Retired identities cannot be restored or reused. A failed partial batch can be
retried without changing already retired rows.

Migration rollback is allowed before any retirement is recorded and deliberately
refused afterward. Restore code that understands the fence instead of dropping it.
Existing files/reservations remain until the deletion reconciler verifies absence.
See [M08 checkpoint](../../../../../tasks/media-cleanup-checkpoint.md).

## Deletion and quota reconciliation (M08b)

Preview retired assets due for deletion, then explicitly apply a bounded batch:

```sh
uv run --directory apps/api --locked python -m wine_journal.media.sweep --limit 50
uv run --directory apps/api --locked python -m wine_journal.media.sweep --limit 50 --apply
```

Preview does not contact Storage or mutate timestamps. Apply rechecks retirement,
references and outstanding work under the account lock, persists its attempt time,
and releases the DB connection before calling Storage. It deletes only the asset's
exact original/display/thumbnail keys and verifies all three are absent. Failed or
interrupted passes retry after five minutes. Each invocation does at most 100 assets;
the default is 50. Individual failures do not prevent other candidates from running.
The command returns nonzero if any attempted deletion fails and prints aggregate
counts only. It never lists objects or empties a bucket.

Confirmed deletion records an immutable quota-release timestamp; original reserved
bytes and operation identity remain for audit/retry protection. New reservations
exclude released assets from byte, asset and inflight limits. Retired upload-operation
replay still fails. This is **logical journal quota**, not a hard instantaneous cap
on provider bytes: an already-accepted client upload can arrive late. Every tombstone,
including released ones, stays eligible for later sweeps to delete such objects.
Never stop revisiting a row just because its first deletion succeeded.

Run retirement followed by sweep periodically (at least every five minutes while
media is enabled); these are one-shot operator commands, not an installed scheduler.
Automatic supervision/scheduling and alerts are the next operational slice. Backlogs
need enough batch throughput. Do not enable unattended deletion until every API and
worker runs the new code. Stop old processes before applying migrations locally.

Migration 0018 puts every pre-existing asset on a write hold. New code explicitly
initializes tracking; inserts by old code retain the conservative DB default. A
worker records a hold before each external write and settles it only after an
acknowledged successful response and a valid lease. Readback after timeout can
publish a usable photo but cannot settle that uncertain request. Legacy/uncertain
holds are never cleared automatically or by guessed timeouts; provider-backed
resolution tooling remains future work. These assets retain their quota. Migration
0018 refuses downgrade with holds; 0020 refuses downgrade after quota release.

## Contract

- Call `enqueue(session, ...)` inside the same transaction as the domain change. A per-owner operation UUID identifies one exact kind/reference/attempt policy. Repeating it returns the existing job; different work under the same key is rejected. Rolled-back domain changes leave no job.
- Jobs carry only owner/reference/operation UUIDs and a bounded internal kind. Do not put files, signed URLs, credentials, paths or journal text in the queue. Handlers re-read the owned resource and check its current state; `reference_id` is not a media FK because the queue can support other internal kinds.
- Claiming locks one eligible row with `FOR UPDATE SKIP LOCKED`, gives it a new token and increments attempts. The transaction ends before the handler runs. PostgreSQL's clock controls readiness/expiry.
- The token and unexpired lease guard finish/renew. Old workers cannot acknowledge a reclaimed job. Between bounded processing chunks, a handler may renew; a failed renewal means it must stop publishing results. There is no automatic renewal that could hide a hung handler.
- Delivery is **at least once**. A handler can finish its effect and die before acknowledging. Use deterministic output identities, uniqueness/upserts and resource-state checks to tolerate a rerun. Queue fencing guards queue state; it does not itself fence external writes or guarantee exactly-once effects. New media handlers must prove idempotency with their actual storage/database operations.
- Default attempts are five, configurable per job from one to ten. Failures wait `min(300, 2 ** attempt)` seconds. A final expired lease or exhausted failure becomes `FAILED`; successful jobs become `SUCCEEDED`. Unknown kinds fail immediately. Enqueueing a terminal operation does not reset it.
- Only fixed error codes are stored; worker logs include job ID, attempt and acknowledgement outcome, never exception strings, owner data, tokens or connection URLs. Database failure leaves work durable and retries polling; one-shot mode exits nonzero.
- Terminal rows retain operation claims. Cleanup/retention and account deletion must be designed with media lifecycle work; do not delete deduplication records while a corresponding operation can be replayed.

The runtime role can insert/read jobs and update only queue-state columns. Job identity/ownership/operation metadata cannot be rewritten and runtime deletion is denied. API and worker currently share this restricted role; a separate worker role can be introduced if future resource permissions justify it.

Read-only operational summary, using an authorized database session:

```sql
SELECT state, count(*) FROM app.jobs GROUP BY state;
SELECT error_code, count(*) FROM app.jobs WHERE state = 'FAILED' GROUP BY error_code;
```

See [M01 verification](../../../../../tasks/media-jobs-checkpoint.md). Lock behavior follows [PostgreSQL SELECT](https://www.postgresql.org/docs/17/sql-select.html#SQL-FOR-UPDATE-SHARE) and [SQLAlchemy with_for_update](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.with_for_update).
