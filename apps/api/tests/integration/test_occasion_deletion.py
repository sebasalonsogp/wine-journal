from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.core.errors import ApiError
from wine_journal.journal.occasion_deletion import delete_occasion
from wine_journal.journal.occasion_schemas import OccasionFields
from wine_journal.journal.occasions import create_occasion
from wine_journal.journal.schemas import SaveEntry
from wine_journal.journal.service import save_entry
from wine_journal.main import create_app


def test_occasion_deletion_preserves_entries_and_erases_receipt_context(
    database_urls: dict[str, SecretStr],
) -> None:
    owner = Principal("https://occasion-deletion.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: owner
    with TestClient(app) as client:
        account = client.post("/api/v1/me", json={}).json()
        key = {"Idempotency-Key": str(uuid4())}
        body = {
            "occasionDate": "2026-09-29",
            "title": "Remove dinner",
            "notes": "Private dinner note",
            "wines": [
                {
                    "manualWine": {"name": name},
                    "entries": [{"consumedDate": "2026-09-27", "notes": "Keep wine note"}],
                }
                for name in ["Red", "White", "Rose"]
            ],
        }
        occasion = client.post("/api/v1/occasions", json=body, headers=key).json()
        url = f"/api/v1/occasions/{occasion['id']}"
        wines = client.get(url + "/wines").json()["items"]
        assert len(wines) == 3
        wine_url = f"/api/v1/me/wines/{wines[0]['id']}"
        client.put(wine_url + "/rating", json={"score": 4.5, "version": 0})
        added_key = {"Idempotency-Key": str(uuid4())}
        added_body = {
            "wines": [
                {"releaseId": wines[0]["releaseId"], "entries": [{"consumedDate": "2026-09-28"}]}
            ]
        }
        assert client.post(url + "/wines", json=added_body, headers=added_key).status_code == 200
        original = [
            entry
            for wine in wines
            for entry in client.get(f"/api/v1/me/wines/{wine['id']}/entries").json()["items"]
        ]
        assert len(original) == 4
        enriched = client.patch(
            f"/api/v1/entries/{original[0]['id']}",
            json={
                "version": 1,
                "localTime": "21:30",
                "timezone": "America/New_York",
                "locationLabel": "Own entry place",
            },
        ).json()
        original[0] = enriched
        assert client.delete(url).status_code == 422
        assert client.delete(url, params={"version": 0}).status_code == 422
        assert (
            client.put(
                url, json={"version": 1, "occasionDate": "2026-09-29", "notes": "New context"}
            ).status_code
            == 200
        )
        assert client.delete(url, params={"version": 1}).status_code == 409
        other = Principal(owner.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        assert client.delete(url, params={"version": 2}).status_code == 404
        app.dependency_overrides[require_principal] = lambda: owner
        result = client.delete(url, params={"version": 2})
        assert result.status_code == 200 and result.json() == {"id": occasion["id"]}
        assert result.headers["cache-control"] == "no-store"
        assert client.get(url).status_code == 404
        assert client.delete(url, params={"version": 2}).status_code == 404
        assert client.get("/api/v1/occasions").json()["items"] == []
        for entry in original:
            kept = client.get(f"/api/v1/entries/{entry['id']}").json()
            assert kept == {**entry, "occasionId": None, "version": entry["version"] + 1}
            assert (
                client.patch(
                    f"/api/v1/entries/{entry['id']}",
                    json={"version": entry["version"], "notes": "Stale"},
                ).status_code
                == 409
            )
        assert len(client.get("/api/v1/me/wines").json()["items"]) == 3
        assert client.get(wine_url).json()["currentRating"] == 4.5
        assert len(client.get(wine_url + "/rating-history").json()["items"]) == 1
        for route, payload, headers in [
            ("/api/v1/occasions", body, key),
            (url + "/wines", added_body, added_key),
        ]:
            retry = client.post(route, json=payload, headers=headers)
            assert retry.status_code == 409 and retry.json()["error"]["code"] == "OCCASION_REMOVED"
        # An inline occasion's receipt belongs to the surviving entry, not the occasion.
        inline_key = {"Idempotency-Key": str(uuid4())}
        inline_body = {
            "manualWine": {"name": "Inline"},
            "consumedDate": "2026-09-26",
            "newOccasion": {"occasionDate": "2026-09-26", "notes": "Erase this occasion"},
        }
        inline = client.post("/api/v1/entries", json=inline_body, headers=inline_key).json()
        assert (
            client.delete(
                f"/api/v1/occasions/{inline['occasionId']}", params={"version": 1}
            ).status_code
            == 200
        )
        replay = client.post("/api/v1/entries", json=inline_body, headers=inline_key)
        assert replay.status_code == 200 and replay.json() == {**inline, "occasionId": None}
        engine = database_engine(database_urls["runtime"])
        try:
            with engine.connect() as connection:
                receipts = connection.scalars(
                    text("SELECT response FROM app.occasion_saves WHERE owner_id = :owner"),
                    {"owner": account["id"]},
                ).all()
                assert receipts == [{"deleted": True}, {"deleted": True}]
                assert (
                    connection.scalar(
                        text("SELECT count(*) FROM app.drinking_entries WHERE owner_id = :owner"),
                        {"owner": account["id"]},
                    )
                    == 5
                )
        finally:
            engine.dispose()


def test_concurrent_capture_and_occasion_deletion_have_no_partial_save(
    database_urls: dict[str, SecretStr],
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://occasion-delete-race.test", uuid4())
    try:
        with Session(engine) as session:
            owner_id = bootstrap_account(session, principal).id
        with Session(engine) as session:
            occasion = create_occasion(
                session,
                principal,
                uuid4(),
                OccasionFields.model_validate({"occasionDate": "2026-09-29"}),
            )
        barrier = Barrier(2)

        def run(remove: bool) -> int:
            barrier.wait()
            with Session(engine) as session:
                try:
                    if remove:
                        delete_occasion(session, principal, occasion.id, 1)
                    else:
                        save_entry(
                            session,
                            principal,
                            uuid4(),
                            SaveEntry.model_validate(
                                {
                                    "manualWine": {"name": "Concurrent"},
                                    "consumedDate": "2026-09-28",
                                    "occasionId": str(occasion.id),
                                }
                            ),
                        )
                    return 200
                except ApiError as error:
                    return error.status

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(run, [True, False]))
        assert results[0] == 200 and results[1] in (200, 404)
        with engine.connect() as connection:
            kept = connection.execute(
                text(
                    "SELECT occasion_id, version FROM app.drinking_entries WHERE owner_id = :owner"
                ),
                {"owner": owner_id},
            ).all()
            assert [tuple(row) for row in kept] == ([(None, 2)] if results[1] == 200 else [])
            assert connection.scalar(
                text("SELECT count(*) FROM app.user_wines WHERE owner_id = :owner"),
                {"owner": owner_id},
            ) == (1 if results[1] == 200 else 0)
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM app.occasions WHERE id = :id"), {"id": occasion.id}
                )
                == 0
            )
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM app.drinking_entries WHERE occasion_id = :id"),
                    {"id": occasion.id},
                )
                == 0
            )
    finally:
        engine.dispose()


