# M03: Private photo processing

October 1, 2026. **M03a isolated conversion, M03b worker publication and M03c authorized viewing/worker registration are implemented.** Photo UI and attachment flows remain M04 onward. Hosted rollout remains subject to R07 capacity and cache-policy verification.

1. **M03a — isolated conversion:** promote the R04 conversion path, enforce derivative byte limits, and run the native decoders in a credential-free, network-disabled Docker container with hard memory/CPU/process limits and a bounded lifetime/output stream. Files: `media/photos.py`, `media/photo_protocol.py`, `media/photo_sandbox.py`, decoder Dockerfile/build inputs, decoder tests and CI. Test orientation/metadata/HEIC, invalid inputs, transparency, deterministic output, output ceilings, actual container restrictions and forced time/memory termination. No journal/Storage credentials or host directories enter the decoder.
2. **M03b — worker publication:** bounded private source downloads, deterministic derivative keys, immutable/retry-safe writes, database publication fenced by the current job lease, explicit asset failure outcomes and crash recovery. Test partial publication, retries, stale workers and real Storage; retain originals/reservations under the M02 grant rules.
3. **M03c — private viewing:** owner-checked status and short-lived derivative links for ready assets only, generated API contracts, two-account/expiry tests, handler registration and local rollout. Upload UI remains M04 onward.

The converter container is an implementation detail of the existing media worker, not a new business service. Docker is already part of local development and CI. Production hosting must support these limits (R07); there is no unbounded fallback when Docker is unavailable. The API will not receive Docker access. The supervising worker is trusted to access Docker; the decoder never receives its socket, credentials, volumes or environment.

