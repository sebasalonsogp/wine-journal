import json
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from wine_journal.catalog.barcode_importer import import_barcodes
from wine_journal.catalog.importer import import_catalog
from wine_journal.catalog.models import CatalogBarcodeObservation, CatalogDefinition, CatalogRelease
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.main import create_app

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = ROOT / "assets/catalog/barcode-evidence.json"
LOOKUP = "/api/v1/identification/barcode-lookups"
CONFIRM = "/api/v1/identification/barcode-confirmations"
CODE = "089121288122"


@pytest.fixture
def barcode_api(database_urls: dict[str, SecretStr]) -> Iterator[tuple[TestClient, Engine]]:
    engine = database_engine(database_urls["migration"], role="wine_migrator")
    import_catalog(engine, ROOT / "assets/evaluation/manifest.csv", apply=True)
    import_barcodes(engine, MANIFEST, apply=True)
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE app.wine_releases SET catalog_release_id = NULL "
                    "WHERE catalog_release_id IN (SELECT id FROM app.catalog_releases)"
                )
            )
            for table in (
                "catalog_barcode_observations",
                "catalog_sources",
                "catalog_releases",
                "catalog_definitions",
            ):
                connection.execute(text(f"DELETE FROM app.{table}"))
        engine.dispose()


def selection(client: TestClient, gtin: str = CODE) -> dict[str, object]:
    wine = client.post(LOOKUP, json={"gtin": gtin}).json()["candidates"][0]["releases"][0]
    return {
        "gtin": gtin,
        "catalogReleaseId": wine["id"],
        "vintageStatus": wine["vintageStatus"],
        "year": wine["year"],
        "edition": wine["edition"],
    }


def test_guest_lookup_normalizes_and_requires_explicit_vintage(
    barcode_api: tuple[TestClient, Engine],
) -> None:
    client, engine = barcode_api
    with engine.connect() as connection:
        before = connection.scalar(text("SELECT count(*) FROM app.user_wines"))
    first = client.post(LOOKUP, json={"gtin": CODE})
    assert first.status_code == 200 and first.headers["cache-control"] == "no-store"
    result = first.json()
    assert result == client.post(LOOKUP, json={"gtin": "00089121288122"}).json()
    assert result["status"] == "NEEDS_CONFIRMATION"
    assert set(result) == {"gtin", "status", "candidates"}
    candidate = result["candidates"][0]
    assert len(result["candidates"]) == 1 and len(candidate["sources"]) == 2
    assert set(candidate) == {
        "definitionId",
        "name",
        "producer",
        "bottleSizesMl",
        "sources",
        "releases",
    }
    assert candidate["bottleSizesMl"] == [750]
    assert {wine["year"] for wine in candidate["releases"]} == {2022, 2023}
    for wine in candidate["releases"]:
        body = {
            "gtin": CODE,
            "catalogReleaseId": wine["id"],
            "vintageStatus": "YEAR",
            "year": wine["year"],
            "edition": wine["edition"],
        }
        response = client.post(CONFIRM, json=body)
        assert response.status_code == 200 and response.json()["id"] == wine["id"]
        assert response.headers["cache-control"] == "no-store"
        assert (
            client.post(CONFIRM, json={k: v for k, v in body.items() if k != "year"}).status_code
            == 422
        )
        assert client.post(CONFIRM, json={**body, "year": 2000}).status_code == 409
    # Reads and confirmation create no account, wine, or entry.
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM app.user_wines")) == before


