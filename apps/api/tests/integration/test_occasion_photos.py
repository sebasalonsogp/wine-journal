import json
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Barrier
from unittest.mock import Mock, patch
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
from wine_journal.core.errors import ApiError
from wine_journal.integrations.storage import Storage, new_staging_key
from wine_journal.main import create_app
from wine_journal.media.attachments import attach_photo
from wine_journal.media.cleanup import candidates, retire
from wine_journal.media.cleanup import main as cleanup_main
from wine_journal.media.models import UploadAsset
from wine_journal.media.routes import private_storage
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
                        text("DELETE FROM app.jobs WHERE owner_id = :owner"), {"owner": owner}
                    )
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


def ready_assets(p: AlbumFixture, *assets: str) -> None:
    with p.admin.begin() as connection:
        for asset in assets:
            connection.execute(
                text(
                    "UPDATE app.upload_assets SET state = 'READY', object_id = :object, "
                    "object_etag = 'fixture', width = 1, height = 1, "
                    "thumbnail_width = 1, thumbnail_height = 1, "
                    "display_bytes = 1, thumbnail_bytes = 1, "
                    "display_sha256 = :hash, thumbnail_sha256 = :hash WHERE id = :asset"
                ),
                {"asset": asset, "object": str(uuid4()), "hash": "a" * 64},
            )


def age_asset(p: AlbumFixture, asset: str) -> None:
    with p.admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.upload_assets SET created_at = now() - interval '2 days' WHERE id = :id"
            ),
            {"id": asset},
        )


@pytest.mark.parametrize(
    "hold", ["recent", "grant", "uncertain", "processing", "pending", "running"]
)
def test_retirement_preserves_live_or_uncertain_work(album: AlbumFixture, hold: str) -> None:
    p, asset = album, album.assets[0]
    age_asset(p, asset)
    with p.admin.begin() as connection:
        if hold == "recent":
            statement = "UPDATE app.upload_assets SET created_at = now() WHERE id = :id"
        elif hold == "grant":
            statement = (
                "UPDATE app.upload_assets SET grant_expires_at = now() + interval '1 hour' "
                "WHERE id = :id"
            )
        elif hold == "uncertain":
            statement = (
                "UPDATE app.upload_assets SET unsettled_grants = 1, "
                "grant_expires_at = now() - interval '1 day' WHERE id = :id"
            )
        elif hold == "processing":
            statement = (
                "UPDATE app.upload_assets SET state = 'PROCESSING', object_id = :object, "
                "object_etag = 'test' WHERE id = :id"
            )
        else:
            statement = """INSERT INTO app.jobs
                (id, owner_id, operation_key, kind, reference_id, state, lease_token, lease_until)
                VALUES (:object, :owner, :id, 'process_photo', :id, :state,
                        :token, :expiry)"""
        connection.execute(
            text(statement),
            {
                "id": asset,
                "owner": p.owners[0],
                "object": uuid4(),
                "state": hold.upper(),
                "token": uuid4() if hold == "running" else None,
                # Even an expired lease is not evidence that its external write has ended.
                "expiry": datetime.now(UTC) - timedelta(hours=1) if hold == "running" else None,
            },
        )
    assert (UUID(p.owners[0]), UUID(asset)) not in candidates(p.engine)
    assert not retire(p.engine, UUID(p.owners[0]), UUID(asset))


def test_retirement_checks_every_active_reference_and_rechecks_preview(album: AlbumFixture) -> None:
    p, asset = album, album.assets[0]
    age_asset(p, asset)
    owner = UUID(p.owners[0])
    assert (owner, UUID(asset)) in candidates(p.engine)
    ready_assets(p, asset)
    entry_url = f"/api/v1/entries/{p.entries[0]}/photos/{asset}"
    assert p.client.put(entry_url, json={}).status_code == 200
    assert p.client.put(p.url(), json={}).status_code == 200
    wine = p.client.get(f"/api/v1/entries/{p.entries[0]}").json()["userWineId"]
    cover_url = f"/api/v1/me/wines/{wine}/cover"
    assert p.client.put(cover_url, json={"assetId": asset, "version": 0}).status_code == 200
    try:
        assert not retire(p.engine, owner, UUID(asset))
        assert p.client.delete(entry_url, params={"version": 1}).status_code == 200
        assert not retire(p.engine, owner, UUID(asset))
        assert p.client.delete(p.url(), params={"version": 1}).status_code == 200
        assert not retire(p.engine, owner, UUID(asset))
    finally:
        assert p.client.put(cover_url, json={"assetId": None, "version": 1}).status_code == 200
    assert retire(p.engine, owner, UUID(asset))
    assert not retire(p.engine, owner, UUID(asset))


