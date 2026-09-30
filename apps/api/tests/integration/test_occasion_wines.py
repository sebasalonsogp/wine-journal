from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.catalog.models import WineDefinition, WineRelease
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.journal.models import DrinkingEntry, Occasion, OccasionSave, UserWine
from wine_journal.journal.occasion_batch import CreateOccasion
from wine_journal.journal.occasions import create_occasion
from wine_journal.main import create_app


def dinner() -> dict[str, object]:
    return {
        "occasionDate": "2026-09-29",
        "title": "Dinner",
        "wines": [
            {
                "manualWine": {"name": name},
                "entries": [
                    {"consumedDate": f"2026-09-{28 + index}", "notes": f"Glass {index + 1}"}
                    for index in range(count)
                ],
            }
            for name, count in [("Red", 2), ("White", 1), ("Rose", 1)]
        ],
    }


def test_dinner_grouping_addition_retry_and_owner_scope(
    database_urls: dict[str, SecretStr],
) -> None:
    principal = Principal("https://occasion-batch.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        key = {"Idempotency-Key": str(uuid4())}
        response = client.post("/api/v1/occasions", json=dinner(), headers=key)
        assert response.status_code == 200
        saved = response.json()
        assert client.post("/api/v1/occasions", json=dinner(), headers=key).json() == saved
        url = f"/api/v1/occasions/{saved['id']}/wines"
        page = client.get(url, params={"limit": 2}).json()
        rest = client.get(url, params={"limit": 2, "cursor": page["nextCursor"]}).json()
        wines = page["items"] + rest["items"]
        assert len(wines) == 3 and sum(w["entryCount"] for w in wines) == 4
        red = next(w for w in wines if w["name"] == "Red")
        entries = client.get(f"/api/v1/me/wines/{red['id']}/entries").json()["items"]
        assert {e["notes"] for e in entries} == {"Glass 1", "Glass 2"}
        assert {e["consumedDate"] for e in entries} == {"2026-09-28", "2026-09-29"}
        addition = {
            "wines": [{"releaseId": red["releaseId"], "entries": [{"consumedDate": "2026-09-30"}]}]
        }
        add_key = {"Idempotency-Key": str(uuid4())}
        assert client.post(url, json=addition, headers=add_key).status_code == 200
        assert client.post(url, json=addition, headers=add_key).status_code == 200
        assert sum(w["entryCount"] for w in client.get(url).json()["items"]) == 5
        other_occasion = client.post(
            "/api/v1/occasions",
            json={"occasionDate": "2026-09-01"},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        other_url = f"/api/v1/occasions/{other_occasion['id']}/wines"
        assert client.get(other_url, params={"cursor": page["nextCursor"]}).status_code == 422
        assert client.post(other_url, json=addition, headers=add_key).status_code == 409
        # Unrelated entries for the same release never inflate the occasion's count.
        client.post(
            "/api/v1/entries",
            json={"releaseId": red["releaseId"], "consumedDate": "2026-09-30"},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert sum(w["entryCount"] for w in client.get(url).json()["items"]) == 5
        other = Principal(principal.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        assert client.get(url).status_code == 404
        assert (
            client.post(url, json=addition, headers={"Idempotency-Key": str(uuid4())}).status_code
            == 404
        )
        assert (
            client.post(
                "/api/v1/occasions",
                json={"occasionDate": "2026-09-29", **addition},
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 404
        )
        assert client.get("/api/v1/occasions").json()["items"] == []


def test_batch_bounds_and_nested_validation(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://batch-validation.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        wine = {"manualWine": {"name": "Red"}, "entries": [{"consumedDate": "2026-09-29"}]}
        invalid = [
            [wine] * 21,
            [{**wine, "entries": []}],
            [{**wine, "entries": [{"consumedDate": "bad"}]}],
            [wine, {**wine, "entries": [{"consumedDate": "2026-09-29"}] * 20}],
            [{**wine, "releaseId": str(uuid4())}],
        ]
        for wines in invalid:
            assert (
                client.post(
                    "/api/v1/occasions",
                    json={"occasionDate": "2026-09-29", "wines": wines},
                    headers={"Idempotency-Key": str(uuid4())},
                ).status_code
                == 422
            )
        assert client.get("/api/v1/occasions").json()["items"] == []
        assert client.get("/api/v1/me/wines").json()["items"] == []


def test_batch_database_rollback_and_concurrent_retry(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://batch-rollback.test", uuid4())
    with Session(engine, expire_on_commit=False) as session:
        owner = bootstrap_account(session, principal).id
    count = 0

    def fail_second(mapper: object, connection: object, entry: DrinkingEntry) -> None:
        nonlocal count
        count += 1
        if count == 2:
            entry.consumed_date = None  # type: ignore[assignment]

    key = uuid4()
    body = CreateOccasion.model_validate(dinner())
    event.listen(DrinkingEntry, "before_insert", fail_second)
    try:
        with Session(engine) as session, pytest.raises(IntegrityError):
            create_occasion(session, principal, key, body)
        with Session(engine) as session:
            for model in [
                Occasion,
                OccasionSave,
                WineDefinition,
                WineRelease,
                UserWine,
                DrinkingEntry,
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
        event.remove(DrinkingEntry, "before_insert", fail_second)
    try:
        barrier = Barrier(2)

        def retry(_: int) -> str:
            barrier.wait()
            with Session(engine) as session:
                return str(create_occasion(session, principal, key, body).id)

        with ThreadPoolExecutor(max_workers=2) as workers:
            assert len(set(workers.map(retry, [1, 2]))) == 1
        with Session(engine) as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(DrinkingEntry)
                    .where(DrinkingEntry.owner_id == owner)
                )
                == 4
            )
    finally:
        engine.dispose()
