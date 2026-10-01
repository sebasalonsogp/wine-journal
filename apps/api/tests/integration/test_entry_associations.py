from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.core.errors import ApiError
from wine_journal.journal.entry_associations import set_occasion
from wine_journal.journal.occasion_schemas import OccasionFields
from wine_journal.journal.occasions import create_occasion
from wine_journal.journal.schemas import SaveEntry
from wine_journal.journal.service import save_entry
from wine_journal.main import create_app


def test_link_move_unlink_preserves_entries_ratings_and_scope(
    database_urls: dict[str, SecretStr],
) -> None:
    principal = Principal("https://entry-links.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        occasions = [
            client.post(
                "/api/v1/occasions",
                json={"occasionDate": "2026-09-29", "title": name},
                headers={"Idempotency-Key": str(uuid4())},
            ).json()
            for name in ["Dinner", "Tasting"]
        ]
        entry = client.post(
            "/api/v1/entries",
            json={
                "manualWine": {"name": "Red"},
                "consumedDate": "2026-09-25",
                "notes": "Original note",
            },
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        entry_url = f"/api/v1/entries/{entry['id']}"
        wine_url = f"/api/v1/me/wines/{entry['userWineId']}"
        entry = client.patch(
            entry_url,
            json={
                "version": 1,
                "localTime": "20:30",
                "timezone": "America/New_York",
                "locationLabel": "Home",
            },
        ).json()
        wine = client.get(wine_url).json()
        second = client.post(
            "/api/v1/entries",
            json={"releaseId": wine["releaseId"], "consumedDate": "2026-09-24"},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        rating = client.put(f"{wine_url}/rating", json={"version": 0, "score": 4.5}).json()
        urls = [f"/api/v1/occasions/{o['id']}/entries/{entry['id']}" for o in occasions]
        linked = client.put(urls[0], json={"version": 2, "previousOccasionId": None})
        assert linked.status_code == 200 and linked.headers["cache-control"] == "no-store"
        assert linked.json()["occasionId"] == occasions[0]["id"]
        assert (
            client.put(urls[1], json={"version": 3, "previousOccasionId": None}).status_code == 409
        )
        assert (
            client.put(
                urls[1], json={"version": 2, "previousOccasionId": occasions[0]["id"]}
            ).status_code
            == 409
        )
        assert client.put(urls[1], json={"version": 3}).status_code == 422
        moved = client.put(
            urls[1], json={"version": 3, "previousOccasionId": occasions[0]["id"]}
        ).json()
        assert moved["version"] == 4
        assert (
            client.put(
                urls[1], json={"version": 4, "previousOccasionId": occasions[1]["id"]}
            ).json()["version"]
            == 4
        )
        assert client.delete(urls[0], params={"version": 4}).status_code == 409
        assert client.delete(urls[1], params={"version": 4}).status_code == 200
        assert client.delete(urls[1], params={"version": 4}).status_code == 409
        unlinked = client.get(entry_url).json()
        assert unlinked["occasionId"] is None and unlinked["version"] == 5

        def preserved(value: dict[str, object]) -> dict[str, object]:
            return {k: v for k, v in value.items() if k not in {"version", "occasionId"}}

        assert preserved(unlinked) == preserved(entry)
        second_url = f"/api/v1/occasions/{occasions[0]['id']}/entries/{second['id']}"
        assert (
            client.put(second_url, json={"version": 1, "previousOccasionId": None}).status_code
            == 200
        )
        assert client.delete(second_url, params={"version": 2}).status_code == 200
        assert client.get(wine_url).json()["entryCount"] == 2
        assert client.get(wine_url).json()["currentRating"] == rating["score"]
        assert len(client.get(f"{wine_url}/rating-history").json()["items"]) == 1
        assert all(
            client.get(f"/api/v1/occasions/{o['id']}/wines").json()["items"] == []
            for o in occasions
        )
        other = Principal(principal.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        own_occasion = client.post(
            "/api/v1/occasions",
            json={"occasionDate": "2026-09-29"},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        own_url = f"/api/v1/occasions/{own_occasion['id']}/entries/{entry['id']}"
        for url in [own_url, urls[0]]:
            assert (
                client.put(url, json={"version": 5, "previousOccasionId": None}).status_code == 404
            )
            assert client.delete(url, params={"version": 5}).status_code == 404


def test_competing_entry_links_never_silently_overwrite(
    database_urls: dict[str, SecretStr],
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://link-race.test", uuid4())
    with Session(engine) as session:
        bootstrap_account(session, principal)
    try:
        with Session(engine) as session:
            entry = save_entry(
                session,
                principal,
                uuid4(),
                SaveEntry.model_validate(
                    {"consumedDate": "2026-09-29", "manualWine": {"name": "Race"}}
                ),
            )
        ids = []
        for _ in range(2):
            with Session(engine) as session:
                ids.append(
                    create_occasion(
                        session,
                        principal,
                        uuid4(),
                        OccasionFields.model_validate({"occasionDate": "2026-09-29"}),
                    ).id
                )
        barrier = Barrier(2)

        def link(target: UUID) -> int:
            barrier.wait()
            with Session(engine) as session:
                try:
                    set_occasion(session, principal, entry.id, target, 1, None)
                    return 200
                except ApiError as error:
                    return error.status

        with ThreadPoolExecutor(max_workers=2) as workers:
            assert sorted(workers.map(link, ids)) == [200, 409]
    finally:
        engine.dispose()


def test_association_grant_migration_preserves_rows(
    database_urls: dict[str, SecretStr], migrate: Callable[..., None]
) -> None:
    engine = database_engine(database_urls["runtime"])
    try:
        with engine.connect() as connection:
            count = connection.scalar(text("SELECT count(*) FROM app.drinking_entries"))
        migrate("downgrade", "0008_entry_occasion")
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("UPDATE app.drinking_entries SET occasion_id = occasion_id"))
        migrate("upgrade", "head")
        migrate("check")
        with engine.begin() as connection:
            connection.execute(text("UPDATE app.drinking_entries SET occasion_id = occasion_id"))
            assert connection.scalar(text("SELECT count(*) FROM app.drinking_entries")) == count
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("UPDATE app.drinking_entries SET owner_id = owner_id"))
    finally:
        engine.dispose()
