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
class AlbumFixture:
    app: FastAPI
    client: TestClient
    engine: Engine
    admin: Engine
    people: list[Principal]
    owners: list[str]
    entries: list[str]
    assets: list[str]
    occasions: list[str]

    def sign_in(self, index: int) -> None:
        self.app.dependency_overrides[require_principal] = lambda: self.people[index]

    def url(self, entry: int = 0, asset: int | None = 0) -> str:
        base = f"/api/v1/occasions/{self.occasions[entry]}/photos"
        return base if asset is None else f"{base}/{self.assets[asset]}"


@pytest.fixture
def album(database_urls: dict[str, SecretStr]) -> Iterator[AlbumFixture]:
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    with TestClient(app) as client:
        p = AlbumFixture(app, client, engine, admin, [], [], [], [], [])
        for index in range(2):
            p.people.append(Principal("https://entry-photos.test", uuid4()))
            p.sign_in(index)
            p.owners.append(client.post("/api/v1/me", json={}).json()["id"])
            occasion = client.post(
                "/api/v1/occasions",
                json={"occasionDate": "2026-10-12", "title": "Album fixture"},
                headers={"Idempotency-Key": str(uuid4())},
            )
            assert occasion.status_code == 200
            p.occasions.append(occasion.json()["id"])
            entry = client.post(
                "/api/v1/entries",
                json={
                    "consumedDate": "2026-10-01",
                    "manualWine": {"name": "Photo test"},
                    "occasionId": p.occasions[index],
                },
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
                        text("DELETE FROM app.occasions WHERE owner_id = :owner"), {"owner": owner}
                    )
                    connection.execute(
                        text("DELETE FROM app.upload_assets WHERE owner_id = :owner"),
                        {"owner": owner},
                    )
            engine.dispose()
            admin.dispose()


def test_occasion_photo_retries_captions_and_removal(album: AlbumFixture) -> None:
    p = album
    original = p.client.get(f"/api/v1/occasions/{p.occasions[0]}").json()
    first = p.client.put(p.url(), json={})
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    assert p.client.put(p.url(), json={}).json() == first.json()
    body = {"version": 1, "caption": "At the table"}
    updated = p.client.patch(p.url(), json=body)
    assert updated.json()["version"] == 2
    assert p.client.patch(p.url(), json=body).json() == updated.json()
    assert p.client.patch(p.url(), json={**body, "caption": "Stale"}).status_code == 409
    assert p.client.delete(p.url(), params={"version": 1}).status_code == 409
    assert p.client.delete(p.url(), params={"version": 2}).status_code == 200
    assert p.client.delete(p.url(), params={"version": 2}).status_code == 200
    assert p.client.put(p.url(), json={}).status_code == 409
    assert p.client.get(p.url(asset=None)).json() == {"items": []}
    assert p.client.get(f"/api/v1/occasions/{p.occasions[0]}").json() == original
    assert p.client.get(f"/api/v1/entries/{p.entries[0]}/photos").json() == {"items": []}


def test_occasion_photo_owner_constraints(album: AlbumFixture) -> None:
    p = album
    for occasion, asset in ((0, 1), (1, 0), (1, 1)):
        assert p.client.put(p.url(occasion, asset), json={}).status_code == 404
        assert (
            p.client.patch(p.url(occasion, asset), json={"version": 1, "caption": None}).status_code
            == 404
        )
        assert p.client.delete(p.url(occasion, asset), params={"version": 1}).status_code == 404
    assert p.client.get(p.url(1, None)).status_code == 404
    assert p.client.put(p.url(), json={"ownerId": p.owners[1]}).status_code == 422
    for occasion, asset in ((0, 1), (1, 0)):
        with pytest.raises(IntegrityError), p.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO app.occasion_photos (owner_id, occasion_id, asset_id) "
                    "VALUES (:owner, :occasion, :asset)"
                ),
                {"owner": p.owners[0], "occasion": p.occasions[occasion], "asset": p.assets[asset]},
            )
    with pytest.raises(ProgrammingError), p.engine.begin() as connection:
        connection.execute(text("DELETE FROM app.occasion_photos"))
    with p.admin.connect() as connection:
        for role in ("anon", "authenticated"):
            assert (
                connection.scalar(
                    text("SELECT has_table_privilege(:role, 'app.occasion_photos', 'SELECT')"),
                    {"role": role},
                )
                is False
            )


