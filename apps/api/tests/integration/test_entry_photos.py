from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import new_staging_key
from wine_journal.main import create_app
from wine_journal.media.models import UploadAsset
from wine_journal.media.uploads import RESERVATION_BYTES


@dataclass
class Photos:
    app: FastAPI
    client: TestClient
    engine: Engine
    admin: Engine
    people: list[Principal]
    owners: list[str]
    entries: list[str]
    assets: list[str]

    def sign_in(self, index: int) -> None:
        self.app.dependency_overrides[require_principal] = lambda: self.people[index]

    def url(self, entry: int = 0, asset: int | None = 0) -> str:
        base = f"/api/v1/entries/{self.entries[entry]}/photos"
        return base if asset is None else f"{base}/{self.assets[asset]}"


@pytest.fixture
def photos(database_urls: dict[str, SecretStr]) -> Iterator[Photos]:
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    with TestClient(app) as client:
        p = Photos(app, client, engine, admin, [], [], [], [])
        for index in range(2):
            p.people.append(Principal("https://entry-photos.test", uuid4()))
            p.sign_in(index)
            p.owners.append(client.post("/api/v1/me", json={}).json()["id"])
            entry = client.post(
                "/api/v1/entries",
                json={"consumedDate": "2026-10-01", "manualWine": {"name": "Photo test"}},
                headers={"Idempotency-Key": str(uuid4())},
            )
            assert entry.status_code == 200
            p.entries.append(entry.json()["id"])
            asset_id = uuid4()
            p.assets.append(str(asset_id))
            with Session(engine) as session, session.begin():
                session.add(
                    UploadAsset(
                        id=asset_id,
                        owner_id=UUID(p.owners[index]),
                        operation_key=uuid4(),
                        object_key=new_staging_key(asset_id),
                        declared_bytes=12,
                        declared_type="image/jpeg",
                        reserved_bytes=RESERVATION_BYTES,
                    )
                )
        p.sign_in(0)
        try:
            yield p
        finally:
            with admin.begin() as connection:
                for owner in p.owners:
                    connection.execute(
                        text("DELETE FROM app.drinking_entries WHERE owner_id = :owner"),
                        {"owner": owner},
                    )
                    connection.execute(
                        text("DELETE FROM app.upload_assets WHERE owner_id = :owner"),
                        {"owner": owner},
                    )
            engine.dispose()
            admin.dispose()


def test_attach_edit_remove_retries_keep_entry_independent(photos: Photos) -> None:
    p = photos
    assert p.client.get(p.url(asset=None)).json() == {"items": []}
    first = p.client.put(p.url(), json={})
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    assert first.json()["state"] == "PENDING"
    assert p.client.put(p.url(), json={}).json() == first.json()
    caption = {"version": 1, "caption": "Around the dinner table"}
    revised = p.client.patch(p.url(), json=caption)
    assert revised.json()["version"] == 2
    assert p.client.patch(p.url(), json=caption).json() == revised.json()
    assert p.client.patch(p.url(), json={**caption, "caption": "Stale"}).status_code == 409
    # Late attachment retries cannot reset a caption or duplicate the photo.
    assert p.client.put(p.url(), json={}).json() == revised.json()
    assert len(p.client.get(p.url(asset=None)).json()["items"]) == 1
    assert p.client.delete(p.url(), params={"version": 1}).status_code == 409
    assert p.client.delete(p.url(), params={"version": 2}).status_code == 200
    assert p.client.delete(p.url(), params={"version": 2}).status_code == 200
    assert p.client.put(p.url(), json={}).status_code == 409
    assert p.client.patch(p.url(), json={"version": 3, "caption": None}).status_code == 404
    assert p.client.get(p.url(asset=None)).json() == {"items": []}
    entry = p.client.get(f"/api/v1/entries/{p.entries[0]}").json()
    assert entry["version"] == 1 and entry["notes"] is None
    assert p.client.get(f"/api/v1/media/{p.assets[0]}").status_code == 200


def test_ownership_disabled_accounts_and_input_validation(photos: Photos) -> None:
    p = photos
    for entry, asset in ((0, 1), (1, 0), (1, 1)):
        assert p.client.put(p.url(entry, asset), json={}).status_code == 404
        assert (
            p.client.patch(p.url(entry, asset), json={"version": 1, "caption": None}).status_code
            == 404
        )
        assert p.client.delete(p.url(entry, asset), params={"version": 1}).status_code == 404
    assert p.client.get(p.url(1, None)).status_code == 404
    assert p.client.put(p.url(), json={"ownerId": p.owners[1]}).status_code == 422
    assert p.client.put(p.url(), json={}).status_code == 200
    for body in (
        {"version": 0, "caption": None},
        {"version": 1, "caption": "a" * 501},
        {"version": 1, "caption": "bad\x00caption"},
        {"version": 1},
    ):
        assert p.client.patch(p.url(), json=body).status_code == 422
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.app_users SET state = 'DISABLED' WHERE id = :id"), {"id": p.owners[0]}
        )
    for response in (
        p.client.get(p.url(asset=None)),
        p.client.put(p.url(), json={}),
        p.client.patch(p.url(), json={"version": 1, "caption": None}),
        p.client.delete(p.url(), params={"version": 1}),
    ):
        assert response.status_code == 403
        assert response.headers["cache-control"] == "no-store"


