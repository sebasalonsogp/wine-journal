# M02: Private upload authorization

September 30, 2026. **M02a (Storage integration) is complete; M02b (owned assets, reservations and routes) remains.** The parent task is not complete and no upload endpoint/UI is enabled yet. The preceding R04 commit passed all CI jobs, including the browser suite.

## M02a delivered

- `integrations/storage.py` is a concrete Supabase REST client, with separately loaded `StorageSettings`. It requires HTTPS outside loopback, redacts the service key and signed capability in object representations, rejects redirects, caps JSON responses, uses bounded network timeouts and disables ambient proxy configuration.
- Local provisioning creates `wine-journal-staging` as private, with a 20 MiB per-object limit and only JPEG/PNG/WebP/HEIC/HEIF MIME declarations. Existing buckets must match exactly; the script never silently changes their public state or limits. Actual image validation is still M03; a MIME declaration is not evidence of valid image bytes.
- Staging keys are generated as `staging/<asset UUID>/<random object UUID>`. Caller-supplied filenames and arbitrary paths are rejected. Signing never opts into overwrite. Returned capabilities must name the exact bucket/key, contain a bounded future expiry and have no upsert permission. Only the trusted configured endpoint can appear in the returned URL.
- Object verification parses the provider's authoritative size/type/ETag/ID and requires the expected key. Provider errors and unexpected bodies never flow into application messages. The existing HTTPX dependency is promoted from development to runtime; no new package/version is introduced.
- `configure_storage.py` creates an ignored `apps/api/.env.storage` only after successful local bucket verification. Repeated setup preserves and verifies an existing credential rather than replacing it. It does not use a hosted project or change the journal database. `check_browser_secrets.py` also checks this service key when the file exists.
- CI provisions local Storage and runs the real-provider smoke test after starting the disposable stack. Its temporary probe bucket has a fresh UUID, and cleanup removes only its three known synthetic keys and that bucket. No journal photos or application bucket are emptied.

## Verification

**145 API tests passed locally**, including 22 new adapter/configuration cases. Lint, formatting, types, API build and dependency audit passed. The browser bundle contains none of the generated private values. API contracts and frontend behavior are unchanged.

The real local Storage probe passed:

1. Create and recheck a private bucket; upload with a valid path-bound capability.
2. Read authoritative object size and content type using the server credential.
3. Reject overwrite even when the uploader supplies `x-upsert: true`; the original size remains intact.
4. Deny anonymous reads through both public and authenticated object routes, and deny unsigned creation.
5. Reject using the same capability for a different object path or for reading.
6. Reject files above the bucket byte limit and disallowed MIME declarations.
7. Reject a correctly signed but expired capability. The test verifies a genuine local token first, then signs an expired variant with the **local Docker Storage** secret in memory. That secret, URLs and credentials are never printed or persisted by the probe. This is a local fixture, not a production signing mechanism.

Observed compatibility details: this Storage version returns some missing-object/bucket and upload-limit failures as HTTP 400 with a more specific JSON error code/status. The client and probe distinguish these from successful responses. The command emits only fixed result labels and cleans its objects even after an assertion fails.

## Run locally

After the usual local Supabase setup, from the repository root:

```sh
uv run --directory apps/api --locked python ../../scripts/configure_storage.py
uv run --directory apps/api --locked python ../../scripts/smoke_local_storage.py
```

The first command verifies the application staging bucket and writes API-only local credentials. The second needs Docker and tests only `http://127.0.0.1:54321`. It refuses hosted endpoints. Existing `.env.storage` settings are preserved; a mismatched endpoint/bucket or invalid key fails with a safe message. No app process loads this file yet: M02b will wire the storage client only when media is configured.

Never copy the service key into the web app, a `NEXT_PUBLIC_` variable, browser JavaScript, an API response, Git, a job payload or a signed-link log. Supabase's service credential is privileged and bypasses Storage RLS; the application must check ownership and quota before invoking this adapter. A private bucket alone is not the complete authorization model. Hosted provisioning must also verify that no client RLS policies grant access to this staging bucket.

## M02b implementation contract

Complete the remaining parent acceptance criteria before marking M02 done:

- Add owner-scoped pending assets and immutable operation/object keys via Alembic, with reserved bytes, declared type/size, state and the latest capability expiry. Never accept an owner ID or storage path from the browser.
- Serialize reservations per account; enforce account bytes, asset count and in-flight limits under that lock. Reserve the **maximum storage-enforced input allowance** plus bounded derivatives, not only the client's declared bytes: the capability can upload up to the bucket limit before completion is called.
- Implement authenticated `POST /media/uploads` with an idempotency key. Replays must preserve the asset/key and reject different inputs. A reissued grant must extend its tracked expiry before returning the capability; signing failure must not release a reservation that might have a live grant.
- Implement authenticated `POST /media/{id}/complete`. Look up the owned asset, verify that exact object's server-reported size/type outside a SQL transaction, then lock/recheck state and atomically transition plus enqueue one processing job. Replays enqueue no duplicates. Cross-owner/guessed IDs, mismatched metadata, expired grants and quota races need real database/Storage tests with two accounts.
- Avoid holding database connections while awaiting Storage. Keep journal text saves independent. Retain reservations on uncertain provider outcomes rather than allocating the same capacity twice.
- Supabase signed upload links are valid for two hours and are bearer capabilities. They are not individually revocable through this adapter. **Do not delete an uploaded staging key or release its allowance while a grant can still recreate that key.** M03/M08 must coordinate retention, expiry and reconciliation. This refines the original-retention recommendation from R04.
- Keep failed/processing images unavailable for viewing; status and derivative download authorization belong to M03. Do not run queued photo jobs against the currently empty production handler registry.

Primary M02b files: `media/models.py`, `media/schemas.py`, `media/uploads.py`, `media/routes.py`, migration 0012, app configuration/registration and integration tests. Split schema/service and route/provider verification into separate commits if needed; retain all parent acceptance cases.

Sources: [signed upload lifetime and behavior](https://supabase.com/docs/reference/javascript/file-buckets-createsigneduploadurl), [upsert authorization](https://supabase.com/docs/reference/javascript/file-buckets-uploadtosignedurl), [official Storage REST API](https://supabase.github.io/storage/), [standard upload tradeoffs](https://supabase.com/docs/guides/storage/uploads/standard-uploads). A future UI should preserve retry state for larger photos; standard uploads above 6 MB can be less reliable than resumable uploads, so test the chosen flow on a real phone before claiming resilient mobile uploads.