def test_occasion_photo_migration_roundtrip(migrate: Callable[..., None]) -> None:
    migrate("downgrade", "0015_wine_covers")
    migrate("upgrade", "head")
    migrate("check")


def owned_asset(p: AlbumFixture) -> str:
    asset_id = uuid4()
    with Session(p.engine) as session, session.begin():
        session.add(
            UploadAsset(
                id=asset_id,
                owner_id=UUID(p.owners[0]),
                operation_key=uuid4(),
                object_key=new_staging_key(asset_id),
                declared_bytes=12,
                declared_type="image/jpeg",
                reserved_bytes=RESERVATION_BYTES,
            )
        )
    return str(asset_id)


def test_album_deduplicates_and_preserves_original_references_after_unlink_delete(
    album: AlbumFixture,
) -> None:
    p = album
    occasion = p.occasions[0]
    url = f"/api/v1/occasions/{occasion}/album"
    shared = p.assets[0]
    general, entry_only, standalone_asset = [owned_asset(p) for _ in range(3)]
    second = p.client.post(
        "/api/v1/entries",
        json={
            "consumedDate": "2026-10-12",
            "manualWine": {"name": "Second wine"},
            "occasionId": occasion,
        },
        headers={"Idempotency-Key": str(uuid4())},
    ).json()
    standalone = p.client.post(
        "/api/v1/entries",
        json={"consumedDate": "2026-10-12", "manualWine": {"name": "Unlinked wine"}},
        headers={"Idempotency-Key": str(uuid4())},
    ).json()
    for entry, asset in (
        (p.entries[0], shared),
        (second["id"], shared),
        (p.entries[0], entry_only),
        (standalone["id"], standalone_asset),
    ):
        assert p.client.put(f"/api/v1/entries/{entry}/photos/{asset}", json={}).status_code == 200
    for asset in (general, shared):
        assert (
            p.client.put(f"/api/v1/occasions/{occasion}/photos/{asset}", json={}).status_code == 200
        )
    assert (
        p.client.patch(
            p.url(), json={"version": 1, "caption": "General occasion caption"}
        ).status_code
        == 200
    )
    result = p.client.get(url)
    assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
    items = result.json()["items"]
    assert {item["assetId"] for item in items} == {shared, general, entry_only}
    common = next(item for item in items if item["assetId"] == shared)
    assert common["sourceCount"] == 3
    assert common["source"]["caption"] == "General occasion caption"
    assert common["source"]["kind"] == "OCCASION"
    source_url = f"{url}/{shared}/sources"
    sources = p.client.get(source_url, params={"limit": 2}).json()
    assert sources["nextOffset"] == 2
    sources["items"] += p.client.get(source_url, params={"limit": 2, "offset": 2}).json()["items"]
    assert {item["parentId"] for item in sources["items"]} == {occasion, p.entries[0], second["id"]}
    # Each asset appears once across all album pages, even when references overlap.
    seen, cursor = [], None
    while True:
        page = p.client.get(
            url, params={"limit": 1, **({"cursor": cursor} if cursor else {})}
        ).json()
        seen += [item["assetId"] for item in page["items"]]
        cursor = page["nextCursor"]
        if cursor is None:
            break
    assert len(seen) == len(set(seen)) == 3
    link = f"/api/v1/occasions/{occasion}/entries/{p.entries[0]}"
    assert p.client.delete(link, params={"version": 1}).status_code == 200
    assert {item["assetId"] for item in p.client.get(url).json()["items"]} == {general, shared}
    assert len(p.client.get(f"/api/v1/entries/{p.entries[0]}/photos").json()["items"]) == 2
    assert (
        p.client.delete(f"/api/v1/occasions/{occasion}", params={"version": 1}).status_code == 200
    )
    assert p.client.get(url).status_code == 404
    assert p.client.get(source_url).status_code == 404
    assert p.client.put(p.url(), json={}).status_code == 404
    assert len(p.client.get(f"/api/v1/entries/{second['id']}/photos").json()["items"]) == 1
    for asset in (shared, general, entry_only, standalone_asset):
        assert p.client.get(f"/api/v1/media/{asset}").status_code == 200


