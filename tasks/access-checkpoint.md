# Access foundation checkpoint

September 14, 2026. This is the first backend checkpoint within Phase 1, not the finished sign-in experience or private journal.

## Implemented

- Public-repository protections: GitHub secret scanning/push protection, checksum-pinned Gitleaks CI, narrow reviewed prose false-positive rule, and a tested guard against forced credential-file additions.
- F01 direction: email codes plus Google/Apple/Facebook selected; local code templates, asymmetric local signing and provider setup boundaries documented in ADR 0006.
- F02 data boundary: limited runtime/migration roles, unexposed app schema, first accounts migration, model parity, disposable Postgres runner and database CI configuration.
- F03 identity verification: asymmetric JWTs, configured issuer/audience/role, required expiry/subject, bounded key retrieval/cache/cooldown, generic failures.
- F04 account API: idempotent `POST /me`, read-only `GET /me`, two-account isolation, disabled-account denial, consistent errors/request IDs, no-store responses and typed OpenAPI.

F02 was split into configuration/model/migration work and provisioning/integration verification; F03 and F04 remain separate slices. Dependencies were added only for these behaviors. No journal/media/public-feed schemas were generated in advance.

## Verification evidence

- Full API tests run against a fresh Postgres 17 container with generated credentials; migration downgrade/upgrade, constraints, role denials and concurrent account creation pass.
- Actual local Supabase email-code flow passed for two synthetic accounts: new-user login, single-use-code rejection on replay, real signed JWT verification and repeat account bootstrap/read. No codes/tokens were displayed or committed.
- Ruff, formatting, strict Python types, package build and generated OpenAPI/type checks are run for this checkpoint. Locked Python dependency audit reported no known vulnerabilities.
- Full history scan passed with the exact reviewed documentation false-positive exception. The staged diff and tracked-file checks are required again before publishing.
- Local startup guard was exercised on the real host: it detected non-loopback Supabase ports and stopped the stack, retaining volumes. Unit tests also cover allowed loopback, non-loopback and inspection-failure cleanup.

[GitHub CI](https://github.com/sebasalonsogp/wine-journal/actions/runs/34917468032) passed for code commit `965ba22`: all 38 API tests, web checks/build and generated contract checks. [Secret checks](https://github.com/sebasalonsogp/wine-journal/actions/runs/34917468120) also passed. F01/F03/F04 are complete; F02 remains partial until safe persistent local Supabase startup is usable. The [pull request](https://github.com/sebasalonsogp/wine-journal/pull/1) contains the reviewed commits.

## Remaining work

F05–F07 still own the web sign-in shell, secure session/callback/recovery behavior, provider buttons and browser CI. Social providers need registered apps/credentials and live verification; none is claimed operational. No hosted services or real email delivery were configured.

The current Docker Desktop/Supabase network-binding mismatch must be resolved before leaving the full local stack running; see [local setup](../supabase/README.md). The isolated API test runner uses an explicit loopback mapping and remains usable. Synthetic identities remain only in retained local volumes. Existing upstream test-client deprecations and a Windows pytest-cache ACL warning are recorded; checks are not disabled to hide them.

Provider/media feasibility tasks R01–R07 and the journal itself remain pending. The next implementation target is F05 after confirming a usable local Auth environment; the first useful journal remains J04.