def test_retirement_fences_all_public_access_and_retains_quota(album: AlbumFixture) -> None:
    p, asset = album, album.assets[0]
    age_asset(p, asset)
    assert not retire(p.engine, UUID(p.owners[1]), UUID(asset))
    assert retire(p.engine, UUID(p.owners[0]), UUID(asset))
    with Session(p.engine) as session:
        record = session.get(UploadAsset, UUID(asset))
        assert record and record.retired_at and record.reserved_bytes == RESERVATION_BYTES
        operation = str(record.operation_key)
    storage = Mock(spec=Storage)
    p.app.dependency_overrides[private_storage] = lambda: storage
    assert p.client.get(f"/api/v1/media/{asset}").status_code == 404
    for suffix, body in (("complete", {}), ("view", {"variant": "thumbnail"})):
        assert p.client.post(f"/api/v1/media/{asset}/{suffix}", json=body).status_code == 404
    assert p.client.put(p.url(), json={}).status_code == 404
    assert (
        p.client.put(f"/api/v1/entries/{p.entries[0]}/photos/{asset}", json={}).status_code == 404
    )
    wine = p.client.get(f"/api/v1/entries/{p.entries[0]}").json()["userWineId"]
    assert (
        p.client.put(
            f"/api/v1/me/wines/{wine}/cover", json={"assetId": asset, "version": 0}
        ).status_code
        == 404
    )
    response = p.client.post(
        "/api/v1/media/uploads",
        json={"sizeBytes": 12, "contentType": "image/jpeg"},
        headers={"Idempotency-Key": operation},
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "UPLOAD_RETIRED"
    assert storage.mock_calls == []
    with p.engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text("UPDATE app.upload_assets SET retired_at = NULL WHERE id = :id"), {"id": asset}
        )


@pytest.mark.parametrize("attempt", range(3))
def test_retirement_serializes_with_a_new_attachment(album: AlbumFixture, attempt: int) -> None:
    p, asset = album, album.assets[0]
    age_asset(p, asset)
    barrier = Barrier(2)

    def attach() -> bool:
        barrier.wait(timeout=5)
        try:
            with Session(p.engine) as session:
                attach_photo(session, p.people[0], UUID(p.entries[0]), UUID(asset))
            return True
        except ApiError as error:
            assert error.status == 404
            return False

    def cleanup() -> bool:
        barrier.wait(timeout=5)
        return retire(p.engine, UUID(p.owners[0]), UUID(asset))

    with ThreadPoolExecutor(max_workers=2) as pool:
        attached, retired = pool.submit(attach), pool.submit(cleanup)
        assert attached.result(timeout=10) != retired.result(timeout=10)


def test_retirement_migration_preserves_rows_and_refuses_resurrection(
    album: AlbumFixture,
    migrate: Callable[..., None],
) -> None:
    p, asset = album, album.assets[0]
    migrate("downgrade", "0016_occasion_photos")
    migrate("upgrade", "head")
    migrate("check")
    assert p.client.get(f"/api/v1/media/{asset}").status_code == 200
    age_asset(p, asset)
    assert retire(p.engine, UUID(p.owners[0]), UUID(asset))
    with pytest.raises(AssertionError, match="Migration verification failed"):
        migrate("downgrade", "0016_occasion_photos")
    assert p.client.get(f"/api/v1/media/{asset}").status_code == 404
    for limit in (0, 101, True):
        with pytest.raises(ValueError):
            candidates(p.engine, limit=limit)