def test_parallel_attach_and_entry_deletion_preserve_storage(photos: Photos) -> None:
    p = photos
    barrier = Barrier(2)

    def attach() -> int:
        barrier.wait()
        return int(p.client.put(p.url(), json={}).status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: attach(), range(2))) == [200, 200]
    assert len(p.client.get(p.url(asset=None)).json()["items"]) == 1
    assert (
        p.client.delete(f"/api/v1/entries/{p.entries[0]}", params={"version": 1}).status_code == 200
    )
    assert p.client.put(p.url(), json={}).status_code == 404
    with p.engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM app.entry_photos WHERE entry_id = :id"),
                {"id": p.entries[0]},
            )
            == 0
        )
        assert (
            connection.scalar(
                text("SELECT reserved_bytes FROM app.upload_assets WHERE id = :id"),
                {"id": p.assets[0]},
            )
            == RESERVATION_BYTES
        )


def test_database_owner_constraints_and_restricted_grants(photos: Photos) -> None:
    p = photos
    for entry, asset in ((0, 1), (1, 0)):
        with pytest.raises(IntegrityError), p.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO app.entry_photos (owner_id, entry_id, asset_id) "
                    "VALUES (:owner, :entry, :asset)"
                ),
                {"owner": p.owners[0], "entry": p.entries[entry], "asset": p.assets[asset]},
            )
    assert p.client.put(p.url(), json={}).status_code == 200
    for sql in (
        "DELETE FROM app.entry_photos",
        "UPDATE app.entry_photos SET owner_id = owner_id",
        "UPDATE app.entry_photos SET asset_id = asset_id",
    ):
        with pytest.raises(ProgrammingError), p.engine.begin() as connection:
            connection.execute(text(sql))
    with p.admin.connect() as connection:
        for role in ("anon", "authenticated"):
            assert (
                connection.scalar(
                    text("SELECT has_table_privilege(:role, 'app.entry_photos', 'SELECT')"),
                    {"role": role},
                )
                is False
            )


def test_failed_photo_and_caption_leave_text_saved(photos: Photos) -> None:
    p = photos
    assert p.client.put(p.url(), json={}).status_code == 200
    with p.admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.upload_assets SET state = 'FAILED', "
                "processing_error = 'INVALID_IMAGE' WHERE id = :id"
            ),
            {"id": p.assets[0]},
        )
    listed = p.client.get(p.url(asset=None)).json()["items"]
    assert listed[0]["state"] == "FAILED" and listed[0]["errorCode"] == "PHOTO_PROCESSING_FAILED"
    assert "INVALID_IMAGE" not in str(listed)
    assert p.client.patch(p.url(), json={"version": 1, "caption": "   "}).json()["caption"] is None
    assert p.client.get(f"/api/v1/entries/{p.entries[0]}").json()["version"] == 1


def test_concurrent_last_slot_and_removal_respect_attachment_limit(photos: Photos) -> None:
    p = photos
    # Seed assets directly: this tests association bounds, independently of upload quota.
    assets = [str(uuid4()) for _ in range(13)]
    with Session(p.engine) as session, session.begin():
        for value in assets:
            identifier = UUID(value)
            session.add(
                UploadAsset(
                    id=identifier,
                    owner_id=UUID(p.owners[0]),
                    operation_key=uuid4(),
                    object_key=new_staging_key(identifier),
                    declared_bytes=12,
                    declared_type="image/jpeg",
                    reserved_bytes=RESERVATION_BYTES,
                )
            )
    base = p.url(asset=None)
    for asset in assets[:11]:
        assert p.client.put(f"{base}/{asset}", json={}).status_code == 200
    barrier = Barrier(2)

    def attach(asset: str) -> int:
        barrier.wait()
        return int(p.client.put(f"{base}/{asset}", json={}).status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attach, assets[11:]))
    assert sorted(outcomes) == [200, 409]
    assert len(p.client.get(base).json()["items"]) == 12
    assert p.client.put(f"{base}/{assets[0]}", json={}).status_code == 200
    rejected = assets[11 + outcomes.index(409)]
    assert p.client.delete(f"{base}/{assets[0]}", params={"version": 1}).status_code == 200
    assert p.client.put(f"{base}/{rejected}", json={}).status_code == 200
    assert p.client.put(f"{base}/{assets[0]}", json={}).status_code == 409
    assert len(p.client.get(base).json()["items"]) == 12


def test_same_owned_asset_can_be_shared_without_copying_or_cascade_loss(photos: Photos) -> None:
    p = photos
    another = p.client.post(
        "/api/v1/entries",
        json={"consumedDate": "2026-10-01", "manualWine": {"name": "Another wine at dinner"}},
        headers={"Idempotency-Key": str(uuid4())},
    ).json()["id"]
    shared_url = f"/api/v1/entries/{another}/photos/{p.assets[0]}"
    assert p.client.put(p.url(), json={}).status_code == 200
    assert p.client.put(shared_url, json={}).status_code == 200
    assert (
        p.client.delete(f"/api/v1/entries/{p.entries[0]}", params={"version": 1}).status_code == 200
    )
    assert len(p.client.get(f"/api/v1/entries/{another}/photos").json()["items"]) == 1
    assert p.client.get(f"/api/v1/media/{p.assets[0]}").status_code == 200


def test_entry_photo_migration_roundtrip(migrate: Callable[..., None]) -> None:
    migrate("downgrade", "0013_photo_publication")
    migrate("upgrade", "head")
    migrate("check")
