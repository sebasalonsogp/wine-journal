# Authentication routes

Thin sign-in/callback/session routes delegate to `features/auth`. Email-code sign-in is connected; OAuth entry/callback is available only for configured providers. Cookie-backed handlers require the configured Origin, validate inputs, and never cache session responses. Business APIs remain in FastAPI.
