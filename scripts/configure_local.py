"""Create ignored local credential files from the running Supabase stack."""

import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def write_new(path: Path, content: str) -> None:
    # Exclusive creation prevents overwriting user configuration. POSIX mode is owner-only;
    # Windows uses the user's existing profile/workspace ACLs.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
        output.write(content)


def main() -> None:
    npx = shutil.which("npx.cmd" if os.name == "nt" else "npx")
    if npx is None:
        raise RuntimeError("Node.js and npx are required.")
    result = subprocess.run(
        [npx, "--yes", "supabase@2.117.0", "status", "-o", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    status = json.loads(result.stdout)
    admin = make_url(status["DB_URL"])
    if admin.host not in {"127.0.0.1", "localhost", "::1"} or admin.port != 54322:
        raise ValueError("Expected this project's local Supabase database.")
    if status["API_URL"] != "http://127.0.0.1:54321":
        raise ValueError("Expected this project's local Supabase API.")
    files = {
        "wine_api": (ROOT / "apps/api/.env", "WINE_JOURNAL_DATABASE_URL"),
        "wine_migrator": (ROOT / "apps/api/.env.migrations", "WINE_JOURNAL_MIGRATION_DATABASE_URL"),
    }
    values = dict(os.environ)
    values["WINE_JOURNAL_ADMIN_DATABASE_URL"] = status["DB_URL"]
    for role, (path, variable) in files.items():
        if not path.exists():
            connection = admin.set(
                drivername="postgresql+psycopg", username=role, password=secrets.token_urlsafe(32)
            ).render_as_string(hide_password=False)
            content = f"{variable}={connection}\n"
            if role == "wine_api":
                content += f"WINE_JOURNAL_AUTH_ISSUER={status['API_URL']}/auth/v1\n"
            write_new(path, content)
        value = dotenv_values(path).get(variable)
        if not value:
            raise ValueError(
                "Existing configuration is missing its role connection; file preserved."
            )
        values[variable] = value
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/provision_database.py")],
        cwd=ROOT,
        env=values,
        check=True,
    )
    web = ROOT / "apps/web/.env.local"
    if not web.exists():
        public_key = status["PUBLISHABLE_KEY"]
        write_new(
            web,
            f"SUPABASE_URL={status['API_URL']}\n"
            f"SUPABASE_PUBLISHABLE_KEY={public_key}\n"
            "WINE_JOURNAL_API_URL=http://127.0.0.1:8000\n"
            "WINE_JOURNAL_SITE_URL=http://localhost:3000\n"
            "WINE_JOURNAL_OAUTH_PROVIDERS=\n",
        )
    print("Local environment files are ready. Existing files were preserved; no keys were printed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(
            f"Local configuration failed ({type(exc).__name__}); no credentials were displayed."
        )
