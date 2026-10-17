from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

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
from wine_journal.journal.edits import edit_entry
from wine_journal.journal.schemas import EditEntry, SaveEntry
from wine_journal.journal.service import save_entry
from wine_journal.main import create_app


def test_edit_omission_clearing_conflict_and_ownership(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://edits.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        original = client.post(
            "/api/v1/entries",
            json={"consumedDate": "2026-09-29", "manualWine": {"name": "Journal wine"}},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        url = f"/api/v1/entries/{original['id']}"
        change = {
            "version": 1,
            "consumedDate": "2026-01-01",
            "localTime": "00:15",
            "timezone": "Pacific/Kiritimati",
            "locationLabel": "A friend's house",
            "notes": "Cherry, herbs.\nShared over dinner.",
        }
        response = client.patch(url, json=change)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        edited = response.json()
        assert edited["id"] == original["id"] and edited["version"] == 2
        assert edited["createdAt"] == original["createdAt"]
        assert edited["consumedDate"] == "2026-01-01"
        assert edited["localTime"] == "00:15:00"
        assert client.patch(url, json=change).status_code == 409
        assert client.get(url).json() == edited
        omitted = client.patch(url, json={"version": 2, "notes": None}).json()
        assert omitted["notes"] is None
        assert omitted["locationLabel"] == change["locationLabel"]
        assert omitted["localTime"] == "00:15:00"
        invalid_patches: list[dict[str, object]] = [
            {"consumedDate": None},
            {"localTime": "12:00+03:00"},
            {"localTime": "12:00:01"},
            {"timezone": "Not/AZone"},
            {"localTime": None},
            {"notes": "x" * 10001},
            {"ownerId": str(uuid4())},
            {},
        ]
        for invalid in invalid_patches:
            assert client.patch(url, json={"version": 3, **invalid}).status_code == 422
        cleared = client.patch(
            url,
            json={
                "version": 3,
                "localTime": None,
                "timezone": None,
                "locationLabel": None,
            },
        ).json()
        assert cleared["version"] == 4 and cleared["localTime"] is None
        history = client.get(f"/api/v1/me/wines/{original['userWineId']}/entries").json()
        assert history["items"] == [cleared]
        assert (
            client.get(f"/api/v1/me/wines/{original['userWineId']}").json()["lastConsumedDate"]
            == "2026-01-01"
        )
        # Bootstrap a stable second identity, then prove neither reads nor writes cross owners.
        other = Principal(principal.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        assert client.get(url).status_code == 404
        assert client.patch(url, json={"version": 4, "notes": "Other"}).status_code == 404


def test_simultaneous_editors_have_exactly_one_winner(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://edit-race.test", uuid4())
    try:
        with Session(engine, expire_on_commit=False) as session:
            bootstrap_account(session, principal)
            entry = save_entry(
                session,
                principal,
                uuid4(),
                SaveEntry.model_validate(
                    {
                        "consumedDate": "2026-11-01",
                        "manualWine": {"name": "Race wine"},
                    }
                ),
            )
        barrier = Barrier(2)

        def edit(note: str) -> int:
            with Session(engine, expire_on_commit=False) as session:
                barrier.wait(timeout=5)
                try:
                    saved = edit_entry(
                        session,
                        principal,
                        entry.id,
                        EditEntry.model_validate(
                            {
                                "version": 1,
                                "notes": note,
                                "localTime": "01:30",
                                "timezone": "America/New_York",
                            }
                        ),
                    )
                    assert saved.version == 2 and saved.consumed_date == entry.consumed_date
                    return 200
                except ApiError as error:
                    return error.status

        with ThreadPoolExecutor(max_workers=2) as workers:
            assert sorted(workers.map(edit, ["Editor A", "Editor B"])) == [200, 409]
    finally:
        engine.dispose()


def test_upgrade_preserves_existing_entry_and_limits_update_columns(
    database_urls: dict[str, SecretStr],
    migrate: Callable[..., None],
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://edit-upgrade.test", uuid4())
    try:
        with Session(engine, expire_on_commit=False) as session:
            bootstrap_account(session, principal)
            entry = save_entry(
                session,
                principal,
                uuid4(),
                SaveEntry.model_validate(
                    {
                        "consumedDate": "2026-09-01",
                        "manualWine": {"name": "Before upgrade"},
                    }
                ),
            )
        migrate("downgrade", "0003_entries")
        migrate("upgrade", "head")
        with Session(engine) as session:
            from wine_journal.accounts.service import read_account
            from wine_journal.journal.edits import read_entry

            saved = read_entry(session, read_account(session, principal).id, entry.id)
            assert saved.version == 1 and saved.notes is None and saved.local_time is None
            assert saved.consumed_date == entry.consumed_date
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("UPDATE app.drinking_entries SET owner_id = owner_id"))
        migrate("check")
    finally:
        engine.dispose()
