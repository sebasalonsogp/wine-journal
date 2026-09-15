# Authentication setup and implementation boundary

The selected methods are email verification codes plus Google, Apple and Facebook through Supabase Auth. [ADR 0006](decisions/0006-authentication-and-public-repository.md) records the decision. Email-code sign-in, web session refresh/recovery, account switching, and sign-out are implemented and tested locally. The OAuth entry/callback and conditional buttons are implemented; real social-provider flows require registered applications and live verification before activation.

## Values and where they belong

| Value | Owner / location |
| --- | --- |
| Supabase project URL and publishable key | Public project configuration, generated into ignored web `.env.local`; used by server auth handlers. The web config rejects legacy/service-role JWT keys. |
| API database URL | `WINE_JOURNAL_DATABASE_URL` in ignored API `.env` or server secret store; `wine_api` role |
| Migration database URL | `WINE_JOURNAL_MIGRATION_DATABASE_URL` in ignored `.env.migrations` or migration-runner secret store; never loaded by the API |
| OAuth client IDs | Registered provider application plus Supabase provider configuration; not an identity credential themselves |
| OAuth client secrets / Apple signing material | Provider/Supabase secret configuration only; never Git, browser bundles or `NEXT_PUBLIC_*` |
| Local ES256 signing key | Generated `supabase/signing_keys.json`, ignored; API reads only the public JWKS endpoint |
| Supabase admin/secret/service-role key | No normal API or web-sign-in use; future administration requires a separate explicitly scoped process |

`.env` is a local configuration mechanism, not encryption or a hosted secret vault. Production environment values belong in the hosting/provider secret stores with restricted access. Do not paste credentials into chat or GitHub issues.

## Provider activation checklist for F05/F06

| Provider | Required setup |
| --- | --- |
| Email code | Reviewed templates and redirect/site configuration; production SMTP/delivery configuration; bounded resend/verification limits and abuse protection. The local Mailpit inbox does not prove hosted delivery. |
| Google | Register the OAuth web client, configure consent/scopes and the exact Supabase callback from its dashboard, then store client ID/secret in Supabase. |
| Apple | Configure Sign in with Apple identifiers/domains/callbacks and the required signing material/client secret. Document renewal before enabling it. |
| Facebook | Register the app, configure Facebook Login and exact allowed callback/domain settings, and verify the permissions/provider review requirements for the intended audience. |

Register only the intended local/staging/production destinations; no wildcard or caller-supplied redirect host. The Supabase provider callback and the web app's post-auth callback are different URLs. The web implementation must validate return destinations against known internal routes, use the SDK's PKCE/state/nonce protections, and keep an interrupted capture separate from credentials.

`WINE_JOURNAL_OAUTH_PROVIDERS` is a comma-separated allowlist of `google,apple,facebook`. It defaults to empty and controls both visible buttons and accepted OAuth initiation requests. Enable a provider only after its corresponding integration is configured and verified.

## Web session boundary

`@supabase/ssr` runs only inside request-scoped server handlers. Its session and PKCE cookies are HTTP-only, SameSite=Lax, host-scoped, and Secure for HTTPS site URLs. Local HTTP uses non-Secure cookies. This deliberately differs from Supabase's usual browser SDK setup: our browser never runs a Supabase client or receives a refresh token. All cookie writes occur in Route Handlers, so there is no refresh middleware or Server Component cookie mutation.

`POST /auth/session` verifies the user through Supabase and returns only an access token, expiry, verified subject/email, and public API URL. An instance-scoped client keeps that token in memory and calls FastAPI directly through generated types. Account results use TanStack Query; tokens do not. One concurrent refresh is shared and a rejected API request retries at most once. Network/provider failures show a retry state; an invalid refresh ends the browser session without looping. Sign-out revokes the current provider session and clears cookies/caches; other tabs clear their private state through BroadcastChannel. Restored browser-back pages reload before showing private account content. No owned journal drafts exist yet; future draft storage must join this cleanup boundary.

Auth mutations require the exact configured Origin, JSON bodies capped at 4 KiB, and reject cross-site Fetch Metadata. Return destinations are a fixed set of internal routes. OAuth uses the SDK's PKCE verifier in HTTP-only cookies, a configured callback origin, and a short-lived internal return-path cookie. Every auth response is `private, no-store`; callback query logging and referrers are disabled. Current CSP blocks framing, objects and foreign base URLs; a nonce-based script policy and hosted edge/SMTP abuse limits remain deployment work, not claims of this checkpoint.

The private shell is a client navigation guard; FastAPI remains the authorization boundary. Private account data is never rendered into static HTML or a shared server cache. An already issued JWT can remain valid at FastAPI until expiry after sign-out; logout revokes refresh capability and clears the app's browser state, not every copied bearer token. Hosted token lifetimes/revocation requirements must be reviewed before release.

Use Supabase's identity-linking rules; do not merge app users by a matching submitted email. Linking additional providers to an existing account and recovery after losing access need deliberate user journeys and tests, not administrative shortcuts.

## Current API behavior

Guests receive 401 on `/api/v1/me`. A valid user token can `POST {}` to create/reuse its own account, then `GET` it without side effects. `GET` before bootstrap returns 404. Disabled identities return 403 for both operations. The API validates signature/algorithm/issuer/audience/expiry/subject and never accepts owner identity from the request body. Neither route returns the user's email, OAuth tokens or provider response.

References: [Supabase email OTP](https://supabase.com/docs/guides/auth/auth-email-passwordless), [Google setup](https://supabase.com/docs/guides/auth/social-login/auth-google), [Apple setup](https://supabase.com/docs/guides/auth/social-login/auth-apple), [Facebook setup](https://supabase.com/docs/guides/auth/social-login/auth-facebook).
