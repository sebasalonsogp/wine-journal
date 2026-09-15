# Web access checkpoint

September 14, 2026. F02 local startup and F05/F06 web access are implemented. F07's browser suite and CI job are implemented; the first fresh GitHub run is pending verification.

- Docker Desktop's separate localhost-default port setting resolved persistent local startup. The four Supabase published ports were inspected on `127.0.0.1`/`::1`; migration and real OTP/API smoke passed again.
- Email code request/verify, retry/recovery, account bootstrap/read, sign-out, and account switching run against real local Supabase and FastAPI. Social provider initiation/callback code is present behind configuration, but Google/Apple/Facebook are not activated or claimed live.
- The UI inherits the reviewed palette and navigation: Browse Wines first, then My Wines, Occasions, Guides, with My Wines the initial private destination. Account details identify the signed-in email. Empty states do not fabricate wines, occasions or public ratings.
- HTTP-only cookies hold refresh credentials. Short-lived access tokens stay in instance memory; no localStorage/sessionStorage. Origin/body checks, fixed internal return paths, no-store headers, safe errors and bounded refresh are verified. A browser test caught and now guards a cross-tab sign-out race.
- Five focused web unit tests pass. Three browser scenarios pass against the production build (the account-switch scenario was rerun after correcting its navigation wait). They include real refreshed/revoked sessions, two accounts, back navigation, keyboard use, axe and four viewport widths. Desktop/phone captures were visually inspected.
- TypeScript, ESLint, formatting, production build and Python lint/types pass. The browser scan checked 15 built JavaScript files against generated local database passwords/private signing material and found none. It complements the repository-wide secret scanner; it is not a proof against arbitrary unknown secrets.

No hosted SMTP, social-provider credentials, deployment, journal persistence, media or wine-data provider was configured. An issued API JWT may remain valid until expiry after sign-out; refresh revocation and local state clearing do not provide immediate bearer-token revocation. Production abuse limits, stricter script CSP and release-specific token policies remain explicit release work.

Next: first private journal slice J01–J04, retaining the independent provider/media feasibility lane. F07 is only marked complete after fresh browser CI passes.
