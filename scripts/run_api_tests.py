"""Run all API tests against a fresh loopback-only Postgres container."""

import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import psycopg
from sqlalchemy import URL

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    container = "wine-journal-test-" + uuid4().hex[:12]
    environment = dict(os.environ)
    environment["POSTGRES_PASSWORD"] = secrets.token_urlsafe(32)
    started = False
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                container,
                "--label",
                "wine-journal.disposable-test=true",
                "--publish",
                "127.0.0.1::5432",
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                "POSTGRES_DB=wine_journal_test",
                "postgres:17-alpine",
            ],
            env=environment,
            check=True,
            capture_output=True,
        )
        started = True
        info = json.loads(
            subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{json .NetworkSettings.Ports}}",
                    container,
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
        binding = info["5432/tcp"][0]
        if binding["HostIp"] != "127.0.0.1":
            raise RuntimeError("Refusing a test database exposed outside loopback.")
        url = URL.create(
            "postgresql",
            username="postgres",
            password=environment["POSTGRES_PASSWORD"],
            host="127.0.0.1",
            port=int(binding["HostPort"]),
            database="wine_journal_test",
        )
        connection = url.render_as_string(hide_password=False)
        deadline = time.monotonic() + 60
        while True:
            try:
                with psycopg.connect(connection, connect_timeout=2):
                    break
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Disposable database did not become ready.") from None
                time.sleep(0.5)
        environment["WINE_JOURNAL_TEST_ADMIN_DATABASE_URL"] = connection
        print("Running API tests with a fresh, isolated Postgres database.", flush=True)
        return subprocess.run(
            [sys.executable, "-m", "pytest", *sys.argv[1:]], cwd=ROOT / "apps/api", env=environment
        ).returncode
    finally:
        if started:
            subprocess.run(["docker", "rm", "--force", container], capture_output=True, check=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        sys.exit(
            f"Database test runner failed ({type(exc).__name__}); credentials were not displayed."
        )