def test_retirement_command_previews_by_default_and_safely_replays(
    album: AlbumFixture,
    database_urls: dict[str, SecretStr],
    capsys: pytest.CaptureFixture[str],
) -> None:
    p = album
    age_asset(p, p.assets[0])
    with p.admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.upload_assets SET grant_expires_at = now() - interval '1 day' "
                "WHERE id = :id"
            ),
            {"id": p.assets[0]},
        )
    settings = Settings.model_construct(database_url=database_urls["runtime"])
    with patch("wine_journal.media.cleanup.Settings", return_value=settings):
        with patch("sys.argv", ["cleanup", "--limit", "1"]):
            assert cleanup_main() == 0
        assert json.loads(capsys.readouterr().out) == {
            "mode": "preview",
            "candidates": 1,
            "retired": 0,
            "filesDeleted": 0,
            "quotaReleased": 0,
        }
        assert p.client.get(f"/api/v1/media/{p.assets[0]}").status_code == 200
        with patch("sys.argv", ["cleanup", "--apply", "--limit", "1"]):
            assert cleanup_main() == 0
            assert json.loads(capsys.readouterr().out)["retired"] == 1
            assert cleanup_main() == 0
            assert json.loads(capsys.readouterr().out)["retired"] == 0
        with (
            patch("sys.argv", ["cleanup"]),
            patch(
                "wine_journal.media.cleanup.candidates", side_effect=RuntimeError("PRIVATE_VALUE")
            ),
        ):
            assert cleanup_main() == 1
            assert "PRIVATE_VALUE" not in capsys.readouterr().out


def test_wine_moments_exact_membership_dates_pagination_and_repeated_links(
    album: AlbumFixture,
) -> None:
    p = album
    entry = p.client.get(f"/api/v1/entries/{p.entries[0]}").json()
    wine = p.client.get(f"/api/v1/me/wines/{entry['userWineId']}").json()
    url = f"/api/v1/me/wines/{wine['id']}/moments"
    assert p.client.get(url).json() == {"items": [], "nextCursor": None}
    children = []
    for day, name, linked in (
        ("2026-10-14", None, True),
        ("2026-10-15", "Other wine", True),
        ("2026-10-16", None, False),
    ):
        child = p.client.post(
            "/api/v1/entries",
            json={
                "consumedDate": day,
                **({"manualWine": {"name": name}} if name else {"releaseId": wine["releaseId"]}),
                **({"occasionId": p.occasions[0]} if linked else {}),
            },
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert child.status_code == 200
        children.append(child.json()["id"])
    shared, general, own, tied, foreign_entry, standalone, pending, orphan = [
        owned_asset(p) for _ in range(8)
    ]
    ready_assets(p, shared, general, own, tied, foreign_entry, standalone, orphan)
    for parent, asset in (
        (p.entries[0], shared),
        (children[0], shared),
        (p.entries[0], own),
        (p.entries[0], tied),
        (children[1], foreign_entry),
        (children[2], standalone),
        (p.entries[0], pending),
    ):
        assert p.client.put(f"/api/v1/entries/{parent}/photos/{asset}", json={}).status_code == 200
    for asset in (shared, general):
        assert (
            p.client.put(f"/api/v1/occasions/{p.occasions[0]}/photos/{asset}", json={}).status_code
            == 200
        )
    result = p.client.get(url)
    assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
    items = result.json()["items"]
    expected = [standalone, shared, general, *sorted([own, tied])]
    assert [item["assetId"] for item in items] == expected
    assert items[1]["sourceCount"] == 3  # Two entry references, one occasion reference.
    assert items[1]["source"]["parentId"] == children[0]
    assert items[1]["source"]["sourceDate"] == "2026-10-14"
    assert items[2]["sourceCount"] == 1  # Repeated glasses do not multiply occasion references.
    preview = p.client.get(url, params={"limit": 3}).json()
    assert [item["assetId"] for item in preview["items"]] == expected[:3]
    remainder = p.client.get(url, params={"limit": 20, "cursor": preview["nextCursor"]}).json()
    assert [item["assetId"] for item in remainder["items"]] == expected[3:]
    assert remainder["nextCursor"] is None
    # Backdating changes the latest eligible source; equal dates prefer the entry.
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.drinking_entries SET consumed_date = '2026-10-12' WHERE id = :id"),
            {"id": children[0]},
        )
    shared_item = next(
        item for item in p.client.get(url).json()["items"] if item["assetId"] == shared
    )
    assert shared_item["source"]["kind"] == "ENTRY"
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.drinking_entries SET consumed_date = '2026-09-01' WHERE id = :id"),
            {"id": children[0]},
        )
    shared_item = next(
        item for item in p.client.get(url).json()["items"] if item["assetId"] == shared
    )
    assert shared_item["source"]["kind"] == "OCCASION"
    assert shared_item["source"]["sourceDate"] == "2026-10-12"
    for parent in (p.entries[0], children[0]):
        assert (
            p.client.delete(
                f"/api/v1/occasions/{p.occasions[0]}/entries/{parent}", params={"version": 1}
            ).status_code
            == 200
        )
    assert {item["assetId"] for item in p.client.get(url).json()["items"]} == {
        standalone,
        shared,
        own,
        tied,
    }
    assert (
        p.client.delete(f"/api/v1/occasions/{p.occasions[0]}", params={"version": 1}).status_code
        == 200
    )
    assert {item["assetId"] for item in p.client.get(url).json()["items"]} == {
        standalone,
        shared,
        own,
        tied,
    }


