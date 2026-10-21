# M08 — Safe media cleanup and quota recovery

Status: M08a, M08b, M08c1 and the first three M08c2 slices implemented, October 19, 2026. M08 remains incomplete
pending legacy/uncertain-hold resolution, deployment supervision/alert routing and
audit closeout.

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
5. M08c1: add `media/maintenance.py` for serial retirement/sweep cycles,
   default preview, explicit apply, bounded batches, interruptible polling and
   redacted JSON status. Add `media/maintenance_status.py` for aggregate hold
   diagnostics. Verify real SQL eligibility/hold totals, per-asset failures, restart
   and shutdown behavior, configuration errors, and a preview subprocess. Document
   supervisor/alert requirements; do not install an unattended deletion service on
   the developer machine.
6. M08c2: evidence-based resolution of legacy/uncertain write/signing holds. The
   database counter cannot establish which remote request has stopped. Do not add
   a force-clear flag or infer safety from age; provider-backed evidence remains
   required. Deployment supervision and alert delivery remain release requirements.
   First slice: retain one immutable identity per new derivative write, registered
   atomically with its counter before I/O. A confirmed response settles only that
   attempt under the account lock, independently of a subsequently expired worker
   lease. Publication still requires the current lease. Verify duplicate/concurrent
   acknowledgements, ownership, transaction rollback, prior uncertainty, immutable
   evidence and migration preservation. Historical counters and signing holds stay
   unchanged; this does not invent provider evidence for requests already lost.
   Second slice: persist a confirmed derivative-write response before readback.
   Separate write acknowledgement from byte/identity verification so a later read
   failure cannot discard known terminal evidence. Verify that failed readback still
   blocks publication, unknown writes retain their holds, and a failed acknowledgement
   commit stops further I/O. No historical settlement or schema change is involved.
   Third slice: report pending tracked attempts separately from counter holds without
   attempt records, using one database snapshot. Detect counters smaller than their
   pending ledgers; abort the maintenance cycle before selecting/mutating assets and
   emit a fixed alert. Verify mixed evidence, acknowledged/released exclusions,
   single-statement totals, empty totals and CLI failure behavior. Never label all
   unattributed holds as legacy or infer that pending attempts are failed requests.

The runner's operational questions are: is cleanup progressing, are batches full,
are failures delaying recovery, and how much reserved capacity is held? Structured
cycle events answer the first three; read-only aggregate hold counts answer the
last. No private identities or raw provider/DB exceptions appear in those events.

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

## M08c1 evidence — October 19

All **346 API tests passed**, including real Storage and isolated Docker decoding.
Seventeen new checks cover preview without Storage configuration, hold-count
deduplication, real eligibility/deletion/quota orchestration, repeated runs,
subprocess preview/restart, per-asset failure isolation, startup validation,
redacted failures, watch-mode recovery and shutdown between assets/during waits.

Ruff, formatting (146 files), strict typing (121 source files), package build and
unchanged OpenAPI export passed. The browser secret scan again checked 19 scripts.
No schema, dependencies, environment variables, public APIs or frontend behavior
changed. The maintenance runner is a separate executable module; existing API and
photo-worker processes do not need a migration or restart for this slice.

A local one-cycle preview found 7 retirement candidates and 72 assets with write
holds; zero assets were retired or deleted. Counts describe the whole local test
database, and reserved capacity is not measured provider usage. No apply/watch
deletion process or OS-level scheduler was installed. The PR records exact-head CI
results. M08c2 remains open because counters alone cannot identify or certify each
legacy/uncertain provider request; an elapsed-time or force-clear bypass is absent.

## M08c2 first-slice evidence — October 19

Migration 0021 and the photo publisher now retain exact derivative-attempt identities
before I/O. A confirmed response atomically records acknowledgement and settles
only its own hold, even after lease expiry or a replacement worker finishing. This
never authorizes stale publication. Lost responses, readback-only success, legacy
counters and signing holds are unchanged. There is no manual settlement bypass.

All **352 API tests passed**, including real Storage and Docker decoding. Six new
scenarios verify concurrent/idempotent acknowledgement with other/legacy holds,
ownership checks, registration rollback, inconsistent-counter failure, immutable
evidence and protected downgrade, acknowledgement after a replacement completes,
and migration preservation. Existing publication tests now verify committed attempt
records before I/O, retained uncertainty after retry, and late acknowledgement
without stale publication.

Ruff, formatting (148 files), strict typing (122 source files), package build,
unchanged OpenAPI export and the 19-script browser secret scan passed. Migration
0021 was applied locally with journal/media counts, total reservations, both hold
counters and retirement/release counts unchanged. No uploads were retired, deleted
or quota-released by this rollout. API and photo worker run the updated code.

This is prospective evidence tracking, not historical recovery. Requests whose
responses were lost still need authoritative terminal evidence; internal UUIDs are
not provider request IDs. A safe operational resolution workflow, deployment
supervision/alert routing and full dependency-audit closeout remain open. Exact-head
CI results are recorded on the PR.

## M08c2 second-slice evidence — October 19

The Storage adapter now separates write acknowledgement from derivative readback.
The publisher records confirmed completion before verifying bytes, so a later read
failure cannot discard that evidence. Verification remains mandatory before READY;
unknown write responses still retain their holds. An acknowledgement commit failure
stops the worker before verification or further writes. This is an internal boundary
change without a migration, new configuration, dependency or public API change.

All **362 API tests passed** with real Storage and Docker decoding. Six HTTP cases
first reproduced confirmation loss on 200/201 responses followed by timeout, missing
object or changed size; they pass after the split. Four integration cases verify
durable confirmation before failed readback, rejection/retry without publication,
recovery after transient failure, preservation of other holds and stopping on an
acknowledgement failure. Existing real JPEG/HEIF tests verify the split operations,
immutable output conflicts, restart, deletion and late-upload reconciliation.

Ruff, formatting, strict typing, package build, unchanged OpenAPI export and the
19-script browser secret scan passed. The idle local photo worker was restarted
with this code; no cleanup apply process was run. Historical/lost-response and
signing holds, deployment supervision and dependency-audit closeout remain open.
Exact-head CI results are recorded on the PR.

## M08c2 third-slice evidence — October 19

Maintenance now reports pending tracked write attempts, counter holds without
attempt records, and assets whose pending ledger exceeds their counter. One SQL
statement compares both sources in the same snapshot. These are aggregate diagnostics
for unreleased assets; they neither classify all unknown holds as legacy nor prove
that pending requests failed. Multiple attempts do not multiply reserved capacity.

A detected deficit stops the maintenance cycle before candidate selection or
Storage access. The fixed `WRITE_ACCOUNTING_MISMATCH` alert returns a nonzero
one-shot exit; watch mode retries normally. No counter repair or settlement is
performed. The snapshot guard does not replace existing per-asset safety checks.

All **370 API tests passed**, including real Storage and Docker decoding. Eight new
cases cover mixed/acknowledged evidence, released exclusions, empty numeric totals,
deficits in preview/apply, no candidate queries on mismatch and CLI alert/exit
behavior. The existing subprocess test verifies the added counts remain private
and read-only. Ruff, formatting, strict typing, build, unchanged OpenAPI and the
19-script browser secret scan passed.

The local read-only preview found 72 unattributed write holds, zero pending tracked
attempts and zero mismatches. It retired/deleted/released nothing. No schema,
dependency, configuration or public API change was needed, and existing API/worker
processes need no restart for this maintenance-only change. Historical resolution,
supervision/alert delivery and audit acceptance remain open. Exact-head CI evidence
is recorded on the PR.
