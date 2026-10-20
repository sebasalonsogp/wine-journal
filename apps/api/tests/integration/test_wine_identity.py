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
from wine_journal.journal.schemas import SaveEntry
from wine_journal.journal.service import save_entry
from wine_journal.journal.wine_identity import EditWineIdentity, edit_wine_identity
from wine_journal.main import create_app


def test_identity_preserves_ids_history_and_capture_retries(
    database_urls: dict[str, SecretStr],
) -> None:
    principal = Principal("https://identity.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        body = {"consumedDate": "2026-10-20", "manualWine": {"name": "Typo"}}
        headers = {"Idempotency-Key": str(uuid4())}
        first = client.post("/api/v1/entries", json=body, headers=headers).json()
        url = f"/api/v1/me/wines/{first['userWineId']}"
        before = client.get(url).json()
        second = client.post(
            "/api/v1/entries",
            json={"consumedDate": "2026-10-19", "releaseId": before["releaseId"]},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        client.put(f"{url}/rating", json={"version": 0, "score": 4.5})
        history = client.get(f"{url}/rating-history").json()
        corrected = {
            "name": "Correct label",
            "producer": "Estate",
            "vintageStatus": "YEAR",
            "year": 2022,
            "edition": "Reserve",
        }
        matching_entry = client.post(
            "/api/v1/entries",
            json={"consumedDate": "2026-10-20", "manualWine": corrected},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        matching_url = f"/api/v1/me/wines/{matching_entry['userWineId']}"
        matching_before = client.get(matching_url).json()
        response = client.put(f"{url}/identity", json={"version": 0, "wine": corrected})
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        saved = response.json()
        assert saved["id"] == before["id"] and saved["releaseId"] == before["releaseId"]
        assert saved["entryCount"] == 2 and saved["currentRating"] == 4.5
        assert saved["identityVersion"] == 1 and saved["canEditIdentity"] is True
        assert all(saved[key] == value for key, value in corrected.items())
        assert client.get(matching_url).json() == matching_before
        assert len(client.get("/api/v1/me/wines").json()["items"]) == 2
        assert client.get(f"{url}/rating-history").json() == history
        for entry in (first, second):
            assert client.get(f"/api/v1/entries/{entry['id']}").json() == entry
        assert client.post("/api/v1/entries", json=body, headers=headers).json() == first
        assert (
            client.put(f"{url}/identity", json={"version": 0, "wine": corrected}).status_code == 409
        )
        assert client.get(url).json() == saved
        for invalid in [
            {"version": True, "wine": corrected},
            {"version": -1, "wine": corrected},
            {"version": 1, "wine": {"name": " "}},
            {"version": 1, "wine": {"name": "Name", "year": 2020}},
            {"version": 1, "wine": {"name": "Name", "ownerId": str(uuid4())}},
            {"version": 1, "wine": corrected, "releaseId": str(uuid4())},
        ]:
            assert client.put(f"{url}/identity", json=invalid).status_code == 422
        cleared = client.put(
            f"{url}/identity", json={"version": 1, "wine": {"name": "Correct label"}}
        ).json()
        assert cleared["year"] is None and cleared["producer"] is None
        assert cleared["vintageStatus"] == "UNKNOWN" and cleared["identityVersion"] == 2
        other = Principal(principal.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        assert (
            client.put(f"{url}/identity", json={"version": 2, "wine": corrected}).status_code == 404
        )
        del app.dependency_overrides[require_principal]
        assert (
            client.put(f"{url}/identity", json={"version": 2, "wine": corrected}).status_code == 401
        )


def test_identity_concurrent_edits_have_one_winner(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://identity-race.test", uuid4())
    try:
        with Session(engine) as session:
            bootstrap_account(session, principal)
            entry = save_entry(
                session,
                principal,
                uuid4(),
                SaveEntry.model_validate(
                    {"consumedDate": "2026-10-20", "manualWine": {"name": "Original"}}
                ),
            )
        barrier = Barrier(2)

        def edit(name: str) -> int:
            barrier.wait()
            with Session(engine) as session:
                try:
                    result = edit_wine_identity(
                        session,
                        principal,
                        entry.user_wine_id,
                        EditWineIdentity.model_validate({"version": 0, "wine": {"name": name}}),
                    )
                    assert result.identity_version == 1
                    return 200
                except ApiError as error:
                    assert error.code == "IDENTITY_CONFLICT"
                    return 409

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(edit, ["First", "Second"])) == [200, 409]
    finally:
        engine.dispose()


def test_identity_migration_limits_grants(
    database_urls: dict[str, SecretStr], migrate: Callable[..., None]
) -> None:
    engine = database_engine(database_urls["runtime"])
    try:
        for table, columns in {
            "wine_definitions": ["id", "owner_id"],
            "wine_releases": ["id", "owner_id", "definition_id", "catalog_release_id"],
            "catalog_definitions": ["name"],
            "catalog_releases": ["year"],
        }.items():
            for column in columns:
                with engine.begin() as connection, pytest.raises(ProgrammingError):
                    connection.execute(text(f"UPDATE app.{table} SET {column} = {column}"))
        with engine.begin() as connection:
            connection.execute(text("UPDATE app.wine_definitions SET name = name WHERE false"))
            connection.execute(text("UPDATE app.wine_releases SET year = year WHERE false"))
        migrate("downgrade", "0024_entry_wine")
        with engine.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("UPDATE app.wine_definitions SET name = name"))
        migrate("upgrade", "head")
        migrate("check")
    finally:
        engine.dispose()


def test_shared_definition_and_disabled_account_are_protected(
    database_urls: dict[str, SecretStr],
) -> None:
    principal = Principal("https://identity-shared.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    try:
        with TestClient(app) as client:
            owner = client.post("/api/v1/me", json={}).json()["id"]
            entry = client.post(
                "/api/v1/entries",
                json={"consumedDate": "2026-10-20", "manualWine": {"name": "Shared"}},
                headers={"Idempotency-Key": str(uuid4())},
            ).json()
            url = f"/api/v1/me/wines/{entry['userWineId']}"
            wine = client.get(url).json()
            with admin.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO app.wine_releases"
                        " (id, owner_id, definition_id, vintage_status)"
                        " SELECT :new, owner_id, definition_id, 'UNKNOWN'"
                        " FROM app.wine_releases WHERE id = :id"
                    ),
                    {"new": uuid4(), "id": wine["releaseId"]},
                )
            assert client.get(url).json()["canEditIdentity"] is False
            body = {"version": 0, "wine": {"name": "Unexpected shared edit"}}
            assert client.put(f"{url}/identity", json=body).json()["error"]["code"] == (
                "IDENTITY_PROTECTED"
            )
            assert client.get(url).json()["name"] == "Shared"
            with admin.begin() as connection:
                connection.execute(
                    text("UPDATE app.app_users SET state = 'DISABLED' WHERE id = :owner"),
                    {"owner": owner},
                )
            assert client.put(f"{url}/identity", json=body).status_code == 403
    finally:
        admin.dispose()
