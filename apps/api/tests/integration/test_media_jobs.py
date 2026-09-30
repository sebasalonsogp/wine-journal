import os
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal
from wine_journal.core.database import database_engine
from wine_journal.media.jobs import Claim, claim, enqueue, finish, renew
from wine_journal.worker import run_once


@pytest.fixture
def queue(database_urls: dict[str, SecretStr]) -> Iterator[tuple[Engine, Engine, UUID]]:
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    with Session(engine) as session:
        owner = bootstrap_account(session, Principal("https://jobs.test", uuid4())).id
    try:
        yield engine, admin, owner
    finally:
        with admin.begin() as connection:
            connection.execute(text("DELETE FROM app.jobs"))
        engine.dispose()
        admin.dispose()


def add(engine: Engine, owner: UUID, *, attempts: int = 5, kind: str = "synthetic_effect") -> UUID:
    with Session(engine) as session, session.begin():
        return enqueue(
            session,
            owner_id=owner,
            operation_key=uuid4(),
            kind=kind,
            reference_id=uuid4(),
            max_attempts=attempts,
        )


def expire(admin: Engine, job_id: UUID) -> None:
    with admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.jobs SET lease_until = clock_timestamp() - interval '1 second' "
                "WHERE id = :id"
            ),
            {"id": job_id},
        )


def test_enqueue_is_transactional_and_operation_keys_are_owner_scoped(
    queue: tuple[Engine, Engine, UUID],
) -> None:
    engine, _, owner = queue
    key, reference = uuid4(), uuid4()
    with Session(engine) as session, pytest.raises(RuntimeError), session.begin():
        enqueue(session, owner_id=owner, operation_key=key, kind="photo", reference_id=reference)
        raise RuntimeError("Rollback synthetic domain operation")
    assert claim(engine) is None
    with Session(engine) as session, session.begin():
        first = enqueue(
            session, owner_id=owner, operation_key=key, kind="photo", reference_id=reference
        )
    with Session(engine) as session, session.begin():
        assert (
            enqueue(
                session, owner_id=owner, operation_key=key, kind="photo", reference_id=reference
            )
            == first
        )
    with Session(engine) as session, pytest.raises(ValueError), session.begin():
        enqueue(session, owner_id=owner, operation_key=key, kind="photo", reference_id=uuid4())
    with Session(engine) as session:
        other = bootstrap_account(session, Principal("https://jobs.test", uuid4())).id
    with Session(engine) as session, session.begin():
        assert (
            enqueue(
                session, owner_id=other, operation_key=key, kind="photo", reference_id=reference
            )
            != first
        )
    for statement in [
        "DELETE FROM app.jobs",
        "UPDATE app.jobs SET owner_id = owner_id",
        "UPDATE app.jobs SET operation_key = operation_key",
    ]:
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text(statement))


def test_two_claimants_skip_locks_and_take_distinct_jobs(
    queue: tuple[Engine, Engine, UUID],
) -> None:
    engine, admin, owner = queue
    ids = {add(engine, owner) for _ in range(3)}
    locked = next(iter(ids))
    with admin.begin() as connection:
        connection.execute(
            text("SELECT id FROM app.jobs WHERE id = :id FOR UPDATE"), {"id": locked}
        )
        with ThreadPoolExecutor(max_workers=2) as workers:
            claims = list(workers.map(lambda _: claim(engine), range(2)))
        assert {item.id for item in claims if item} == ids - {locked}
    for item in claims:
        assert item is not None and finish(engine, item)
    last = claim(engine)
    assert last and last.id == locked and finish(engine, last)
    assert claim(engine) is None


