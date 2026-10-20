import hashlib
import os
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.catalog.models import CatalogDefinition, CatalogRelease, WineRelease
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.journal.models import EntrySave
from wine_journal.journal.schemas import SaveEntry
from wine_journal.journal.service import save_entry
from wine_journal.main import create_app


@pytest.fixture
def releases(database_urls: dict[str, SecretStr]) -> Iterator[tuple[UUID, UUID]]:
    engine = database_engine(database_urls["migration"], role="wine_migrator")
    definition_id, first, second = uuid4(), uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add(
            CatalogDefinition(
                id=definition_id, key=f"capture-{uuid4()}", name="Shared label", producer="Estate"
            )
        )
        session.flush()
        session.add_all(
            [
                CatalogRelease(
                    id=first, definition_id=definition_id, vintage_status="YEAR", year=2021
                ),
                CatalogRelease(
                    id=second, definition_id=definition_id, vintage_status="YEAR", year=2022
                ),
            ]
        )
    try:
        yield first, second
    finally:
        # Only this fixture's public links, in the guarded disposable test database.
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE app.wine_releases SET catalog_release_id = NULL "
                    "WHERE catalog_release_id IN (:a, :b)"
                ),
                {"a": first, "b": second},
            )
            connection.execute(
                text("DELETE FROM app.catalog_releases WHERE definition_id = :id"),
                {"id": definition_id},
            )
            connection.execute(
                text("DELETE FROM app.catalog_definitions WHERE id = :id"), {"id": definition_id}
            )
        engine.dispose()


