"""Synthetic idempotent effect used only against disposable test Postgres."""

import os
import sys
import time

from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url

from wine_journal.core.database import database_engine
from wine_journal.media.jobs import Claim
from wine_journal.worker import run_once


def main() -> None:
    url = SecretStr(os.environ["WINE_JOURNAL_TEST_WORKER_URL"])
    parsed = make_url(url.get_secret_value())
    if parsed.host != "127.0.0.1" or parsed.database != "wine_journal_test" or parsed.port == 54322:
        raise ValueError("Disposable test database required")
    engine = database_engine(url)

    def effect(job: Claim) -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO app.worker_test_effects (id) VALUES (:id) ON CONFLICT DO NOTHING"
                ),
                {"id": job.operation_key},
            )
        if "--pause-after-effect" in sys.argv:
            time.sleep(60)

    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if run_once(engine, {"synthetic_effect": effect}, lease_seconds=1):
                return
            time.sleep(0.05)
        raise RuntimeError("Synthetic worker timed out")
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        sys.exit(f"Synthetic worker failed ({type(error).__name__}); details withheld.")
