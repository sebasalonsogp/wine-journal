# Media jobs

M03a now provides an isolated production converter through `photo_sandbox.PhotoSandbox`; it is not yet registered as a queue handler. See [the processing checkpoint](../../../../../tasks/photo-processing-checkpoint.md) for its build command, limits and verification. Keep uploads disabled while M03b/M03c implement publication and private viewing. The remaining M01 notes below describe the queue foundation.

M01 implements durable background execution. Uploads, private object storage and image/video handlers are subsequent slices. There are no public job routes and no media handlers in the production registry yet. Unsupported kinds become terminal failures; no fake processing marks assets ready.

`models.py` defines the queue; `jobs.py` implements transaction-aware enqueue, claiming, renewal and acknowledgement. `wine_journal.worker` is a separate process in this same Python project. It uses the existing restricted `wine_api` connection from the ignored API `.env`; it never loads migration/admin credentials. No new dependency, service or credential is required.

## Running

After the usual local setup and migrations, from `repo/`:

```sh
uv run --directory apps/api --locked python -m wine_journal.worker --once
uv run --directory apps/api --locked python -m wine_journal.worker
```

`--once` checks/processes at most one job (or marks one exhausted lease failed) and exits. Polling defaults to two seconds; `--poll-seconds` accepts 1–60. Leases default to 60 seconds; `--lease-seconds` accepts 1–3600. Normal shutdown stops claiming, lets the current bounded handler return, then disposes connections. A forced stop leaves the lease for another worker to reclaim. A production process supervisor and media subprocess deadlines/resource limits belong to deployment and the processing slices; the runner does not forcibly interrupt a hung Python handler.

No worker needs to run continuously until real handlers are registered. Use `--once` to check local startup now.

## Contract

- Call `enqueue(session, ...)` inside the same transaction as the domain change. A per-owner operation UUID identifies one exact kind/reference/attempt policy. Repeating it returns the existing job; different work under the same key is rejected. Rolled-back domain changes leave no job.
- Jobs carry only owner/reference/operation UUIDs and a bounded internal kind. Do not put files, signed URLs, credentials, paths or journal text in the queue. The future handler must re-read the owned resource and check its current state; `reference_id` is not yet a media FK because assets are not implemented.
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
