# Media jobs

`photo_sandbox.PhotoSandbox` provides isolated conversion and `photo_processing.PhotoPublisher` publishes two verified private derivatives with fenced asset updates and retry recovery. Migration 0013 persists output metadata and fixed failure outcomes. The worker registers `process_photo` when media is enabled and checks private Storage and the decoder before claiming work. See [the processing checkpoint](../../../../../tasks/photo-processing-checkpoint.md) for limits and verification.

There are no public job routes. Unsupported kinds become terminal failures; no fake processing marks assets ready. A terminal `process_photo` failure also fails its matching owned asset if it is still PROCESSING. Already READY/FAILED assets are preserved.

`models.py` defines the queue; `jobs.py` implements transaction-aware enqueue, claiming, renewal and acknowledgement. `wine_journal.worker` is a separate process in this same Python project. It uses the restricted `wine_api` connection from the ignored API `.env` and the private Storage service credential from `.env.storage`; it never loads migration/admin credentials. No credential or application environment is passed into the decoder container.

## Running

After the usual local setup and migration 0013, from `repo/`:

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