Sources: [Docker execution controls](https://docs.docker.com/engine/containers/run/), [memory and swap limits](https://docs.docker.com/engine/containers/resource_constraints), [Docker daemon security boundary](https://docs.docker.com/engine/security/). Disabling networking, dropping capabilities and using an unprivileged user reduce exposure; containers are not a guarantee against every native-code or kernel vulnerability.

## M03a delivered

`photos.py` promotes the proven R04 path into application code: restricted JPEG/PNG/WebP/HEIF decoding, complete primary-image decode, HEIF container-length validation, EXIF orientation, ICC-to-sRGB conversion, transparent-pixel flattening onto white, no upscaling, and reconstruction from pixels to discard metadata. It adds explicit 5 MiB JPEG and 512 KiB WebP output ceilings. Invalid content, dimensions, profiles and output limits produce fixed reason codes rather than native exception text. Palette/grayscale PNG transparency is handled, and CMYK/L profiles are transformed from their original color mode.

`photo_protocol.py` defines bounded input/output data and validates the decoder response without importing native image libraries into the supervisor. Input is at most 20 MiB. The source may have at most 50 million pixels and a 10,000-pixel edge. Output is a JPEG with a 2048-pixel maximum edge and a WebP thumbnail with a 480-pixel maximum edge. The response envelope is capped at 8 MiB, covering base64 expansion; malformed dimensions, format names, encodings and file signatures are rejected. Returned byte fields are excluded from object representations.

`PhotoSandbox` resolves the locally built image to an immutable image ID, checks Docker resource support and creates one unprivileged container per photo. It uses the explicit local Windows named pipe or Linux Unix socket; it does not follow an ambient remote Docker context. Docker must already be running with Linux containers, and the image must already be built. There is no implicit pull or unsandboxed fallback.

The container has no network, host bind mounts, application credentials, Docker socket or writable root filesystem. It drops Linux capabilities, prohibits new privileges and core dumps, disables container logs and IPC, and limits memory to 768 MiB with no swap, one CPU and 32 processes. Input and results travel only through bounded pipes. The API never invokes this adapter; M03b will call it from the separate trusted worker. Native libraries are an optional `photo-decoder` runtime extra; ordinary API installation does not require them. Existing development installations retain them for fixtures and regression tests.

The supervisor permits 20 seconds for execution. A separate `timeout --signal=KILL 20s` inside the image bounds a decoder even if its supervisor disappears. Creation/removal each have their own ten-second control-command timeout, so the total operation is longer than the decode deadline. Cleanup kills the attachment and removes only that call's UUID-named container. The output-flood test initially caught blocked removal caused by an attached stream; stopping the CLI attachment before removing the container fixed it. A supervisor/daemon crash can leave a stopped container requiring later housekeeping; no photo files or decoder logs are persisted in it.

`build_photo_decoder.py` sends only the Dockerfile, two decoder source files and generated requirements to Docker. It never uses the repository root as build context. The Python base image is pinned by digest. Wheel versions and hashes come from the committed `uv.lock`; source distributions are disabled. No new decoder dependency version was introduced. Rebuild the image and restart future worker processes when decoder code or its lockfile changes.

## Verification

- The full local API/database suite passed **210 tests** with the sandbox enabled; the existing real-Storage flow remains a separately run opt-in test. Two additional CPU-capability rejection cases were then added and verified with the affected sandbox suite. The retained API suite has **212 cases plus the separate real-Storage case**.
- The existing sixteen JPEG/HEIC orientation cases and seven rejection cases now exercise both experimental and production converters. Thirteen additional cases cover alpha flattening, deterministic results, derivative byte ceilings, malformed decoder responses and resizing. Seven unit cases verify fail-closed container capability checks and input rejection before launching a decoder.
- Seven real Linux-container cases, launched from Windows Docker Desktop, verify JPEG/HEIC conversion, metadata removal and deterministic output, actual unprivileged/read-only/network/credential restrictions, enforced cgroup limits, kernel termination under memory pressure, excessive-output termination, the host deadline and the independent container deadline. Temporary probe images are removed and successful/error calls leave no running decoder containers.
- Ruff, formatting, mypy, API packaging, Python dependency audit and tracked/browser secret checks pass. CI builds the decoder and runs the full API suite with real container tests enabled. API routes/contracts, database schema and frontend behavior are unchanged by M03a.

## Reproduce

From `apps/api` with Docker running in Linux-container mode:

```sh
uv run --locked python ../../scripts/build_photo_decoder.py
```

Set `WINE_JOURNAL_TEST_PHOTO_SANDBOX=1` for the test process, then run:

```sh
uv run --locked python ../../scripts/run_api_tests.py
```

For a focused sandbox run, use `uv run --locked pytest tests/integration/test_photo_sandbox.py -q`. Only synthetic fixtures are used. The M03a/M03b slices kept uploads disabled; M03c adds the registered handler and opt-in setup described in the [media README](../apps/api/src/wine_journal/media/README.md).

## M03b delivered

`Storage.download` checks the source's stored identity, size, MIME type and ETag before and after a bounded authenticated read. It rejects redirects, compressed responses, changed headers and bodies outside the declared length. `put_derivative` uses immutable writes and reads the object back to verify the exact expected bytes, including after an uncertain upload response. Existing different bytes fail closed. User upload capabilities still authorize only staging paths.

`PhotoPublisher` loads owned work under account → job → asset locks, releases the transaction before Storage/decoder I/O, and renews its lease between bounded steps. It checks private-bucket configuration before reading. Publication locks/rechecks ownership, active account, current token and lease, then records READY only after both outputs are verified. A final database-clock check rolls back changes if the lease expired during the transaction. Stale workers can leave only the same two immutable, private objects; they cannot make an asset ready or overwrite another worker's result.

Migration `0013_photo_publication` adds immutable processing version 1, bounded output sizes/dimensions, SHA-256 hashes and fixed failure codes. READY requires both outputs' metadata and the source identity. Runtime grants permit lifecycle updates only; ownership, paths, version and reservation sizes remain immutable. Output keys are `photos/{asset UUID}/v1/display.jpg` and `thumbnail.webp`. Changing the conversion recipe requires an explicit versioning decision; do not silently replace the decoder recipe for existing pending v1 jobs.

Content rejection records an asset failure and successfully acknowledges the processing decision. Infrastructure failures retry with the existing bounded queue policy. Terminal errors and final expired leases atomically fail only matching owned PROCESSING assets; they never demote READY. If the process dies after publishing but before acknowledging, its successor skips conversion and acknowledges the existing result. A final-attempt crash after READY may leave a FAILED queue row with a READY asset; asset state remains authoritative for future viewing.

Original objects, grant expiries, unresolved signing holds and the full 25.5 MiB reservation are retained. M08 owns safe reclamation. No status/viewing route, production handler registration or frontend behavior is added by M03b.

Verification includes adapter limit/identity/conflict/uncertain-response tests and disposable-Postgres cases for partial output recovery, stale tokens, expiry during the final write, disabled accounts, foreign ownership, exhausted retries, final lease expiry, crash-after-ready replay, constraints/grants and reversible migration. Real Supabase + Docker cases cover JPEG and HEIC with an interruption before the thumbnail, byte-identical reuse of the first output, metadata removal, orientation, private access and preserved sources. The HEIF fixture was corrected to serialize EXIF bytes: passing a Pillow Exif object did not encode the intended container rotation. Production conversion code was unchanged.

CI builds the isolated decoder in the browser/Storage job as well as the API job. The real provider test uses UUID temporary buckets and a disposable database; it does not touch journal files. For the full pipeline test, set `WINE_JOURNAL_TEST_STORAGE=1` and run `uv run --locked python ../../scripts/run_api_tests.py tests/integration/test_media_storage_flow.py -q --tb=short` from `apps/api` with local Supabase and the decoder image available.

The full local suite passed **253 tests**, with both real Storage and real sandbox checks enabled. Ruff, format, mypy (98 files), packaging, dependency audit, unchanged OpenAPI generation and tracked/browser secret checks passed. Local migration 0013 preserved the entry/occasion counts and left uploads disabled. Known non-failing warnings concern Starlette/httpx deprecations and Windows pytest cache permissions.

### M03b implementation sequence

1. Extend `integrations/storage.py` with bounded authenticated reads and immutable derivative writes. Verify identity/size/type before and after reads; reconcile uncertain writes by reading back the expected bytes. Unit cases cover limits, redirects, changed objects, interrupted writes and conflicts; the real Storage flow verifies provider behavior.
2. Add migration `0013` and model fields for processing version, derivative sizes/dimensions/hashes and fixed failure codes. Implement `media/photo_processing.py` around short, lease-fenced SQL transactions, with no open SQL connection during Storage or decoding. Extend queue terminal failure handling so an exhausted or abandoned final attempt cannot strand an asset in PROCESSING. Exercise retries, crashes, stale claims, disabled accounts and ownership with disposable PostgreSQL.
3. Run the actual private Storage → isolated decoder → private derivatives path, including an interruption between output writes. Update CI and record evidence. Keep source/grant reservations, upload feature flag and production handler registration unchanged until M03c.

Storage contract references: [authenticated private downloads](https://supabase.com/docs/guides/storage/serving/downloads), [immutable standard uploads](https://supabase.com/docs/guides/storage/uploads/standard-uploads). Derivative paths are server-generated and versioned; upload capabilities remain restricted to staging paths. No provider credentials, capabilities, source bytes or exception bodies enter job payloads or logs.

## Remaining acceptance

Originals and the 25.5 MiB reservation remain subject to the M02 capability-retention rules; safe cleanup remains M08. Recent physical-iPhone/HDR visual checks and actual hosting capacity remain R04/R07/UI follow-ups.

## M03c delivered

The API exposes owner-only photo status and POST-issued viewing capabilities for READY display/thumbnail derivatives. Clients cannot choose source paths, original variants, owners or expiry. Unknown and cross-account identifiers return the same 404. Status requires an active account but no Storage availability. Viewing checks readiness and account state before and after provider I/O, without holding a database connection across signing. Both responses are no-store, status failures use a generic public code, and capability strings are omitted from object representations and logs. OpenAPI and generated frontend types include the new contract.

The Storage adapter signs exact derivative paths for 120 seconds and validates the returned origin-relative URL, token path and bounded expiry before returning it. Signing checks that the configured bucket is still private. The real test uses genuine provider signatures with a two-second TTL, warms the URL, then verifies rejection after expiry. It also rejects token reuse for a different derivative or the source file. These tests do not inspect signing secrets or forge provider tokens.

Provider behavior matters: Storage v1.72.1's signed route emits `Expires` based on token expiry instead of the object's Cache-Control header. The regression test initially expected no-store on that route; inspection of the installed renderer and signed-object handler established the actual contract. New derivative uploads carry no-store, which is verified on authenticated reads; API JSON remains no-store. Hosted CDN revocation is a separate deployment gate, because [Supabase documents cached signed responses outliving token expiry](https://supabase.com/docs/guides/storage/cdn/smart-cdn#signed-urls-and-cdn-caching). Do not promise immediate revocation of issued links or downloaded bytes. The upload UI should use nonpersistent fetches and clear private media on sign-out.

The separate worker now explicitly registers the photo publisher, validates private Storage and Docker/image availability before claiming, and closes resources on success or startup failure. Disabled media means no job claims, rather than failing queued photos against an empty handler registry. Six startup cases check registration, configuration failures, disabled mode and cleanup. Nine database/API cases verify status/view ownership, all four states, invalid requests, signing failures, expiry and account/state races; twelve adapter cases verify signed-response validation. Both real JPEG/HEIC flows recover an interrupted publication through the actual CLI worker, using only the disposable runtime/Storage credentials in its environment.

M03c verification: **280 tests passed** in the complete local API/database suite with Storage and Docker checks enabled. Ruff, formatting, mypy (102 files), API packaging, Python dependency audit, tracked/browser secret checks and generated frontend type checking passed. OpenAPI and TypeScript contracts were regenerated. Known non-failing warnings remain Starlette/httpx deprecations and Windows pytest-cache permissions.

Local rollout on October 1: started the validated worker in a hidden process, enabled media only in ignored `apps/api/.env`, and restarted only the identified API process. The API liveness route and My Wines preview return 200; new media routes require authentication. Entry and occasion counts were checked before/after and preserved. The checked-in example retains `false`. No new migration follows 0013, no data reset was performed, and no frontend upload/gallery controls were added. M03 is complete; M04 is next.
