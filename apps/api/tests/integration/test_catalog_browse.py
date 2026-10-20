from collections.abc import Iterator
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from wine_journal.catalog.importer import import_catalog
from wine_journal.catalog.models import CatalogSource
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.main import create_app

ROOT = Path(__file__).resolve().parents[4]
PUBLIC_KEYS = {"id", "name", "producer", "vintageStatus", "year", "edition"}


@pytest.fixture
def catalog(database_urls: dict[str, SecretStr]) -> Iterator[tuple[TestClient, Engine]]:
    engine = database_engine(database_urls["migration"], role="wine_migrator")
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    import_catalog(engine, ROOT / "assets/evaluation/manifest.csv", apply=True)
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM app.catalog_sources"))
            connection.execute(text("DELETE FROM app.catalog_releases"))
            connection.execute(text("DELETE FROM app.catalog_definitions"))
        engine.dispose()


def test_guest_browses_all_releases_once_and_searches_specific_vintages(
    catalog: tuple[TestClient, Engine],
) -> None:
    client, _ = catalog
    ids: list[str] = []
    offset: int | None = 0
    while offset is not None:
        response = client.get("/api/v1/catalog/wines", params={"limit": 7, "offset": offset})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        page = response.json()
        assert all(set(wine) == PUBLIC_KEYS for wine in page["items"])
        ids.extend(wine["id"] for wine in page["items"])
        offset = page["nextOffset"]
    assert len(ids) == len(set(ids)) == 30
    pair = client.get("/api/v1/catalog/wines", params={"q": "RIDGE monte bello"}).json()["items"]
    assert len(pair) == 2 and pair[0]["year"] > pair[1]["year"]
    result = client.get(
        "/api/v1/catalog/wines", params={"q": f"monte {pair[1]['year']} ridge"}
    ).json()
    assert [wine["id"] for wine in result["items"]] == [pair[1]["id"]]
    assert result["nextOffset"] is None
    for query in ("does-not-exist", "%", "_", "' OR 1=1 --"):
        assert client.get("/api/v1/catalog/wines", params={"q": query}).json()["items"] == []


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 49}, {"offset": -1}, {"offset": 10001}, {"q": "a" * 201}, {"q": "\0"}],
)
def test_public_query_is_bounded(
    catalog: tuple[TestClient, Engine], params: dict[str, str | int]
) -> None:
    client, _ = catalog
    assert client.get("/api/v1/catalog/wines", params=params).status_code == 422


def test_public_details_sources_and_missing_release(catalog: tuple[TestClient, Engine]) -> None:
    client, _ = catalog
    wines = client.get("/api/v1/catalog/wines", params={"q": "krug"}).json()["items"]
    assert len(wines) == 2 and wines[0]["edition"] != wines[1]["edition"]
    for wine in wines:
        response = client.get(f"/api/v1/catalog/wines/{wine['id']}")
        detail = response.json()
        assert set(detail) == PUBLIC_KEYS | {"sources"}
        assert detail["vintageStatus"] == "MULTI_VINTAGE"
        assert detail["year"] is None
        assert len(detail["sources"]) == 1
        assert set(detail["sources"][0]) == {"url", "retrievedOn"}
        assert detail["sources"][0]["url"].startswith("https://")
    assert client.get(f"/api/v1/catalog/wines/{uuid4()}").status_code == 404
    assert client.get("/api/v1/catalog/wines/not-a-uuid").status_code == 422


def test_invalid_outbound_sources_are_omitted_and_repeated_observations_deduplicated(
    catalog: tuple[TestClient, Engine],
) -> None:
    client, engine = catalog
    wine = client.get("/api/v1/catalog/wines").json()["items"][0]
    with Session(engine) as session, session.begin():
        source = session.scalar(select(CatalogSource).where(CatalogSource.release_id == wine["id"]))
        assert source is not None
        for url in (
            "https://user:secret@example.com/wine",
            "https://example.com/wine?token=secret",
            "https://example.com:bad/wine",
            "https://%zz.example.com/wine",
            "https://example.com\\@evil.test/wine",
            "https://example.com/\nunsafe",
            source.url,
        ):
            session.add(
                CatalogSource(
                    release_id=source.release_id,
                    url=url,
                    retrieved_on=date(2026, 10, 20),
                    market="UNVERIFIED",
                    evidence_status="SOURCE_ONLY",
                )
            )
    detail = client.get(f"/api/v1/catalog/wines/{wine['id']}").json()
    assert len(detail["sources"]) == 1
    assert detail["sources"][0]["retrievedOn"] == "2026-10-20"
    with Session(engine) as session, session.begin():
        session.execute(
            text("DELETE FROM app.catalog_sources WHERE release_id = :id"), {"id": wine["id"]}
        )
    assert client.get(f"/api/v1/catalog/wines/{wine['id']}").json()["sources"] == []


def test_private_wines_never_appear_and_browsing_creates_no_entries(
    catalog: tuple[TestClient, Engine],
) -> None:
    client, engine = catalog
    principal = Principal("https://catalog-browse.test", uuid4())
    app = client.app
    assert hasattr(app, "dependency_overrides")
    app.dependency_overrides[require_principal] = lambda: principal
    assert client.post("/api/v1/me", json={}).status_code == 200
    saved = client.post(
        "/api/v1/entries",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "consumedDate": "2026-10-20",
            "manualWine": {"name": "Secret family bottle"},
            "notes": "Private dinner memory",
        },
    )
    assert saved.status_code == 200
    private_release = client.get("/api/v1/me/wines").json()["items"][0]["releaseId"]
    with engine.connect() as connection:
        before = connection.scalar(text("SELECT count(*) FROM app.drinking_entries"))
    app.dependency_overrides.clear()
    assert client.get("/api/v1/me/wines").status_code == 401
    assert client.get(f"/api/v1/catalog/wines/{private_release}").status_code == 404
    assert client.get("/api/v1/catalog/wines", params={"q": "Secret family"}).json()["items"] == []
    response = client.get("/api/v1/catalog/wines")
    assert "Private dinner memory" not in response.text
    for wine in response.json()["items"]:
        assert client.get(f"/api/v1/catalog/wines/{wine['id']}").status_code == 200
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM app.drinking_entries")) == before
