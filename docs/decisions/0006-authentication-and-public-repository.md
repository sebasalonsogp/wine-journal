# ADR 0006: Managed multi-provider identity and public-repository safeguards

Status: Accepted and implemented for local email/web sessions, September 14, 2026. Live social-provider activation remains external setup work.

## Context

The user made the repository public and explicitly requested careful handling of environment variables and secrets. They selected direct email-code sign-in plus Google, Apple and Facebook, rather than limiting the eventual experience to one method.

## Decision

Use Supabase Auth for email OTP and supported OAuth providers. The application does not implement a password database or its own OAuth token issuer. All methods resolve to a Supabase subject; FastAPI maps the verified `(issuer, subject)` to one internal application UUID. Never identify users by a submitted email address or a Google/Facebook/Apple ID in journal requests. Do not implement automatic account merging ourselves.

Begin with a real local email-code path: six digits, ten-minute expiry, provider-enforced resend/verification limits, one-time verification and no password reset flow. Returning users repeat sign-in; losing email access is not recoverable by an unauthenticated journal endpoint. An expired/invalid code must allow a new request, and cancelling sign-in must retain only the explicit public capture intent. Guest browsing does not create an account.

The web sign-in slice must implement the Google, Apple and Facebook choices behind verified provider configuration. No fake working buttons, embedded client secrets, or raw provider errors. Registered apps, permitted callback URLs, appropriate scopes and provider-specific credentials are prerequisites for enabling each option. Further providers require an explicit selection; “etc.” does not authorize integrating every identity provider.

Preserve the architecture's verified-token API boundary. The browser session-storage/refresh and callback implementation is the next F05/F06 slice: keep refresh credentials in secure HTTP-only cookies through narrowly scoped web auth plumbing, protect cookie-backed state changes against CSRF, and keep journal business rules in FastAPI. A thin web session bridge may provide short-lived access credentials in memory for direct API calls; it must not introduce another business API or store sessions in localStorage. Native clients will use platform-appropriate secure storage and the same API.

FastAPI accepts only the configured Supabase issuer, `authenticated` audience/role, valid UUID subject and unexpired asymmetric ES256/RS256 signatures. Public signing keys are cached for five minutes, with a thirty-second refresh cooldown; no legacy HMAC secret is distributed to the API. No private signing key, secret/service-role API key or OAuth secret is required by FastAPI for normal account verification.

## Public repository and local data

GitHub secret scanning and push protection are enabled. CI also runs checksum-pinned Gitleaks with redacted output and rejects tracked local credential/private-data files. Keep only safe environment templates in Git. Local role passwords and signing keys are generated; runtime and migration connection files are separate. API configuration masks credentials in representations/errors and rejects administrative runtime roles.

Alembic owns the unexposed `app` schema. `wine_migrator` owns its DDL; `wine_api` receives only required schema usage and table operations. Provider Data API roles have no app grants. The local provisioning administrator needs SET membership in the migration role to assign ownership; the API role never receives that membership. Tests use a new disposable Postgres container with random credentials, not personal data or long-lived GitHub credentials.

## Evidence and limits

See [access checkpoint](../../tasks/access-checkpoint.md) and [web access checkpoint](../../tasks/web-access-checkpoint.md) for verification. Local email OTP, the web UI/session lifecycle and the API boundary have been exercised; actual social-provider callbacks have not. Hosted email delivery, provider registrations, production rate limits and deployment remain explicit setup work. Docker Desktop's separate localhost-default setting resolved the local binding issue; the startup wrapper still stops the stack if it cannot verify loopback bindings.

References: [email OTP](https://supabase.com/docs/guides/auth/auth-email-passwordless), [JWT verification](https://supabase.com/docs/guides/auth/jwts), [Google](https://supabase.com/docs/guides/auth/social-login/auth-google), [Apple](https://supabase.com/docs/guides/auth/social-login/auth-apple), [Facebook](https://supabase.com/docs/guides/auth/social-login/auth-facebook).
