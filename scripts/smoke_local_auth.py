"""Exercise email OTP and the real API identity boundary using local Supabase only."""

import re
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from wine_journal.core.config import Settings
from wine_journal.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    settings = Settings()
    if settings.auth_issuer != "http://127.0.0.1:54321/auth/v1":
        raise ValueError("Smoke test only supports the local Supabase issuer.")
    web = dotenv_values(ROOT / "apps/web/.env.local")
    key = web.get("SUPABASE_PUBLISHABLE_KEY")
    if not key or web.get("SUPABASE_URL") != "http://127.0.0.1:54321":
        raise ValueError("Run configure_local.py first; hosted projects are refused.")
    with httpx.Client(timeout=10) as auth, TestClient(create_app(settings)) as api:
        identities = []
        for _ in range(2):
            mailbox = "wine-smoke-" + uuid4().hex[:12]
            email = mailbox + "@example.test"
            requested = auth.post(
                settings.auth_issuer + "/otp",
                headers={"apikey": key},
                json={"email": email, "create_user": True},
            )
            assert requested.status_code == 200, "Local OTP request failed."
            deadline = time.monotonic() + 15
            while True:
                inbox = auth.get("http://127.0.0.1:54324/api/v1/messages").json()
                messages = [
                    item
                    for item in inbox["messages"]
                    if any(recipient["Address"] == email for recipient in item["To"])
                ]
                if messages:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("No message in the local development inbox.")
                time.sleep(0.2)
            message = auth.get(f"http://127.0.0.1:54324/api/v1/message/{messages[0]['ID']}").json()
            code = re.search(r"\b\d{6}\b", message["Text"] or message["HTML"])
            assert code is not None, "Local email did not contain a six-digit code."
            verified = auth.post(
                settings.auth_issuer + "/verify",
                headers={"apikey": key},
                json={"email": email, "token": code[0], "type": "email"},
            )
            assert verified.status_code == 200, "Local OTP verification failed."
            token = verified.json()["access_token"]
            headers = {"Authorization": "Bearer " + token}
            assert api.get("/api/v1/me", headers=headers).status_code == 404
            saved = api.post("/api/v1/me", headers=headers, json={})
            assert saved.status_code == 200, "The real signed token was not accepted by the API."
            assert api.get("/api/v1/me", headers=headers).json() == saved.json()
            assert api.post("/api/v1/me", headers=headers, json={}).json() == saved.json()
            identities.append(saved.json()["id"])
            replay = auth.post(
                settings.auth_issuer + "/verify",
                headers={"apikey": key},
                json={"email": email, "token": code[0], "type": "email"},
            )
            assert replay.status_code != 200, "OTP must be single-use."
        assert identities[0] != identities[1]
        assert api.get("/api/v1/me").status_code == 401
    print(
        "PASS: two real email-code sign-ins, single-use codes, signed JWT verification, "
        "read-only lookup and idempotent separate accounts. No credentials displayed."
    )
    print("Two synthetic test identities remain in local Supabase; no external email was sent.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(f"Local auth smoke failed ({type(exc).__name__}); inspect the local setup.")
