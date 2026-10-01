# Security and local configuration

The repository is public. GitHub secret scanning and push protection were enabled on September 14, 2026. Gitleaks also checks complete Git history in CI, with redacted output. These checks detect known patterns; they do not prove that arbitrary text or uploaded images contain no private information.

## Configuration boundary

- Commit `.env.example` files containing variable names, comments and safe placeholders only. Real values belong in ignored local environment files or the deployment platform's secret store.
- Everything prefixed `NEXT_PUBLIC_` is public and may be embedded in JavaScript. Only deliberately public URLs, feature configuration and Supabase publishable keys qualify. Database credentials, JWT signing keys, Supabase secret/service-role keys and OAuth client secrets never belong there.
- The Python API uses `WINE_JOURNAL_` variables. Runtime and migration database credentials are separate. Never log a Settings object, connection URL, Authorization header, session, OTP, signed URL or provider response containing credentials.
- Social-provider client secrets live in Supabase's provider configuration (or ignored local Supabase variables), not the web application. No provider secret is needed by the browser or journal API.
- Generate local test credentials; do not reuse hosted credentials. CI databases and identities are disposable. Fork pull requests must not require deployment secrets or access to personal data.
- Keep uploads, backups, local signing keys, service-account files and diagnostic reports out of Git. Check staged files explicitly: `.gitignore` does not protect an already tracked file or a forced add.

## Before publishing changes

Inspect the staged filenames and diff. Run Gitleaks 8.30.1 with redaction:

```sh
gitleaks git --redact=100 --no-banner --log-opts=--all .
git diff --cached --no-ext-diff | gitleaks stdin --redact=100 --no-banner
```

The sole initial allowlist is an exact prose value in one architecture document. Do not add blanket exclusions for examples, tests, environment files or generated design exports. Review findings individually without copying credential values into issues, logs or chat.

If a real secret reaches GitHub, revoke/rotate it first, assess its access and then clean up the tracked file/history as appropriate. Deleting a line does not invalidate a credential.

## Current trust boundaries

Untrusted browsers and future native clients send access tokens to FastAPI. The API verifies the configured issuer/signature/claims and authorizes each owned record. Only the migration role can change the application schema; the API runtime cannot administer roles or read provider-owned Auth tables. Supabase's Data API roles receive no application-table privileges. SQLAlchemy does not automatically apply a browser user's RLS identity.

The email inbox and database in the local Supabase stack are development tools. They must remain local and contain test data only. No hosted deployment, production email delivery or social-provider registration is implied by starting this stack.

References: [Gitleaks](https://github.com/gitleaks/gitleaks), [Supabase API keys](https://supabase.com/docs/guides/api/api-keys), [Next.js environment variables](https://nextjs.org/docs/app/guides/environment-variables).