def test_album_cursor_privacy_and_source_membership(album: AlbumFixture) -> None:
    p = album
    url = f"/api/v1/occasions/{p.occasions[0]}/album"
    other_url = f"/api/v1/occasions/{p.occasions[1]}/album"
    assert p.client.get(other_url).status_code == 404
    assert p.client.get(f"{url}/{p.assets[1]}/sources").status_code == 404
    assert p.client.get(f"{url}/{p.assets[0]}/sources").status_code == 404
    for asset in (p.assets[0], owned_asset(p)):
        assert (
            p.client.put(f"/api/v1/occasions/{p.occasions[0]}/photos/{asset}", json={}).status_code
            == 200
        )
    first = p.client.get(url, params={"limit": 1}).json()
    p.sign_in(1)
    assert p.client.get(other_url, params={"cursor": first["nextCursor"]}).status_code == 422
    p.sign_in(0)
    for cursor in ("bad", "W10=", "null"):
        assert p.client.get(url, params={"cursor": cursor}).status_code == 422
    assert p.client.get(url, params={"limit": 0}).status_code == 422
    assert p.client.get(url, params={"limit": 51}).status_code == 422
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.app_users SET state = 'DISABLED' WHERE id = :owner"),
            {"owner": p.owners[0]},
        )
    assert p.client.get(url).status_code == 403
    assert p.client.get(f"{url}/{p.assets[0]}/sources").status_code == 403
    assert p.client.put(p.url(), json={}).status_code == 403


def test_concurrent_occasion_photo_capacity_and_tombstone(album: AlbumFixture) -> None:
    p = album
    assets = [owned_asset(p) for _ in range(25)]
    base = p.url(asset=None)
    for asset in assets[:23]:
        assert p.client.put(f"{base}/{asset}", json={}).status_code == 200
    barrier = Barrier(2)

    def attach(asset: str) -> int:
        barrier.wait()
        return int(p.client.put(f"{base}/{asset}", json={}).status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attach, assets[23:]))
    assert sorted(outcomes) == [200, 409]
    assert len(p.client.get(base).json()["items"]) == 24
    assert p.client.delete(f"{base}/{assets[0]}", params={"version": 1}).status_code == 200
    rejected = assets[23 + outcomes.index(409)]
    assert p.client.put(f"{base}/{rejected}", json={}).status_code == 200
    assert p.client.put(f"{base}/{assets[0]}", json={}).status_code == 409


def test_removing_general_reference_keeps_shared_entry_photo_and_excludes_cover(
    album: AlbumFixture,
) -> None:
    p = album
    asset = p.assets[0]
    entry = p.client.get(f"/api/v1/entries/{p.entries[0]}").json()
    assert p.client.put(p.url(), json={}).status_code == 200
    entry_url = f"/api/v1/entries/{p.entries[0]}/photos/{asset}"
    assert p.client.put(entry_url, json={}).status_code == 200
    assert (
        p.client.patch(entry_url, json={"version": 1, "caption": "From the wine entry"}).status_code
        == 200
    )
    assert p.client.delete(p.url(), params={"version": 1}).status_code == 200
    cover = owned_asset(p)
    with p.admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.upload_assets SET state = 'READY', object_id = :object, "
                "object_etag = 'fixture', width = 1, height = 1, "
                "thumbnail_width = 1, thumbnail_height = 1, "
                "display_bytes = 1, thumbnail_bytes = 1, "
                "display_sha256 = :hash, thumbnail_sha256 = :hash "
                "WHERE id = :asset"
            ),
            {"asset": cover, "object": str(uuid4()), "hash": "a" * 64},
        )
    assert (
        p.client.put(
            f"/api/v1/me/wines/{entry['userWineId']}/cover", json={"assetId": cover, "version": 0}
        ).status_code
        == 200
    )
    url = f"/api/v1/occasions/{p.occasions[0]}/album"
    items = p.client.get(url).json()["items"]
    assert len(items) == 1 and items[0]["assetId"] == asset
    assert items[0]["sourceCount"] == 1
    assert items[0]["source"]["caption"] == "From the wine entry"
    assert items[0]["source"]["userWineId"] == entry["userWineId"]
    # Remove the fixture cover so its asset is no longer referenced at teardown.
    assert (
        p.client.put(
            f"/api/v1/me/wines/{entry['userWineId']}/cover", json={"assetId": None, "version": 1}
        ).status_code
        == 200
    )
