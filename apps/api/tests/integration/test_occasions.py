from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import Occasion, OccasionSave
from wine_journal.journal.occasion_schemas import EditOccasion, OccasionFields
from wine_journal.journal.occasions import create_occasion, edit_occasion
from wine_journal.main import create_app


def test_occasion_lifecycle_owner_scope_and_pagination(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://occasions.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        key = {"Idempotency-Key": str(uuid4())}
        body = {
            "title": " Dinner with friends ",
            "occasionDate": "2026-09-29",
            "localTime": "19:30",
            "timezone": "America/New_York",
            "locationLabel": "At home",
            "notes": "Shared a few favorites.",
        }
        response = client.post("/api/v1/occasions", json=body, headers=key)
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        first = response.json()
        assert first["title"] == "Dinner with friends" and first["version"] == 1
        assert client.post("/api/v1/occasions", json=body, headers=key).json() == first
        assert (
            client.post(
                "/api/v1/occasions", json={**body, "title": "Other"}, headers=key
            ).status_code
            == 409
        )
        untitled = client.post(
            "/api/v1/occasions",
            json={"occasionDate": "2026-09-29", "title": " "},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        assert untitled["title"] is None
        page = client.get("/api/v1/occasions", params={"limit": 1}).json()
        second_page = client.get(
            "/api/v1/occasions", params={"limit": 1, "cursor": page["nextCursor"]}
        ).json()
        assert {item["id"] for item in page["items"] + second_page["items"]} == {
            first["id"],
            untitled["id"],
        }
        assert second_page["nextCursor"] is None
        url = f"/api/v1/occasions/{first['id']}"
        assert client.get(url).json() == first
        edited = client.put(
            url, json={"version": 1, "occasionDate": "2026-01-01", "title": None}
        ).json()
        assert edited["version"] == 2 and edited["localTime"] is None and edited["notes"] is None
        assert edited["createdAt"] == first["createdAt"]
        assert client.put(url, json={"version": 1, "occasionDate": "2026-01-01"}).status_code == 409
        assert client.get(url).json() == edited
        assert client.get("/api/v1/occasions").json()["items"][0]["id"] == untitled["id"]
        assert client.get("/api/v1/me/wines").json()["items"] == []
        client.post(
            "/api/v1/entries",
            json={"consumedDate": "2026-09-29", "manualWine": {"name": "Ordinary glass"}},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert len(client.get("/api/v1/occasions").json()["items"]) == 2
        other = Principal(principal.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        assert client.get(url).status_code == 404
        assert client.put(url, json={"version": 2, "occasionDate": "2026-01-01"}).status_code == 404
        assert client.get("/api/v1/occasions").json()["items"] == []
        assert (
            client.get("/api/v1/occasions", params={"cursor": page["nextCursor"]}).status_code
            == 422
        )


def test_occasion_validation(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://occasion-validation.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        key = {"Idempotency-Key": str(uuid4())}
        invalid: list[dict[str, object]] = [
            {},
            {"occasionDate": None},
            {"occasionDate": "2026-02-30"},
            {"localTime": "19:00"},
            {"timezone": "UTC"},
            {"localTime": "19:00:01", "timezone": "UTC"},
            {"localTime": "19:00+01:00", "timezone": "UTC"},
            {"localTime": "19:00", "timezone": "Unknown/Zone"},
            {"title": "x" * 201},
            {"notes": "x" * 10001},
            {"locationLabel": "\x00"},
            {"ownerId": str(uuid4())},
        ]
        for fields in invalid:
            body = {"occasionDate": "2026-09-29", **fields} if fields else {}
            assert client.post("/api/v1/occasions", json=body, headers=key).status_code == 422
        assert client.get("/api/v1/occasions").json()["items"] == []
        assert client.get("/api/v1/occasions", params={"cursor": "bad"}).status_code == 422
        assert client.get("/api/v1/occasions", params={"limit": 101}).status_code == 422


def test_concurrent_creation_and_edits(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://occasion-race.test", uuid4())
    try:
        with Session(engine, expire_on_commit=False) as session:
            bootstrap_account(session, principal)
        key = uuid4()
        body = OccasionFields.model_validate({"occasionDate": "2026-09-29"})
        barrier = Barrier(2)

        def create(_: int) -> UUID:
            with Session(engine, expire_on_commit=False) as session:
                barrier.wait(timeout=5)
                return create_occasion(session, principal, key, body).id

        with ThreadPoolExecutor(max_workers=2) as workers:
            ids = list(workers.map(create, [1, 2]))
        assert ids[0] == ids[1]
        barrier = Barrier(2)

        def edit(title: str) -> int:
            with Session(engine, expire_on_commit=False) as session:
                barrier.wait(timeout=5)
                try:
                    edit_occasion(
                        session,
                        principal,
                        ids[0],
                        EditOccasion.model_validate(
                            {"occasionDate": "2026-09-29", "version": 1, "title": title}
                        ),
                    )
                    return 200
                except ApiError as error:
                    return error.status

        with ThreadPoolExecutor(max_workers=2) as workers:
            assert sorted(workers.map(edit, ["Dinner", "Winery visit"])) == [200, 409]
    finally:
        engine.dispose()


def test_failed_creation_rolls_back_receipt(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://occasion-rollback.test", uuid4())
    with Session(engine, expire_on_commit=False) as session:
        owner = bootstrap_account(session, principal).id
    key = uuid4()

    def reject(*args: object) -> None:
        raise RuntimeError("Injected save failure")

    event.listen(Occasion, "before_insert", reject)
    try:
        with Session(engine) as session, pytest.raises(RuntimeError):
            create_occasion(
                session,
                principal,
                key,
                OccasionFields.model_validate({"occasionDate": "2026-09-29"}),
            )
        with Session(engine) as session:
            assert session.get(OccasionSave, (owner, key)) is None
            assert (
                session.scalar(
                    select(func.count()).select_from(Occasion).where(Occasion.owner_id == owner)
                )
                == 0
            )
    finally:
        event.remove(Occasion, "before_insert", reject)
        engine.dispose()


def test_occasion_migration_and_restricted_grants(
    database_urls: dict[str, SecretStr], migrate: Callable[..., None]
) -> None:
    engine = database_engine(database_urls["runtime"])
    try:
        with engine.connect() as connection:
            entries = connection.scalar(text("SELECT count(*) FROM app.drinking_entries"))
        migrate("downgrade", "0006_ratings")
        migrate("upgrade", "head")
        migrate("check")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM app.drinking_entries")) == entries
        for statement in [
            "UPDATE app.occasions SET owner_id = owner_id",
            "UPDATE app.occasions SET id = id",
        ]:
            with engine.begin() as connection, pytest.raises(ProgrammingError):
                connection.execute(text(statement))
    finally:
        engine.dispose()


def test_occasions_require_auth() -> None:
    with TestClient(create_app(Settings.model_construct())) as client:
        assert client.get("/api/v1/occasions").status_code == 401
        assert client.get(f"/api/v1/occasions/{uuid4()}").status_code == 401
