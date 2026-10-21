from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.core.errors import ApiError
from wine_journal.journal.deletion import delete_entry
from wine_journal.journal.edits import edit_entry, read_entry
from wine_journal.journal.entry_associations import set_occasion
from wine_journal.journal.entry_wines import MoveEntryWine, move_entry_wine
from wine_journal.journal.models import DrinkingEntry, Occasion
from wine_journal.journal.schemas import EditEntry, SaveEntry
from wine_journal.journal.service import save_entry
from wine_journal.main import create_app


def capture(client: TestClient, name: str, key: UUID | None = None) -> dict[str, object]:
    response = client.post(
        "/api/v1/entries",
        json={"consumedDate": "2026-10-20", "manualWine": {"name": name}},
        headers={"Idempotency-Key": str(key or uuid4())},
    )
    assert response.status_code == 200
    return dict(response.json())


def test_move_preserves_entry_and_ratings_with_retry_and_validation(
    database_urls: dict[str, SecretStr],
) -> None:
    principal = Principal("https://move-entry.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        capture_key = uuid4()
        original, target = capture(client, "Original", capture_key), capture(client, "Target")
        source_id, target_id = original["userWineId"], target["userWineId"]
        url = f"/api/v1/entries/{original['id']}"
        original = client.patch(
            url,
            json={
                "version": 1,
                "notes": "Keep this memory",
                "locationLabel": "A friend's house",
                "localTime": "19:30",
                "timezone": "America/New_York",
            },
        ).json()
        for wine, score in [(source_id, 4), (target_id, 3)]:
            assert (
                client.put(
                    f"/api/v1/me/wines/{wine}/rating", json={"version": 0, "score": score}
                ).status_code
                == 200
            )
        history = client.get(f"/api/v1/me/wines/{source_id}/rating-history").json()
        body = {"version": 2, "previousWineId": source_id, "wineId": target_id}
        response = client.put(f"{url}/wine", json=body)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        moved = response.json()
        assert moved == {**original, "userWineId": target_id, "version": 3}
        assert client.put(f"{url}/wine", json=body).status_code == 409
        assert client.get(url).json() == moved
        assert capture(client, "Original", capture_key) == moved
        assert client.get(f"/api/v1/me/wines/{source_id}/rating-history").json() == history
        for wine, count, score in [(source_id, 0, 4), (target_id, 2, 3)]:
            details = client.get(f"/api/v1/me/wines/{wine}").json()
            assert details["entryCount"] == count and details["currentRating"] == score
        noop = {"version": 3, "previousWineId": target_id, "wineId": target_id}
        assert client.put(f"{url}/wine", json=noop).json() == moved
        assert (
            client.put(f"{url}/wine", json={**noop, "previousWineId": source_id}).status_code == 409
        )
        invalid_bodies: list[dict[str, object]] = [
            {"version": True},
            {"manualWine": {"name": "Other"}},
            {"ownerId": str(uuid4())},
            {"notes": "Overwrite"},
            {"wineId": None},
        ]
        for invalid in invalid_bodies:
            assert client.put(f"{url}/wine", json={**noop, **invalid}).status_code == 422
        assert client.put(f"{url}/wine", json={**noop, "wineId": str(uuid4())}).status_code == 404
        # New manual destinations are deliberate records, even if their names match.
        new_body = {"version": 3, "previousWineId": target_id, "manualWine": {"name": "Target"}}
        new = client.put(f"{url}/wine", json=new_body)
        assert new.status_code == 200
        assert new.json()["userWineId"] not in (source_id, target_id)
        assert client.put(f"{url}/wine", json=new_body).status_code == 409
        assert len(client.get("/api/v1/me/wines").json()["items"]) == 3
        assert client.get(url).json() == new.json()
        other = Principal(principal.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        foreign = capture(client, "Someone else's wine")
        assert client.put(f"{url}/wine", json=new_body).status_code == 404
        app.dependency_overrides[require_principal] = lambda: principal
        assert (
            client.put(
                f"{url}/wine",
                json={
                    "version": 4,
                    "previousWineId": new.json()["userWineId"],
                    "wineId": foreign["userWineId"],
                },
            ).status_code
            == 404
        )
        del app.dependency_overrides[require_principal]
        assert client.put(f"{url}/wine", json=new_body).status_code == 401


def test_concurrent_new_destinations_rollback_the_loser(
    database_urls: dict[str, SecretStr],
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://move-race.test", uuid4())
    try:
        with Session(engine, expire_on_commit=False) as session:
            owner = bootstrap_account(session, principal)
            entry = save_entry(
                session,
                principal,
                uuid4(),
                SaveEntry.model_validate(
                    {"consumedDate": "2026-10-20", "manualWine": {"name": "Source"}}
                ),
            )
        barrier = Barrier(2)

        def synchronized_read(session: Session, owner_id: UUID, entry_id: UUID) -> DrinkingEntry:
            result = read_entry(session, owner_id, entry_id)
            barrier.wait(timeout=5)
            return result

        def move(name: str) -> int:
            with Session(engine, expire_on_commit=False) as session:
                try:
                    move_entry_wine(
                        session,
                        principal,
                        entry.id,
                        MoveEntryWine.model_validate(
                            {
                                "version": 1,
                                "previousWineId": str(entry.user_wine_id),
                                "manualWine": {"name": name},
                            }
                        ),
                    )
                    return 200
                except ApiError as error:
                    return error.status

        with patch("wine_journal.journal.entry_wines.read_entry", side_effect=synchronized_read):
            with ThreadPoolExecutor(max_workers=2) as workers:
                assert sorted(workers.map(move, ["A", "B"])) == [200, 409]
        with engine.connect() as connection:
            for table in ["wine_definitions", "wine_releases", "user_wines"]:
                assert (
                    connection.scalar(
                        text(f"SELECT count(*) FROM app.{table} WHERE owner_id = :owner"),
                        {"owner": owner.id},
                    )
                    == 2
                )
            assert (
                connection.scalar(
                    text("SELECT version FROM app.drinking_entries WHERE id = :id"),
                    {"id": entry.id},
                )
                == 2
            )
    finally:
        engine.dispose()


def test_move_grant_is_narrow_and_reversible(
    database_urls: dict[str, SecretStr],
    migrate: Callable[..., None],
) -> None:
    engine = database_engine(database_urls["runtime"])
    try:
        with engine.begin() as connection:
            connection.execute(text("UPDATE app.drinking_entries SET user_wine_id = user_wine_id"))
        for column in ["owner_id", "id", "created_at"]:
            with engine.begin() as connection, pytest.raises(ProgrammingError):
                connection.execute(text(f"UPDATE app.drinking_entries SET {column} = {column}"))
        # Database ownership constraints still reject a cross-owner wine.
        principals = [Principal("https://move-grants.test", uuid4()) for _ in range(2)]
        entries = []
        for person in principals:
            with Session(engine, expire_on_commit=False) as session:
                bootstrap_account(session, person)
                entries.append(
                    save_entry(
                        session,
                        person,
                        uuid4(),
                        SaveEntry.model_validate(
                            {"consumedDate": "2026-10-20", "manualWine": {"name": "Grant test"}}
                        ),
                    )
                )
        with engine.begin() as connection, pytest.raises(IntegrityError):
            connection.execute(
                text("UPDATE app.drinking_entries SET user_wine_id = :wine WHERE id = :entry"),
                {"wine": entries[1].user_wine_id, "entry": entries[0].id},
            )
        migrate("downgrade", "0023_catalog_capture")
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("UPDATE app.drinking_entries SET user_wine_id = user_wine_id"))
        migrate("upgrade", "head")
        migrate("check")
    finally:
        engine.dispose()


@pytest.mark.parametrize("competing_change", ["edit", "delete", "occasion"])
def test_change_after_initial_read_prevents_move_and_orphan_wines(
    database_urls: dict[str, SecretStr],
    competing_change: str,
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://move-cas.test", uuid4())
    try:
        with Session(engine, expire_on_commit=False) as session:
            owner = bootstrap_account(session, principal)
            entry = save_entry(
                session,
                principal,
                uuid4(),
                SaveEntry.model_validate(
                    {"consumedDate": "2026-10-20", "manualWine": {"name": "Source"}}
                ),
            )
            with session.begin():
                occasion = Occasion(owner_id=owner.id, occasion_date=entry.consumed_date)
                session.add(occasion)
                session.flush()

        def changed_read(
            session: Session,
            owner_id: UUID,
            entry_id: UUID,
        ) -> DrinkingEntry:
            stale = read_entry(session, owner_id, entry_id)
            with Session(engine, expire_on_commit=False) as other:
                if competing_change == "edit":
                    edit_entry(
                        other,
                        principal,
                        entry_id,
                        EditEntry.model_validate({"version": 1, "notes": "Newer notes"}),
                    )
                elif competing_change == "delete":
                    delete_entry(other, principal, entry_id, 1)
                else:
                    set_occasion(other, principal, entry_id, occasion.id, 1, None)
            return stale

        with patch("wine_journal.journal.entry_wines.read_entry", side_effect=changed_read):
            with Session(engine) as session, pytest.raises(ApiError) as failure:
                move_entry_wine(
                    session,
                    principal,
                    entry.id,
                    MoveEntryWine.model_validate(
                        {
                            "version": 1,
                            "previousWineId": str(entry.user_wine_id),
                            "manualWine": {"name": "Must roll back"},
                        }
                    ),
                )
            assert failure.value.code == "MOVE_CONFLICT"
        with engine.connect() as connection:
            for table in ["wine_definitions", "wine_releases", "user_wines"]:
                assert (
                    connection.scalar(
                        text(f"SELECT count(*) FROM app.{table} WHERE owner_id = :owner"),
                        {"owner": owner.id},
                    )
                    == 1
                )
        with Session(engine) as session:
            saved = session.get(DrinkingEntry, entry.id)
            if competing_change == "delete":
                assert saved is None
            else:
                assert saved is not None
                assert saved.user_wine_id == entry.user_wine_id and saved.version == 2
                if competing_change == "edit":
                    assert saved.notes == "Newer notes"
                else:
                    assert saved.occasion_id == occasion.id
    finally:
        engine.dispose()