@pytest.mark.parametrize(
    "gtin",
    [
        12345678,
        "123",
        "00000000000000",
        "089121288123",
        "10089121288129",
        " 089121288122",
        "x" * 1000,
    ],
)
def test_invalid_codes_are_rejected(barcode_api: tuple[TestClient, Engine], gtin: object) -> None:
    client, _ = barcode_api
    response = client.post(LOOKUP, json={"gtin": gtin})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_private_or_unrelated_release_cannot_be_confirmed(
    barcode_api: tuple[TestClient, Engine],
) -> None:
    client, _ = barcode_api
    assert client.post(LOOKUP, json={"gtin": "4006381333931"}).json()["status"] == "NOT_FOUND"
    body = selection(client)
    assert client.post(CONFIRM, json={**body, "catalogReleaseId": str(uuid4())}).status_code == 409
    other = client.get("/api/v1/catalog/wines", params={"q": "monte bello"}).json()["items"][0]
    assert (
        client.post(
            CONFIRM, json={**body, "catalogReleaseId": other["id"], "year": other["year"]}
        ).status_code
        == 409
    )
    assert client.post(CONFIRM, json={**body, "edition": "Invented"}).status_code == 409
    assert (
        client.post(
            CONFIRM, json={**body, "vintageStatus": "NON_VINTAGE", "year": None}
        ).status_code
        == 409
    )


def test_bad_stored_source_is_neither_exposed_nor_used(
    barcode_api: tuple[TestClient, Engine],
) -> None:
    client, engine = barcode_api
    body = selection(client)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE app.catalog_barcode_observations "
                "SET url = 'https://example.com/' || id || '?secret=hidden'"
            )
        )
    assert client.post(LOOKUP, json={"gtin": CODE}).json() == {
        "gtin": "00089121288122",
        "status": "NOT_FOUND",
        "candidates": [],
    }
    assert client.post(CONFIRM, json=body).status_code == 409


def test_retraction_preview_exactness_and_stale_confirmation(
    barcode_api: tuple[TestClient, Engine], tmp_path: Path
) -> None:
    client, engine = barcode_api
    body = selection(client)
    result = import_barcodes(engine, MANIFEST, retract=True)
    assert (result.observations, result.package_codes, result.applied) == (5, 4, False)
    assert client.post(CONFIRM, json=body).status_code == 200
    rows = json.loads(MANIFEST.read_text())
    rows[-1]["bottle_ml"] = 375
    path = tmp_path / "conflict.json"
    path.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="conflicts"):
        import_barcodes(engine, path, retract=True, apply=True)
    assert client.post(CONFIRM, json=body).status_code == 200
    # Removing one of two valid sources keeps the offering usable.
    path.write_text(json.dumps(rows[:1]))
    partial = import_barcodes(engine, path, retract=True, apply=True)
    assert (partial.observations, partial.package_codes) == (1, 0)
    assert client.post(CONFIRM, json=body).status_code == 200
    result = import_barcodes(engine, MANIFEST, retract=True, apply=True)
    assert (result.observations, result.package_codes) == (4, 4)
    assert client.post(CONFIRM, json=body).status_code == 409
    assert import_barcodes(engine, MANIFEST, retract=True, apply=True).observations == 0


@pytest.mark.parametrize("offering", ["krug-grande-cuvee", "grahams-10-year-old-tawny"])
def test_ambiguity_non_vintage_edition_and_one_release_still_need_confirmation(
    barcode_api: tuple[TestClient, Engine],
    offering: str,
) -> None:
    client, engine = barcode_api
    with Session(engine) as session, session.begin():
        sources = session.scalars(
            select(CatalogBarcodeObservation).where(
                CatalogBarcodeObservation.gtin == "00089121288122"
            )
        ).all()
        definition = session.scalar(
            select(CatalogDefinition).where(CatalogDefinition.key == offering)
        )
        assert definition is not None
        sources[0].definition_id = definition.id
        sources[0].bottle_ml = 375
        other = sources[1].definition_id
        # Keep a single catalog release on the original offering.
        release = session.scalar(
            select(CatalogRelease).where(
                CatalogRelease.definition_id == other, CatalogRelease.year == 2022
            )
        )
        assert release is not None
        session.execute(
            text("DELETE FROM app.catalog_sources WHERE release_id = :id"), {"id": release.id}
        )
        session.delete(release)
    result = client.post(LOOKUP, json={"gtin": CODE}).json()
    assert result["status"] == "NEEDS_CONFIRMATION" and len(result["candidates"]) == 2
    for candidate in result["candidates"]:
        for wine in candidate["releases"]:
            body = {
                "gtin": CODE,
                "catalogReleaseId": wine["id"],
                "vintageStatus": wine["vintageStatus"],
                "year": wine["year"],
                "edition": wine["edition"],
            }
            assert client.post(CONFIRM, json=body).status_code == 200


