from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.integrations.storage import new_staging_key
from wine_journal.main import create_app
from wine_journal.media.models import UploadAsset
from wine_journal.media.uploads import RESERVATION_BYTES


@pytest.fixture
def covers(
    database_urls: dict[str, SecretStr],
) -> Iterator[tuple[TestClient, list[str], list[str]]]:
    engine = database_engine(database_urls["runtime"])
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    people = [Principal("https://covers.test", uuid4()) for _ in range(2)]
    wines, assets = [], []
    with TestClient(app) as client:
        for person in people:
            app.dependency_overrides[require_principal] = lambda person=person: person
            owner = UUID(client.post("/api/v1/me", json={}).json()["id"])
            entry = client.post(
                "/api/v1/entries",
                json={"consumedDate": "2026-10-01", "manualWine": {"name": "Cover wine"}},
                headers={"Idempotency-Key": str(uuid4())},
            ).json()
            wines.append(entry["userWineId"])
            for state in ("READY", "READY", "PENDING"):
                identifier = uuid4()
                assets.append(str(identifier))
                with Session(engine) as session, session.begin():
                    session.add(
                        UploadAsset(
                            id=identifier,
                            owner_id=owner,
                            operation_key=uuid4(),
                            object_key=new_staging_key(identifier),
                            declared_bytes=12,
                            declared_type="image/jpeg",
                            reserved_bytes=RESERVATION_BYTES,
                            state=state,
                            object_id=uuid4(),
                            object_etag="test",
                            display_bytes=12,
                            thumbnail_bytes=12,
                            width=1,
                            height=1,
                            thumbnail_width=1,
                            thumbnail_height=1,
                            display_sha256="a" * 64,
                            thumbnail_sha256="b" * 64,
                        )
                    )
        app.dependency_overrides[require_principal] = lambda: people[0]
        yield client, wines, assets
    engine.dispose()


def test_cover_replacement_removal_replay_and_memory_independence(
    covers: tuple[TestClient, list[str], list[str]],
) -> None:
    client, wines, assets = covers
    base = f"/api/v1/me/wines/{wines[0]}"
    original = client.get(base).json()
    assert original["coverAssetId"] is None and original["coverVersion"] == 0
    first = {"assetId": assets[0], "version": 0}
    result = client.put(base + "/cover", json=first)
    assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
    assert result.json() == {"assetId": assets[0], "version": 1}
    assert client.put(base + "/cover", json=first).json() == result.json()
    # Failed conversion and a stale tab cannot erase the working cover.
    assert client.put(base + "/cover", json={"assetId": assets[2], "version": 1}).status_code == 409
    assert client.put(base + "/cover", json={"assetId": assets[1], "version": 0}).status_code == 409
    assert (
        client.put(base + "/cover", json={"assetId": assets[1], "version": 1}).json()["version"]
        == 2
    )
    assert client.put(base + "/cover", json={"assetId": None, "version": 2}).json()["version"] == 3
    assert client.put(base + "/cover", json={"assetId": None, "version": 2}).status_code == 200
    assert client.put(base + "/cover", json=first).status_code == 409
    final = client.get(base).json()
    assert final == {**original, "coverVersion": 3}
    entries = client.get(base + "/entries").json()["items"]
    assert len(entries) == 1
    assert client.get(f"/api/v1/entries/{entries[0]['id']}/photos").json() == {"items": []}
    assert client.get(f"/api/v1/media/{assets[0]}").status_code == 200


def test_cover_ownership_validation_and_list_projection(
    covers: tuple[TestClient, list[str], list[str]],
) -> None:
    client, wines, assets = covers
    base = f"/api/v1/me/wines/{wines[0]}/cover"
    assert client.put(base, json={"assetId": assets[3], "version": 0}).status_code == 404
    assert (
        client.put(
            f"/api/v1/me/wines/{wines[1]}/cover", json={"assetId": assets[0], "version": 0}
        ).status_code
        == 404
    )
    for body in (
        {"assetId": None},
        {"assetId": None, "version": -1},
        {"assetId": None, "version": True},
        {"assetId": None, "version": 0, "ownerId": str(uuid4())},
    ):
        assert client.put(base, json=body).status_code == 422
    assert client.put(base, json={"assetId": assets[0], "version": 0}).status_code == 200
    assert client.get("/api/v1/me/wines").json()["items"][0]["coverAssetId"] == assets[0]


def test_concurrent_covers_do_not_overwrite_each_other(
    covers: tuple[TestClient, list[str], list[str]],
) -> None:
    client, wines, assets = covers
    barrier = Barrier(2)

    def replace(asset: str) -> int:
        barrier.wait()
        return int(
            client.put(
                f"/api/v1/me/wines/{wines[0]}/cover", json={"assetId": asset, "version": 0}
            ).status_code
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(replace, assets[:2])) == [200, 409]


def test_cover_constraints_and_disabled_accounts(
    covers: tuple[TestClient, list[str], list[str]], database_urls: dict[str, SecretStr]
) -> None:
    client, wines, assets = covers
    engine = database_engine(database_urls["runtime"])
    admin = database_engine(database_urls["migration"], role="wine_migrator")
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text("UPDATE app.user_wines SET cover_asset_id = :asset WHERE id = :wine"),
            {"asset": assets[3], "wine": wines[0]},
        )
    with pytest.raises(ProgrammingError), engine.begin() as connection:
        connection.execute(text("UPDATE app.user_wines SET owner_id = owner_id"))
    with admin.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.app_users SET state = 'DISABLED' "
                "WHERE id = (SELECT owner_id FROM app.user_wines WHERE id = :wine)"
            ),
            {"wine": wines[0]},
        )
        for role in ("anon", "authenticated"):
            assert (
                connection.scalar(
                    text("SELECT has_table_privilege(:role, 'app.user_wines', 'SELECT')"),
                    {"role": role},
                )
                is False
            )
    assert (
        client.put(
            f"/api/v1/me/wines/{wines[0]}/cover", json={"assetId": assets[0], "version": 0}
        ).status_code
        == 403
    )
    engine.dispose()
    admin.dispose()


def test_cover_migration_roundtrip(migrate: Callable[..., None]) -> None:
    migrate("downgrade", "0014_entry_photos")
    migrate("upgrade", "head")
    migrate("check")
