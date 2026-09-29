from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.catalog.models import WineDefinition
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.journal.models import DrinkingEntry, EntrySave, UserWine
from wine_journal.journal.schemas import SaveEntry
from wine_journal.journal.service import save_entry
from wine_journal.main import create_app


def test_retry_concurrency_and_intentional_repeats(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://journal.test", uuid4())
    body = SaveEntry.model_validate(
        {"consumedDate": "2026-09-01", "manualWine": {"name": "Dinner wine"}}
    )
    key = uuid4()
    try:
        with Session(engine, expire_on_commit=False) as session:
            owner = bootstrap_account(session, principal)

        def save(_: int) -> UUID:
            with Session(engine, expire_on_commit=False) as session:
                return save_entry(session, principal, key, body).id

        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(save, range(8)))
        assert len(set(results)) == 1
        with Session(engine, expire_on_commit=False) as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(WineDefinition)
                    .where(WineDefinition.owner_id == owner.id)
                )
                == 1
            )
            wine = session.scalar(select(UserWine).where(UserWine.owner_id == owner.id))
            assert wine is not None
            wine_id, release_id = wine.id, wine.release_id
            session.rollback()
            repeat = SaveEntry.model_validate(
                {"consumedDate": "2026-09-01", "releaseId": str(release_id)}
            )
            another = save_entry(session, principal, uuid4(), repeat)
            assert another.id != results[0]
            assert another.user_wine_id == wine_id
    finally:
        engine.dispose()


def test_save_http_validation_ownership_and_replay(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://journal.test", uuid4())
    other = Principal(principal.issuer, uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        body = {"consumedDate": "2026-08-01", "manualWine": {"name": "Cabernet"}}
        headers = {"Idempotency-Key": str(uuid4())}
        first = client.post("/api/v1/entries", json=body, headers=headers)
        assert first.status_code == 200
        assert first.headers["cache-control"] == "no-store"
        assert client.post("/api/v1/entries", json=body, headers=headers).json() == first.json()
        assert client.post("/api/v1/entries", json=body).status_code == 422
        assert (
            client.post(
                "/api/v1/entries", json={**body, "consumedDate": "2026-08-02"}, headers=headers
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/v1/entries", json={**body, "ownerId": str(uuid4())}, headers=headers
            ).status_code
            == 422
        )
        engine = database_engine(database_urls["runtime"])
        try:
            with Session(engine) as session:
                wine = session.get(UserWine, UUID(first.json()["userWineId"]))
                assert wine is not None
                release_id = str(wine.release_id)
            app.dependency_overrides[require_principal] = lambda: other
            other_id = UUID(client.post("/api/v1/me", json={}).json()["id"])
            invalid_key = uuid4()
            assert (
                client.post(
                    "/api/v1/entries",
                    json={"consumedDate": "2026-08-01", "releaseId": release_id},
                    headers={"Idempotency-Key": str(invalid_key)},
                ).status_code
                == 404
            )
            with Session(engine) as session:
                assert session.get(EntrySave, (other_id, invalid_key)) is None
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.add(
                        DrinkingEntry(
                            owner_id=other_id,
                            user_wine_id=UUID(first.json()["userWineId"]),
                            consumed_date=body["consumedDate"],
                        )
                    )
                    session.flush()
        finally:
            engine.dispose()


def test_atomic_failure_rolls_back_manual_wine(
    database_urls: dict[str, SecretStr], monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://journal.test", uuid4())
    key = uuid4()
    try:
        with Session(engine, expire_on_commit=False) as session:
            owner = bootstrap_account(session, principal)
            original = session.flush

            def fail_on_entry(*args: object, **kwargs: object) -> None:
                if any(isinstance(item, DrinkingEntry) for item in session.new):
                    raise RuntimeError("Simulated failure after manual identity creation")
                original()

            monkeypatch.setattr(session, "flush", fail_on_entry)
            with pytest.raises(RuntimeError):
                save_entry(
                    session,
                    principal,
                    key,
                    SaveEntry.model_validate(
                        {"consumedDate": "2026-09-01", "manualWine": {"name": "Rollback wine"}}
                    ),
                )
            assert session.get(EntrySave, (owner.id, key)) is None
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(WineDefinition)
                    .where(WineDefinition.owner_id == owner.id)
                )
                == 0
            )
    finally:
        engine.dispose()
