# M08 — Safe media cleanup and quota recovery

Status: M08a implemented and verified, October 17, 2026. M08 remains incomplete;
physical deletion, outstanding-write reconciliation and quota release are M08b.

## Slices and verification

1. M08a: retirement eligibility and durable fencing. Add migration 0017, a nullable
   retirement timestamp/index, the media cleanup command and guards in upload
   access/retry and publication. Verify shared entry/occasion/cover references,
   known live grants, unresolved signing attempts, jobs/leases, recent drafts,
   concurrent attachment versus retirement, retry identity and migration/grants
   using disposable Postgres. No objects are deleted or quota released in this slice.
2. M08b: physical deletion with bounded retries, retained tombstones and late-object
   reconciliation. Establish tracking for outstanding derivative writes before
   enabling deletion of processed assets; a job lease alone cannot fence an
   already-issued Storage request. Verify real Storage deletion/retry and late
   objects, worker restarts, quota release and repeated reconciliation.

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
