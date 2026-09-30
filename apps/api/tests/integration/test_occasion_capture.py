import hashlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.catalog.models import WineDefinition, WineRelease
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.journal.models import DrinkingEntry, EntrySave, Occasion, UserWine
from wine_journal.journal.schemas import SaveEntry
from wine_journal.journal.service import save_entry
from wine_journal.main import create_app


def test_capture_links_new_and_existing_owned_occasions(
    database_urls: dict[str, SecretStr],
) -> None:
    principal = Principal("https://occasion-capture.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        body = {
            "consumedDate": "2026-09-28",
            "manualWine": {"name": "Dinner red"},
            "notes": "A bright finish",
            "newOccasion": {"occasionDate": "2026-09-27", "title": "Weekend", "notes": "Friends"},
        }
        key = {"Idempotency-Key": str(uuid4())}
        response = client.post("/api/v1/entries", json=body, headers=key)
        assert response.status_code == 200
        entry = response.json()
        assert entry["occasionId"] and entry["notes"] == "A bright finish"
        assert entry["consumedDate"] == "2026-09-28"
        assert client.post("/api/v1/entries", json=body, headers=key).json() == entry
        assert client.get(f"/api/v1/entries/{entry['id']}").json() == entry
        occasion = client.get(f"/api/v1/occasions/{entry['occasionId']}").json()
        assert occasion["occasionDate"] == "2026-09-27" and occasion["notes"] == "Friends"
        wine = client.get(f"/api/v1/me/wines/{entry['userWineId']}").json()
        repeat_body = {
            "consumedDate": "2026-09-29",
            "releaseId": wine["releaseId"],
            "occasionId": entry["occasionId"],
        }
        repeat = client.post(
            "/api/v1/entries", json=repeat_body, headers={"Idempotency-Key": str(uuid4())}
        )
        assert repeat.status_code == 200 and repeat.json()["occasionId"] == entry["occasionId"]
        assert len(client.get("/api/v1/occasions").json()["items"]) == 1
        assert client.get(f"/api/v1/occasions/{entry['occasionId']}").json() == occasion
        assert client.get(f"/api/v1/me/wines/{entry['userWineId']}").json()["entryCount"] == 2
        assert (
            client.post(
                "/api/v1/entries", json={**body, "notes": "Changed"}, headers=key
            ).status_code
            == 409
        )
        other = Principal(principal.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        foreign = {
            "consumedDate": "2026-09-29",
            "manualWine": {"name": "Private"},
            "occasionId": entry["occasionId"],
        }
        assert (
            client.post(
                "/api/v1/entries", json=foreign, headers={"Idempotency-Key": str(uuid4())}
            ).status_code
            == 404
        )
        assert client.get("/api/v1/me/wines").json()["items"] == []


def test_nested_capture_validation_creates_nothing(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://nested-validation.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        invalid: list[dict[str, object]] = [
            {"newOccasion": {"occasionDate": "2026-02-30"}},
            {"newOccasion": {"occasionDate": "2026-09-29", "localTime": "19:00"}},
            {"newOccasion": {"occasionDate": "2026-09-29", "ownerId": str(uuid4())}},
            {"newOccasion": {"occasionDate": "2026-09-29"}, "occasionId": str(uuid4())},
            {"notes": "x" * 10001},
            {"notes": "\x00"},
        ]
        for extra in invalid:
            body: dict[str, object] = {
                "consumedDate": "2026-09-29",
                "manualWine": {"name": "No partial wine"},
                **extra,
            }
            assert (
                client.post(
                    "/api/v1/entries", json=body, headers={"Idempotency-Key": str(uuid4())}
                ).status_code
                == 422
            )
        assert client.get("/api/v1/me/wines").json()["items"] == []
        assert client.get("/api/v1/occasions").json()["items"] == []


def test_nested_database_failure_rolls_back_every_record(
    database_urls: dict[str, SecretStr],
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://nested-rollback.test", uuid4())
    with Session(engine, expire_on_commit=False) as session:
        owner = bootstrap_account(session, principal).id
    key = uuid4()
    body = SaveEntry.model_validate(
        {
            "consumedDate": "2026-09-29",
            "manualWine": {"name": "Atomic bottle"},
            "newOccasion": {"occasionDate": "2026-09-29", "title": "Atomic dinner"},
        }
    )

    def invalidate_nested_occasion(
        mapper: object, connection: object, entry: DrinkingEntry
    ) -> None:
        # Execute after the occasion and wine insertions, proving a real DB failure rolls all back.
        entry.consumed_date = None  # type: ignore[assignment]

    event.listen(DrinkingEntry, "before_insert", invalidate_nested_occasion)
    try:
        with Session(engine) as session, pytest.raises(IntegrityError):
            save_entry(session, principal, key, body)
        with Session(engine) as session:
            for model in [
                Occasion,
                WineDefinition,
                WineRelease,
                UserWine,
                DrinkingEntry,
                EntrySave,
            ]:
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.__table__.c.owner_id == owner)
                    )
                    == 0
                )
    finally:
        event.remove(DrinkingEntry, "before_insert", invalidate_nested_occasion)
    try:
        barrier = Barrier(2)

        def attempt(_: int) -> UUID:
            barrier.wait()
            with Session(engine) as session:
                return save_entry(session, principal, key, body).id

        with ThreadPoolExecutor(max_workers=2) as workers:
            assert len(set(workers.map(attempt, [1, 2]))) == 1
        with Session(engine) as session:
            assert (
                session.scalar(
                    select(func.count()).select_from(Occasion).where(Occasion.owner_id == owner)
                )
                == 1
            )
    finally:
        engine.dispose()


def test_old_receipts_and_occasion_fk_migration(
    database_urls: dict[str, SecretStr], migrate: Callable[..., None]
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://legacy-capture.test", uuid4())
    with Session(engine, expire_on_commit=False) as session:
        owner = bootstrap_account(session, principal).id
    body = SaveEntry.model_validate(
        {"consumedDate": "2026-09-29", "manualWine": {"name": "Legacy bottle"}}
    )
    key = uuid4()
    try:
        with Session(engine) as session:
            saved = save_entry(session, principal, key, body)
        with Session(engine) as session, session.begin():
            receipt = session.get(EntrySave, (owner, key))
            assert receipt is not None and receipt.response is not None
            legacy_json = body.model_dump_json(exclude={"occasion_id", "new_occasion", "notes"})
            assert receipt.request_hash == hashlib.sha256(legacy_json.encode()).hexdigest()
            receipt.response = {k: v for k, v in receipt.response.items() if k != "occasionId"}
        migrate("downgrade", "0007_occasions")
        migrate("upgrade", "head")
        migrate("check")
        with Session(engine) as session:
            replay = save_entry(session, principal, key, body)
            assert replay.id == saved.id and replay.occasion_id is None
        with engine.begin() as connection, pytest.raises(IntegrityError):
            # Existing owner/wine, nonexistent occasion: database rejects the link independently.
            connection.execute(
                text(
                    "INSERT INTO app.drinking_entries "
                    "(id, owner_id, user_wine_id, consumed_date, occasion_id) "
                    "VALUES (:id, :owner, :wine, '2026-09-29', :occasion)"
                ),
                {"id": uuid4(), "owner": owner, "wine": saved.user_wine_id, "occasion": uuid4()},
            )
    finally:
        engine.dispose()
