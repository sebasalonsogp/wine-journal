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

Run retirement followed by sweep periodically while media is enabled. The recurring
runner below combines these operations. Backlogs need enough batch throughput. Do
not enable unattended deletion until every API and worker runs the new code. Stop
old processes before applying migrations locally.

Migration 0018 puts every pre-existing asset on a write hold. New code explicitly
initializes tracking; inserts by old code retain the conservative DB default. A
worker records a hold before each external write and settles it only after an
acknowledged successful response for that exact attempt. Readback after timeout can
publish a usable photo but cannot settle that uncertain request. Legacy/uncertain
holds are never cleared automatically or by guessed timeouts; provider-backed
resolution tooling remains future work. These assets retain their quota. Migration
0018 refuses downgrade with holds; 0020 refuses downgrade after quota release.

## Recurring maintenance and hold diagnostics (M08c1)

From `repo/`, inspect one read-only cycle, or repeat previews:

```sh
uv run --directory apps/api --locked python -m wine_journal.media.maintenance
uv run --directory apps/api --locked python -m wine_journal.media.maintenance --watch
```

After reviewing the preview and confirming all writers run the current code,
explicitly enable the deletion runner under the deployment's process supervisor:

```sh
uv run --directory apps/api --locked python -m wine_journal.media.maintenance --watch --apply --limit 50 --interval-seconds 300
```

No scheduler or deletion service is installed by these repository changes. `--watch`
runs immediately, then waits 300–3600 seconds **after each completed cycle**. Cycles
are serial: slow runs do not overlap or accumulate catch-up work. Each cycle selects
at most `--limit` (1–100) retirements and the same number of deletions. Both are
rechecked by the existing account-lock guards. The second query runs after retirement
so a newly retired asset can be deleted in the same cycle. SIGINT/SIGTERM stops the
wait immediately and stops between assets; an in-flight operation finishes first.
The runner continues cleanup even if new media uploads are disabled.

Preview never loads Storage configuration and performs no mutations. Apply validates
the private bucket before retiring anything. Per-asset failures are counted and do
not stop other candidates. A cycle-level failure emits a fixed error and retries
after the interval in watch mode. One-shot mode exits nonzero on failure. Startup
configuration errors exit nonzero; the supervisor should restart with backoff.
Use the existing ignored server `.env`/`.env.storage`, not credentials in arguments.

Stdout contains JSON events with UTC timestamp, `runId`, `entryPoint` and a fixed
event name. Each cycle emits start/finish or failure; finish includes duration,
batch counts, successful work and independent retirement/deletion failure counts.
Only aggregate values are emitted—no account/asset IDs, keys, URLs or exception
bodies. These are operator diagnostics, not a public API.

- `HELD_ASSETS`: investigate persistent/growing holds. `heldAssets` counts each
  unreleased asset with signing or write uncertainty once. `signingHeldAssets` and
  `writeHeldAssets` overlap. `heldReservedBytes` is reserved capacity, not measured
  provider usage. Referenced photos can have holds; this is not a deletion backlog.
- `BATCH_FULL`: the selected retirement or deletion batch reached its limit. This
  is a possible backlog signal, not proof of more work. Increase capacity only
  after inspecting repeated cycles and provider costs.
- `WRITE_ACCOUNTING_MISMATCH`: an unreleased asset has more pending attempt records
  than its write-hold counter. The cycle stops before candidate selection or cleanup;
  it does not repair the counter. One-shot mode exits nonzero; watch mode reports the
  alert and retries after its normal interval. Investigate before enabling/resuming
  apply. The guard is a snapshot check in this runner, not a replacement for per-asset
  retirement/deletion checks or a database-wide constraint.
- `CLEANUP_FAILED` or `maintenance_cycle_failed`: investigate sustained failures
  and quota recovery delays. For deployment, alert after repeated failures, missing
  cycle starts, or a start with no finish within the deployment's operation budget.
  The runner emits signals; routing them to an alert destination is deployment work.

