# M08 — Safe media cleanup and quota recovery

Status: M08a and M08b implemented, October 17, 2026. M08 remains incomplete pending
supervised recurring execution, legacy/uncertain-hold resolution and audit closeout.

## Slices and verification

1. M08a: retirement eligibility and durable fencing. Add migration 0017, a nullable
   retirement timestamp/index, the media cleanup command and guards in upload
   access/retry and publication. Verify shared entry/occasion/cover references,
   known live grants, unresolved signing attempts, jobs/leases, recent drafts,
   concurrent attachment versus retirement, retry identity and migration/grants
   using disposable Postgres. No objects are deleted or quota released in this slice.
2. M08b1: migration 0018 and durable derivative-write holds. Register each attempt
   before external I/O; settle only an acknowledged successful response under a
   valid lease. Legacy assets receive a hold. A later successful retry does not
   clear an earlier uncertain request. Focused publication/retirement/Storage
   suite passed 65 tests before proceeding to deletion.
3. M08b2: migration 0019, exact-key Storage removal with absence verification,
   and a default-preview sweep command. Persist a five-minute backoff before I/O,
   recheck eligibility at claim time, isolate per-asset failures, and revisit
   tombstones indefinitely. Real JPEG/HEIF fixtures delete all three objects,
   simulate a late upload, then delete it on a subsequent pass.
4. M08b3: migration 0020 and immutable quota-release timestamps. Release only
   after confirmed deletion, preserving original reservations and retry identities.
   New uploads exclude released rows from byte/asset/inflight counts. Verify
   quota exhaustion/recovery, repeat cleanup, failure holds and rollback protection.
5. M08c: supervised recurring retirement/sweep execution and aggregate alerts;
   evidence-based resolution of legacy/uncertain write/signing holds. Both current
   commands are one-shot; no scheduler has been installed or enabled.

## Safety rules

All reference mutations and retirement take the account lock first. A retirement
candidate has no active entry/occasion photo or personal cover, is at least 24 hours
old, has no unresolved signing attempts, no unexpired known upload capability,
no pending/running processing job and is not PROCESSING. Recheck eligibility under
the account lock before recording retirement. Never clear a retirement tombstone;
old upload-operation retries cannot mint a new capability or recreate the asset.

The 24-hour window is draft retention, not proof that remote writes have ended.
An expired worker lease likewise does not prove a remote request has stopped.
M08a's command defaults to a bounded preview; `--apply` records retirement only.
Storage bytes, immutable operation claims and full quota reservations remain.
Unknown signing outcomes stay on hold, even after another retry succeeds. No
timer or guessed provider timeout clears that uncertainty.

The sweep uses the same safety predicates for retired rows. Successful deletion
means the three exact keys were verified absent at that instant. Quota is logical
journal allocation, not a strict bound on instantaneous provider bytes: a request
accepted before upload-capability expiry can finish later. Released tombstones
are retained and revisited, so late objects are eventually removed. Without regular
sweeps this guarantee does not hold; deployment must supervise the commands and
monitor backlog/failures. No unknown derivative write is released by a timeout.

Use the provider deletion API, never direct deletes from its metadata tables:
[Supabase file removal](https://supabase.com/docs/reference/python/storage-from-remove).
The restricted runtime DB role gains only column updates. Preview does not load
Storage credentials; apply uses the existing ignored server-side configuration.

Migration 0018 holds all existing assets and old-code inserts. Do not clear these
holds merely to recover space. A production rollout must stop old writers before
enabling cleanup. Migration 0018 refuses rollback with unresolved writes; 0020
refuses rollback after quota release. No new environment variables or dependencies.

Supabase documents signed upload URLs as valid for two hours:
[official upload reference](https://supabase.com/docs/reference/python/storage-from-createsigneduploadurl).
The app retains each returned expiration and unresolved attempts. That documented
TTL does not establish a bound on a request already accepted by the provider.

## M08a evidence

All 316 API tests passed with real Storage and the isolated Docker photo decoder
enabled. Thirteen new retirement cases cover six independent safety holds, shared
references and preview rechecks, every affected public access path, immutable
retirement, retained quota, three concurrent attachment races, migration rollback
protection, and default-preview/apply/replay/error behavior. The complete fixture
also covers two owners and rejects cross-owner retirement. No Storage call occurs
when retired upload operations are retried.

Ruff, formatting, strict typing (116 source files), API package build and Python
dependency audit passed. OpenAPI export is unchanged. Seven targeted browser
scenarios passed after migration: covers, capture/entry uploads, retry/removal,
occasion albums, wine highlights and sign-out. The previous web build is unchanged;
built-browser secret checks passed.

Local migration 0017 preserved drinking-entry, occasion, personal-wine, upload-asset
and job row counts. No upload was retired. A read-only preview found 28 candidates;
`--apply` was exercised only against synthetic disposable-database fixtures. The
API and worker use the updated code. Do not run an older API alongside retirement;
all writers must enforce the new fence before enabling the apply command.

The production npm audit remains clear. The full development audit still reports
the existing five package findings from braces GHSA-vfj7-8cjw-p6xm. Its audit gate
was not changed. This checkpoint does not claim merge/deployment readiness.

## M08b evidence

All **329 API tests passed** with real Storage and the Docker decoder enabled.
Added coverage includes registered write holds before I/O, readback after timeout,
lease loss, preserved uncertainty after successful retry, legacy migration holds,
exact-key delete failures/absence verification, concurrent sweep claims, cross-owner
rejection, default preview, per-asset failure isolation, delayed retry, late uploads,
quota exhaustion/recovery, immutable release timestamps and protected downgrades.
The two real Storage scenarios cover JPEG and HEIF, restart the registered worker,
delete the original and both derivatives, recreate a late original through the
provider and remove it on another sweep. Test-only SQL clears known synthetic
interruption holds; no production resolution bypass was introduced.

Ruff, formatting, strict typing (117 source files), package build and unchanged
OpenAPI export passed. The built-browser scan checked 19 scripts without finding
generated private values. No dependency or environment additions were required.

Local migrations 0018–0020 preserved entry, occasion, personal-wine, upload and job
counts and the sum of all reserved bytes. Every pre-existing upload received the
legacy write hold. No local upload was retired, deleted or quota-released. Cleanup
mutation has been exercised only against synthetic disposable database/bucket data.
The API and photo worker were restarted after migration. All seven targeted browser
scenarios passed: covers, capture/retry/removal, occasion albums, wine highlights
and cross-tab sign-out. Both cleanup previews reported zero candidates and made
no changes. Exact-head CI outcomes are recorded on the PR after their runs finish.
