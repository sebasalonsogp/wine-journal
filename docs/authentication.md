# Authentication setup and implementation boundary

The selected methods are email verification codes plus Google, Apple and Facebook through Supabase Auth. [ADR 0006](decisions/0006-authentication-and-public-repository.md) records the decision. The local email-code/API path is tested; the web sign-in UI, session refresh/callback implementation and real social-provider flows are not yet built.

## Values and where they belong

| Value | Owner / location |
| --- | --- |
| Supabase project URL and publishable key | Public project configuration; currently generated into ignored web `.env.local` for the upcoming client |
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

`WINE_JOURNAL_OAUTH_PROVIDERS` is reserved configuration for F05 (comma-separated `google,apple,facebook`). It currently enables no UI. Show a provider only after its corresponding integration is configured and verified. An inactive button must not suggest that an unconfigured login works.

Use Supabase's identity-linking rules; do not merge app users by a matching submitted email. Linking additional providers to an existing account and recovery after losing access need deliberate user journeys and tests, not administrative shortcuts.

## Current API behavior

Guests receive 401 on `/api/v1/me`. A valid user token can `POST {}` to create/reuse its own account, then `GET` it without side effects. `GET` before bootstrap returns 404. Disabled identities return 403 for both operations. The API validates signature/algorithm/issuer/audience/expiry/subject and never accepts owner identity from the request body. Neither route returns the user's email, OAuth tokens or provider response.

References: [Supabase email OTP](https://supabase.com/docs/guides/auth/auth-email-passwordless), [Google setup](https://supabase.com/docs/guides/auth/social-login/auth-google), [Apple setup](https://supabase.com/docs/guides/auth/social-login/auth-apple), [Facebook setup](https://supabase.com/docs/guides/auth/social-login/auth-facebook).