The supervisor must capture/rotate logs, restart failed processes with backoff and
enforce a shutdown/run deadline suited to batch size and provider latency. The
existing durable retirement and attempt timestamps make restart/replay safe. Avoid
running both a supervisor loop and a separate scheduler for the same deployment.

### Held-upload investigation

Each maintenance report also includes three aggregate fields, computed together in
one SQL statement so concurrent attempt registration/acknowledgement cannot skew
the comparison between the ledger and counters:

- `pendingWriteAttempts`: unacknowledged ledger records attached to unreleased assets.
  These can be actively running requests; the count does not establish failure.
- `unattributedWriteHolds`: the sum of each asset's positive difference between its
  write counter and pending ledger count. These may be migration holds or uncertain
  requests predating the ledger; they cannot all be classified as legacy. A deficit
  on one asset never cancels an excess on another.
- `writeAccountingMismatchAssets`: unreleased assets whose pending ledger count
  exceeds their counter, including assets whose counter is zero.

Acknowledged attempts and released assets do not contribute to these new counts.
Multiple attempts on one asset do not multiply `heldAssets` or reserved bytes.
These are investigation signals, not settlement evidence; age, matching counts and
zero mismatches do not authorize releasing a hold. Only counts enter the report,
never owner/asset/attempt IDs, lease tokens, object keys or provider responses.

Historical counters cannot distinguish a legacy migration hold from every possible
unacknowledged request or identify individual provider requests. A successful retry,
an existing file, an absent file, an expired lease, or elapsed time is not evidence
that all earlier requests stopped. Therefore this runner never clears holds.

Before releasing a hold, stop/fence all relevant writers, account for upload
capabilities, and obtain authoritative provider evidence that each outstanding
operation is terminal. Keep that evidence in a restricted operational record and
recheck ownership/references under the account lock. If historical evidence is
unavailable, preserve the reservation. An operational resolution tool for historical
or lost responses remains open; there is intentionally no force-clear command.

### Exact derivative-write acknowledgements (M08c2)

Migration 0021 adds `photo_write_attempts`. Before external I/O, the worker commits
an attempt UUID, owner/asset identity, worker lease token, derivative kind and creation
time in the same transaction as its counter increment. This is an internal attempt
identity, **not** a provider request ID. No credentials, URLs or image contents are
stored in this ledger. Existing counters are preserved without fabricated backfill.

After Storage returns a confirmed successful write response, the
worker records an immutable acknowledgement timestamp and decrements exactly one
hold in a transaction under the account lock. Duplicate/concurrent acknowledgements
are no-ops. A late response can settle its own attempt after lease expiry, account
disablement or another worker completing the job; this operation cannot publish a
photo or change queue state. Publication and further writes still require a valid
current lease. Retries never acknowledge a different attempt or a legacy hold.

Write acknowledgement and readback are separate operations. The worker persists
the acknowledgement **before** calling `verify_derivative`, which checks size,
type, exact contents and object identity. A later timeout, missing file or changed
image cannot erase known write completion. Failed verification still blocks READY;
transient failures use the queue retry policy and conflicts remain rejected. If
the acknowledgement transaction fails, the worker stops before readback and keeps
the unresolved hold. Neither step holds a database connection across Storage I/O.
Only both verified derivatives plus the current lease permit publication.

Timeouts, readback-only success, lost responses, and failure to commit the
acknowledgement remain unresolved. This slice does not establish provider evidence
after a crash, resolve historical counters, or change signing-attempt handling.
No new public endpoint or operator settlement command is exposed.

Apply migration 0021 before restarting the photo worker with this code. Older
workers remain conservative but cannot produce attempt evidence; upgrade all workers
before relying on the ledger. Runtime identity updates/deletion are denied, and
acknowledgements cannot be cleared or changed. Asset deletion cascades only through
an administrative operation; runtime asset deletion remains denied and cleanup keeps
the tombstone and its ledger. Downgrade refuses once any attempt evidence exists,
including acknowledged attempts. Code rollback to the prior worker may retain the
additive table; do not discard the ledger to force schema rollback.

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
