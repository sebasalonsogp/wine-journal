# M03: Private photo processing

September 30, 2026. **M03a isolated conversion is implemented and verified locally.** M03b/M03c remain; the parent stays open and uploads remain disabled until all are delivered.

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

For a focused sandbox run, use `uv run --locked pytest tests/integration/test_photo_sandbox.py -q`. Only synthetic fixtures are used. Keep `WINE_JOURNAL_MEDIA_UPLOADS_ENABLED=false`; no production job handler or viewing endpoint has been registered yet.

## Remaining acceptance

### M03b implementation sequence

1. Extend `integrations/storage.py` with bounded authenticated reads and immutable derivative writes. Verify identity/size/type before and after reads; reconcile uncertain writes by reading back the expected bytes. Unit cases cover limits, redirects, changed objects, interrupted writes and conflicts; the real Storage flow verifies provider behavior.
2. Add migration `0013` and model fields for processing version, derivative sizes/dimensions/hashes and fixed failure codes. Implement `media/photo_processing.py` around short, lease-fenced SQL transactions, with no open SQL connection during Storage or decoding. Extend queue terminal failure handling so an exhausted or abandoned final attempt cannot strand an asset in PROCESSING. Exercise retries, crashes, stale claims, disabled accounts and ownership with disposable PostgreSQL.
3. Run the actual private Storage → isolated decoder → private derivatives path, including an interruption between output writes. Update CI and record evidence. Keep source/grant reservations, upload feature flag and production handler registration unchanged until M03c.

Storage contract references: [authenticated private downloads](https://supabase.com/docs/guides/storage/serving/downloads), [immutable standard uploads](https://supabase.com/docs/guides/storage/uploads/standard-uploads). Derivative paths are server-generated and versioned; upload capabilities remain restricted to staging paths. No provider credentials, capabilities, source bytes or exception bodies enter job payloads or logs.

M03b must download the expected immutable source with byte/time bounds, validate source identity, publish deterministic private derivatives, recover interrupted publication and fence asset updates against stale job leases. M03c must authorize ready-only status/viewing, verify link expiry against real Storage and register the handler before enabling upload endpoints. Originals and the 25.5 MiB reservation remain subject to the M02 capability-retention rules; this increment deletes neither. Recent physical-iPhone/HDR visual checks and actual hosting capacity remain R04/R07/UI follow-ups.