def test_wine_moments_cover_exclusion_removal_and_readiness(album: AlbumFixture) -> None:
    p = album
    wine_id = p.client.get(f"/api/v1/entries/{p.entries[0]}").json()["userWineId"]
    url = f"/api/v1/me/wines/{wine_id}/moments"
    asset = p.assets[0]
    assert (
        p.client.put(f"/api/v1/entries/{p.entries[0]}/photos/{asset}", json={}).status_code == 200
    )
    assert p.client.get(url).json()["items"] == []
    with p.admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.upload_assets SET state = 'FAILED', "
                "processing_error = 'INVALID_IMAGE' WHERE id = :id"
            ),
            {"id": asset},
        )
    assert p.client.get(url).json()["items"] == []
    with p.admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.upload_assets SET state = 'PENDING', processing_error = NULL "
                "WHERE id = :id"
            ),
            {"id": asset},
        )
    ready_assets(p, asset)
    assert len(p.client.get(url).json()["items"]) == 1
    cover_url = f"/api/v1/me/wines/{wine_id}/cover"
    assert p.client.put(cover_url, json={"assetId": asset, "version": 0}).status_code == 200
    try:
        assert p.client.get(url).json()["items"] == []
    finally:
        assert p.client.put(cover_url, json={"assetId": None, "version": 1}).status_code == 200
    assert len(p.client.get(url).json()["items"]) == 1
    assert (
        p.client.delete(
            f"/api/v1/entries/{p.entries[0]}/photos/{asset}", params={"version": 1}
        ).status_code
        == 200
    )
    assert p.client.get(url).json()["items"] == []


def test_wine_moments_authorization_and_scoped_cursor(album: AlbumFixture) -> None:
    p = album
    wine_id = p.client.get(f"/api/v1/entries/{p.entries[0]}").json()["userWineId"]
    url = f"/api/v1/me/wines/{wine_id}/moments"
    for asset in (p.assets[0], owned_asset(p)):
        ready_assets(p, asset)
        assert (
            p.client.put(f"/api/v1/entries/{p.entries[0]}/photos/{asset}", json={}).status_code
            == 200
        )
    cursor = p.client.get(url, params={"limit": 1}).json()["nextCursor"]
    for params in ({"limit": 0}, {"limit": 51}, {"cursor": "bad"}, {"cursor": "W10="}):
        assert p.client.get(url, params=params).status_code == 422
    p.sign_in(1)
    assert p.client.get(url).status_code == 404
    other_id = p.client.get(f"/api/v1/entries/{p.entries[1]}").json()["userWineId"]
    assert (
        p.client.get(f"/api/v1/me/wines/{other_id}/moments", params={"cursor": cursor}).status_code
        == 422
    )
    p.sign_in(0)
    p.app.dependency_overrides.pop(require_principal)
    assert p.client.get(url).status_code == 401
    p.sign_in(0)
    with p.admin.begin() as connection:
        connection.execute(
            text("UPDATE app.app_users SET state = 'DISABLED' WHERE id = :id"), {"id": p.owners[0]}
        )
    assert p.client.get(url).status_code == 403


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
