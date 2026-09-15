# auth

Sign-in, sign-out, session recovery, and returning to a preserved capture draft. UI guards aid navigation; FastAPI enforces access.

The email-code form, provider-configured OAuth entry/callback, HTTP-only server session handlers, and verified private shell are implemented. Route files only compose screens or export handlers. Shared HTTP/session and typed API transport live in `src/lib`; they never import product features. Google/Apple/Facebook still require external registration and live verification before enabling their buttons.

No private account content is server-rendered into a shared cache. The client shell verifies its session and reads/bootstraps the account through FastAPI, then renders children. Future private Server Components must add their own verified server access boundary; the shell is navigation UX, not API authorization.