def test_leases_fence_stale_workers_and_retries_are_bounded(
    queue: tuple[Engine, Engine, UUID],
) -> None:
    engine, admin, owner = queue
    identifier = add(engine, owner, attempts=2)
    first = claim(engine)
    assert first is not None
    assert renew(engine, first, lease_seconds=120)
    assert claim(engine) is None
    expire(admin, identifier)
    assert not finish(engine, first) and not renew(engine, first)
    second = claim(engine)
    assert second and second.attempt == 2 and second.token != first.token
    assert not finish(engine, first, error="HANDLER_FAILED")
    assert finish(engine, second, error="HANDLER_FAILED")
    assert claim(engine) is None
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT state, attempts, error_code FROM app.jobs WHERE id = :id"),
            {"id": identifier},
        ).one() == ("FAILED", 2, "HANDLER_FAILED")
    abandoned = add(engine, owner, attempts=1)
    assert claim(engine)
    expire(admin, abandoned)
    assert claim(engine) is None
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT error_code FROM app.jobs WHERE id = :id"), {"id": abandoned}
            )
            == "LEASE_EXPIRED"
        )


def test_handler_failures_back_off_without_logging_private_exceptions(
    queue: tuple[Engine, Engine, UUID], caplog: pytest.LogCaptureFixture
) -> None:
    engine, admin, owner = queue
    identifier = add(engine, owner)

    def failure(_: Claim) -> None:
        raise RuntimeError("SYNTHETIC_PRIVATE_EXCEPTION")

    assert run_once(engine, {"synthetic_effect": failure})
    assert "SYNTHETIC_PRIVATE_EXCEPTION" not in caplog.text
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT state, run_after > clock_timestamp(), error_code FROM app.jobs "
                "WHERE id = :id"
            ),
            {"id": identifier},
        ).one()
        assert row == ("PENDING", True, "HANDLER_FAILED")
    assert claim(engine) is None
    with admin.begin() as connection:
        connection.execute(
            text("UPDATE app.jobs SET run_after = clock_timestamp() WHERE id = :id"),
            {"id": identifier},
        )
    assert run_once(engine, {})
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT state, error_code FROM app.jobs WHERE id = :id"), {"id": identifier}
        ).one() == ("FAILED", "UNSUPPORTED_KIND")


def test_two_processes_recover_a_killed_worker_without_duplicate_effects(
    queue: tuple[Engine, Engine, UUID], database_urls: dict[str, SecretStr]
) -> None:
    engine, admin, owner = queue
    with admin.begin() as connection:
        connection.execute(text("CREATE TABLE app.worker_test_effects (id uuid PRIMARY KEY)"))
        connection.execute(text("GRANT SELECT, INSERT ON app.worker_test_effects TO wine_api"))
    identifier = add(engine, owner)
    environment = dict(os.environ)
    environment["WINE_JOURNAL_TEST_WORKER_URL"] = database_urls["runtime"].get_secret_value()
    script = Path(__file__).parents[1] / "fixtures/job_worker.py"
    children: list[subprocess.Popen[bytes]] = []
    try:
        first = subprocess.Popen(
            [sys.executable, str(script), "--pause-after-effect"],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        children.append(first)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with engine.connect() as connection:
                if connection.scalar(text("SELECT count(*) FROM app.worker_test_effects")) == 1:
                    break
            assert first.poll() is None, "Synthetic worker exited before its effect."
            time.sleep(0.05)
        else:
            pytest.fail("Synthetic worker did not reach its effect.")
        # First handler committed a real effect but has not acknowledged it.
        second = subprocess.Popen(
            [sys.executable, str(script)],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        children.append(second)
        first.kill()
        first.wait(timeout=5)
        assert second.wait(timeout=15) == 0
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM app.worker_test_effects")) == 1
            assert connection.execute(
                text("SELECT state, attempts FROM app.jobs WHERE id = :id"), {"id": identifier}
            ).one() == ("SUCCEEDED", 2)
    finally:
        for process in children:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
        with admin.begin() as connection:
            connection.execute(text("DROP TABLE app.worker_test_effects"))


def test_jobs_migrate_without_altering_journal_rows(
    queue: tuple[Engine, Engine, UUID], migrate: Callable[..., None]
) -> None:
    engine, _, _ = queue
    with engine.connect() as connection:
        before = connection.scalar(text("SELECT count(*) FROM app.drinking_entries"))
    migrate("downgrade", "0010_occasion_deletion")
    migrate("upgrade", "head")
    migrate("check")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM app.drinking_entries")) == before
