"""Provision this project's local private bucket without exposing or replacing credentials."""

import json
import os
import shutil
import subprocess
import sys

from configure_local import ROOT, write_new
from pydantic import SecretStr

from wine_journal.integrations.storage import Storage, StorageSettings


def local_credentials() -> tuple[StorageSettings, SecretStr]:
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
    if status["API_URL"] != "http://127.0.0.1:54321":
        raise ValueError("Only this project's loopback Storage is allowed.")
    return (
        StorageSettings(
            url=status["API_URL"] + "/storage/v1",
            service_key=SecretStr(status["SERVICE_ROLE_KEY"]),
            bucket="wine-journal-staging",
        ),
        SecretStr(status["ANON_KEY"]),
    )


def main() -> None:
    settings, _ = local_credentials()
    path = ROOT / "apps/api/.env.storage"
    if path.exists():
        existing = StorageSettings.model_validate({})
        if existing.url != settings.url or existing.bucket != settings.bucket:
            raise ValueError("Existing storage configuration differs; file preserved.")
        # CLI status can mint a fresh legacy token on each call. Preserve the existing
        # credential and prove it still works instead of comparing token bytes.
        settings = existing
    storage = Storage(settings)
    try:
        storage.ensure_private_bucket()
    finally:
        storage.close()
    if not path.exists():
        write_new(
            path,
            f"WINE_JOURNAL_STORAGE_URL={settings.url}\n"
            f"WINE_JOURNAL_STORAGE_SERVICE_KEY={settings.service_key.get_secret_value()}\n"
            f"WINE_JOURNAL_STORAGE_BUCKET={settings.bucket}\n",
        )
    print("Local private bucket verified. Storage credentials remain in the ignored API-only file.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit("Storage setup failed; existing configuration preserved and details withheld.")
