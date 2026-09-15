"""Check built browser assets against local private values without displaying them."""

import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    private_values: list[str] = []
    for filename, key in (
        (".env", "WINE_JOURNAL_DATABASE_URL"),
        (".env.migrations", "WINE_JOURNAL_MIGRATION_DATABASE_URL"),
    ):
        value = dotenv_values(ROOT / "apps/api" / filename).get(key)
        if not value:
            raise RuntimeError("Local database configuration is required for this check.")
        password = make_url(value).password
        if password:
            private_values.append(password)
    signing = json.loads((ROOT / "supabase/signing_keys.json").read_text(encoding="utf-8"))
    private_values.extend(key["d"] for key in signing if "d" in key)
    files = list((ROOT / "apps/web/.next/static").rglob("*.js"))
    if not files or len(private_values) < 3:
        raise RuntimeError("Build assets and generated local credentials must exist.")
    for file in files:
        data = file.read_text(encoding="utf-8")
        if any(value in data for value in private_values):
            raise RuntimeError("A private value was found in a browser asset; contents withheld.")
    print(f"PASS: {len(files)} browser scripts checked; no generated private values found.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit("Browser secret check failed; do not publish. No values were displayed.")