def test_catalog_save_reuses_owner_wine_but_keeps_vintages_and_accounts_separate(
    database_urls: dict[str, SecretStr], releases: tuple[UUID, UUID]
) -> None:
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    principal = Principal("https://catalog-capture.test", uuid4())
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        body = {
            "consumedDate": "2026-10-20",
            "catalogReleaseId": str(releases[0]),
            "notes": "Private memory",
        }
        key = {"Idempotency-Key": str(uuid4())}
        first = client.post("/api/v1/entries", json=body, headers=key)
        assert first.status_code == 200
        assert client.post("/api/v1/entries", json=body, headers=key).json() == first.json()
        repeat = client.post(
            "/api/v1/entries", json=body, headers={"Idempotency-Key": str(uuid4())}
        ).json()
        assert repeat["id"] != first.json()["id"]
        assert repeat["userWineId"] == first.json()["userWineId"]
        other_vintage = client.post(
            "/api/v1/entries",
            json={**body, "catalogReleaseId": str(releases[1])},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        assert other_vintage["userWineId"] != repeat["userWineId"]
        assert (
            client.post(
                "/api/v1/entries", json={**body, "catalogReleaseId": str(releases[1])}, headers=key
            ).status_code
            == 409
        )
        manual = client.post(
            "/api/v1/entries",
            json={
                "consumedDate": "2026-10-20",
                "manualWine": {
                    "name": "Shared label",
                    "producer": "Estate",
                    "vintageStatus": "YEAR",
                    "year": 2021,
                },
            },
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        assert manual["userWineId"] not in {repeat["userWineId"], other_vintage["userWineId"]}
        detail = client.get(f"/api/v1/me/wines/{repeat['userWineId']}").json()
        assert detail["name"] == "Shared label" and detail["year"] == 2021
        private_id = detail["releaseId"]
        principal = Principal(principal.issuer, uuid4())
        client.post("/api/v1/me", json={})
        second_owner = client.post("/api/v1/entries", json=body, headers=key).json()
        assert second_owner["userWineId"] != repeat["userWineId"]
        for payload in (
            {"releaseId": private_id},
            {"releaseId": str(releases[0])},
            {"catalogReleaseId": private_id},
        ):
            response = client.post(
                "/api/v1/entries",
                json={"consumedDate": "2026-10-20", **payload},
                headers={"Idempotency-Key": str(uuid4())},
            )
            assert response.status_code == 404
        app.dependency_overrides.clear()
        assert client.post("/api/v1/entries", json=body, headers=key).status_code == 401
        assert "Private memory" not in client.get(f"/api/v1/catalog/wines/{releases[0]}").text


def test_concurrent_distinct_catalog_saves_share_one_owned_identity(
    database_urls: dict[str, SecretStr], releases: tuple[UUID, UUID]
) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://catalog-concurrent.test", uuid4())
    with Session(engine, expire_on_commit=False) as session:
        owner_id = bootstrap_account(session, principal).id
    body = SaveEntry.model_validate(
        {"consumedDate": "2026-10-20", "catalogReleaseId": str(releases[0])}
    )

    def save(_: int) -> tuple[UUID, UUID]:
        with Session(engine, expire_on_commit=False) as session:
            entry = save_entry(session, principal, uuid4(), body)
            return entry.id, entry.user_wine_id

    try:
        with ThreadPoolExecutor(max_workers=4) as workers:
            entries = list(workers.map(save, range(8)))
        assert len({entry[0] for entry in entries}) == 8
        assert len({entry[1] for entry in entries}) == 1
        with Session(engine) as session:
            assert (
                len(
                    session.scalars(
                        select(WineRelease).where(WineRelease.owner_id == owner_id)
                    ).all()
                )
                == 1
            )
    finally:
        engine.dispose()


def test_catalog_failure_rolls_back_occasion_receipt_and_identity(
    database_urls: dict[str, SecretStr], releases: tuple[UUID, UUID]
) -> None:
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    principal = Principal("https://catalog-rollback.test", uuid4())
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        owner = client.post("/api/v1/me", json={}).json()["id"]
        headers = {"Idempotency-Key": str(uuid4())}
        body = {
            "consumedDate": "2026-10-20",
            "catalogReleaseId": str(uuid4()),
            "newOccasion": {"occasionDate": "2026-10-20", "title": "Dinner"},
        }
        assert client.post("/api/v1/entries", json=body, headers=headers).status_code == 404
        assert client.get("/api/v1/occasions").json()["items"] == []
        assert client.get("/api/v1/me/wines").json()["items"] == []
        engine = database_engine(database_urls["runtime"])
        try:
            with Session(engine) as session:
                assert (
                    session.get(EntrySave, (UUID(owner), UUID(headers["Idempotency-Key"]))) is None
                )
        finally:
            engine.dispose()
        assert (
            client.post(
                "/api/v1/entries",
                json={**body, "catalogReleaseId": str(releases[0])},
                headers=headers,
            ).status_code
            == 200
        )
        for extra in ({"releaseId": str(uuid4())}, {"manualWine": {"name": "Other"}}):
            assert (
                client.post(
                    "/api/v1/entries",
                    json={**body, **extra},
                    headers={"Idempotency-Key": str(uuid4())},
                ).status_code
                == 422
            )


def test_legacy_manual_receipt_digest_does_not_change(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    principal = Principal("https://catalog-legacy.test", uuid4())
    body = SaveEntry.model_validate(
        {"consumedDate": "2026-10-20", "manualWine": {"name": "Legacy wine"}}
    )
    key = uuid4()
    try:
        with Session(engine, expire_on_commit=False) as session:
            owner = bootstrap_account(session, principal)
            entry = save_entry(session, principal, key, body)
            old_digest = hashlib.sha256(
                body.model_dump_json(
                    exclude={"catalog_release_id", "occasion_id", "new_occasion", "notes"}
                ).encode()
            ).hexdigest()
            receipt = session.get(EntrySave, (owner.id, key))
            assert receipt is not None and receipt.request_hash == old_digest
            session.rollback()
            assert save_entry(session, principal, key, body).id == entry.id
    finally:
        engine.dispose()


def test_catalog_links_enforce_uniqueness_snapshot_and_safe_downgrade(
    database_urls: dict[str, SecretStr], releases: tuple[UUID, UUID]
) -> None:
    runtime = database_engine(database_urls["runtime"])
    migration = database_engine(database_urls["migration"], role="wine_migrator")
    principal = Principal("https://catalog-constraints.test", uuid4())
    body = SaveEntry.model_validate(
        {
            "consumedDate": "2026-10-20",
            "catalogReleaseId": str(releases[0]),
        }
    )
    try:
        with Session(runtime, expire_on_commit=False) as session:
            owner = bootstrap_account(session, principal)
            original = save_entry(session, principal, uuid4(), body)
            owned = session.scalar(select(WineRelease).where(WineRelease.owner_id == owner.id))
            assert owned is not None
            definition_id, release_id = owned.definition_id, owned.id
        for public_id in (releases[0], uuid4()):
            with Session(runtime) as session, pytest.raises(IntegrityError), session.begin():
                session.add(
                    WineRelease(
                        owner_id=owner.id,
                        definition_id=definition_id,
                        catalog_release_id=public_id,
                        vintage_status="YEAR",
                        year=2021,
                    )
                )
                session.flush()
        with runtime.begin() as connection, pytest.raises(ProgrammingError):
            connection.execute(
                text("UPDATE app.wine_releases SET catalog_release_id = NULL WHERE id = :id"),
                {"id": release_id},
            )
        with migration.begin() as connection:
            connection.execute(
                text("UPDATE app.catalog_releases SET year = 2020 WHERE id = :id"),
                {"id": releases[0]},
            )
        with Session(runtime) as session:
            repeat = save_entry(session, principal, uuid4(), body)
            assert repeat.user_wine_id == original.user_wine_id
            snapshot = session.get(WineRelease, release_id)
            assert snapshot is not None and snapshot.year == 2021
        environment = dict(os.environ)
        environment["WINE_JOURNAL_MIGRATION_DATABASE_URL"] = database_urls[
            "migration"
        ].get_secret_value()
        with migration.connect() as connection:
            previous_revision = connection.scalar(
                text("SELECT version_num FROM app.alembic_version")
            )
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "0022_public_catalog"],
            env=environment,
            capture_output=True,
        )
        assert result.returncode != 0, "Populated catalog links must block downgrade."
        with migration.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM app.alembic_version"))
                == previous_revision
            )
            assert (
                connection.scalar(
                    text("SELECT catalog_release_id FROM app.wine_releases WHERE id = :id"),
                    {"id": release_id},
                )
                == releases[0]
            )
    finally:
        runtime.dispose()
        migration.dispose()