def test_shared_budget_counts_invalid_requests_and_ignores_forwarded_headers(
    barcode_api: tuple[TestClient, Engine],
) -> None:
    client, _ = barcode_api
    for i in range(30):
        assert (
            client.post(
                LOOKUP, json={"gtin": "bad"}, headers={"X-Forwarded-For": f"192.0.2.{i}"}
            ).status_code
            == 422
        )
    response = client.post(CONFIRM, json={})
    assert response.status_code == 429
    assert 1 <= int(response.headers["retry-after"]) <= 60
    assert response.headers["cache-control"] == "no-store"


def test_confirmed_release_uses_existing_authenticated_save(
    barcode_api: tuple[TestClient, Engine],
) -> None:
    client, engine = barcode_api
    body = selection(client)
    confirmed = client.post(CONFIRM, json=body).json()
    saved = {"consumedDate": "2026-10-20", "catalogReleaseId": confirmed["id"]}
    assert (
        client.post(
            "/api/v1/entries", json=saved, headers={"Idempotency-Key": str(uuid4())}
        ).status_code
        == 401
    )
    assert hasattr(client.app, "dependency_overrides")
    principal = Principal("https://barcode.test", uuid4())
    client.app.dependency_overrides[require_principal] = lambda: principal
    assert client.post("/api/v1/me", json={}).status_code == 200
    key = {"Idempotency-Key": str(uuid4())}
    first = client.post("/api/v1/entries", json=saved, headers=key)
    assert first.status_code == 200
    assert client.post("/api/v1/entries", json=saved, headers=key).json() == first.json()


@pytest.mark.parametrize("cap", ["MAX_OBSERVATIONS", "MAX_OFFERINGS", "MAX_RELEASES"])
def test_overflow_never_silently_picks_a_subset(
    barcode_api: tuple[TestClient, Engine],
    monkeypatch: pytest.MonkeyPatch,
    cap: str,
) -> None:
    from wine_journal.identification import barcodes

    client, _ = barcode_api
    body = selection(client)
    monkeypatch.setattr(barcodes, cap, 0)
    result = client.post(LOOKUP, json={"gtin": CODE}).json()
    assert result["status"] == "TOO_MANY_MATCHES" and result["candidates"] == []
    assert client.post(CONFIRM, json=body).status_code == 409


def test_oversized_and_invalid_json_are_bounded_and_charged(
    barcode_api: tuple[TestClient, Engine],
) -> None:
    client, _ = barcode_api
    response = client.post(
        LOOKUP,
        content=b" " * 4097,
        headers={"Content-Type": "application/json", "Content-Length": "1"},
    )
    assert response.status_code == 413
    assert response.headers["cache-control"] == "no-store"
    for _ in range(29):
        assert (
            client.post(
                LOOKUP, content=b"{", headers={"Content-Type": "application/json"}
            ).status_code
            == 422
        )
    assert client.post(LOOKUP, json={"gtin": CODE}).status_code == 429


@pytest.mark.parametrize("endpoint", [LOOKUP, CONFIRM])
def test_database_failure_is_safe_retryable_and_does_not_echo_values(
    barcode_api: tuple[TestClient, Engine],
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    from sqlalchemy.exc import OperationalError

    from wine_journal.identification import barcodes

    client, _ = barcode_api
    body = selection(client) if endpoint == CONFIRM else {"gtin": CODE}

    def fail(*args: object) -> None:
        raise OperationalError("PRIVATE_SQL", {}, Exception("DO_NOT_LOG"))

    monkeypatch.setattr(barcodes, "confirm" if endpoint == CONFIRM else "lookup", fail)
    response = client.post(endpoint, json=body)
    assert response.status_code == 503 and response.headers["retry-after"] == "5"
    assert "DO_NOT_LOG" not in response.text and "PRIVATE_SQL" not in response.text
    assert response.json()["error"]["code"] == "BARCODE_LOOKUP_UNAVAILABLE"