def test_occasion_deletion_rolls_back_detach_and_receipt_cleanup(
    database_urls: dict[str, SecretStr],
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://occasion-delete-rollback.test", uuid4())
    try:
        with Session(engine) as session:
            owner_id = bootstrap_account(session, principal).id
        with Session(engine) as session:
            occasion = create_occasion(
                session,
                principal,
                uuid4(),
                OccasionFields.model_validate(
                    {"occasionDate": "2026-09-29", "notes": "Keep on failure"}
                ),
            )
        with Session(engine) as session:
            entry = save_entry(
                session,
                principal,
                uuid4(),
                SaveEntry.model_validate(
                    {
                        "manualWine": {"name": "Keep"},
                        "consumedDate": "2026-09-28",
                        "occasionId": str(occasion.id),
                    }
                ),
            )

        def fail_delete(*args: object) -> None:
            if str(args[2]).startswith("DELETE FROM app.occasions"):
                raise RuntimeError("Synthetic failure after detach and receipt cleanup")

        event.listen(engine, "before_cursor_execute", fail_delete)
        try:
            with Session(engine) as session, pytest.raises(RuntimeError, match="Synthetic failure"):
                delete_occasion(session, principal, occasion.id, 1)
        finally:
            event.remove(engine, "before_cursor_execute", fail_delete)
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT notes FROM app.occasions WHERE id = :id"), {"id": occasion.id}
                )
                == "Keep on failure"
            )
            assert connection.execute(
                text("SELECT occasion_id, version FROM app.drinking_entries WHERE id = :id"),
                {"id": entry.id},
            ).one() == (occasion.id, 1)
            assert (
                connection.scalar(
                    text("SELECT response FROM app.occasion_saves WHERE owner_id = :owner"),
                    {"owner": owner_id},
                )["notes"]
                == "Keep on failure"
            )
            assert connection.scalar(
                text("SELECT response FROM app.entry_saves WHERE owner_id = :owner"),
                {"owner": owner_id},
            )["occasionId"] == str(occasion.id)
    finally:
        engine.dispose()


def test_occasion_delete_grant_is_reversible(
    database_urls: dict[str, SecretStr],
    migrate: Callable[..., None],
) -> None:
    engine = database_engine(database_urls["runtime"])
    try:
        migrate("downgrade", "0009_entry_association")
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("DELETE FROM app.occasions WHERE false"))
        migrate("upgrade", "head")
        migrate("check")
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM app.occasions WHERE false"))
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("UPDATE app.occasions SET owner_id = owner_id WHERE false"))
    finally:
        engine.dispose()
