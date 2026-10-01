from collections.abc import Iterator
from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from wine_journal.catalog.schemas import ManualWine
from wine_journal.catalog.service import create_manual_release
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.journal.models import DrinkingEntry, UserWine
from wine_journal.journal.queries import filtered_wine_query, list_wines
from wine_journal.journal.wine_filters import WineFilters, WineSort
from wine_journal.main import create_app


@pytest.fixture
def search_client(database_urls: dict[str, SecretStr]) -> Iterator[tuple[TestClient, UUID]]:
    principal = Principal("https://search.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        owner = UUID(client.post("/api/v1/me", json={}).json()["id"])
        engine = database_engine(database_urls["runtime"])
        try:
            with Session(engine) as session, session.begin():
                for index in range(24):
                    status = ["YEAR", "NON_VINTAGE", "MULTI_VINTAGE", "UNKNOWN"][index % 4]
                    release = create_manual_release(
                        session,
                        owner,
                        ManualWine.model_validate(
                            {
                                "name": f"Label {index // 2:02}",
                                "producer": "North Cellars",
                                "vintageStatus": status,
                                "year": 2021 + index % 3 if status == "YEAR" else None,
                                "edition": "Reserve" if index % 2 == 0 else None,
                            }
                        ),
                    )
                    wine = UserWine(
                        owner_id=owner,
                        release_id=release.id,
                        rating_units=None if index % 3 == 0 else 8 + index % 2,
                    )
                    session.add(wine)
                    session.flush()
                    if index % 5:
                        session.add(
                            DrinkingEntry(
                                owner_id=owner,
                                user_wine_id=wine.id,
                                consumed_date=date(2026, 9, 1 + index % 3),
                            )
                        )
            yield client, owner
        finally:
            engine.dispose()


@pytest.mark.parametrize("sort", ["LAST_CONSUMED", "NAME", "RATING"])
def test_filtered_pages_preserve_ties_and_unknowns(
    search_client: tuple[TestClient, UUID], sort: WineSort
) -> None:
    client, _ = search_client
    for filters in [
        {},
        {"rating": "RATED"},
        {"rating": "UNRATED"},
        {"vintage": "YEAR"},
        {"vintage": "UNKNOWN"},
        {"q": "NORTH Reserve", "rating": "RATED"},
    ]:
        params = {"sort": sort, **filters}
        whole = client.get("/api/v1/me/wines", params={**params, "limit": 100}).json()["items"]
        found = []
        cursor = None
        for _ in range(15):
            page = client.get(
                "/api/v1/me/wines",
                params={**params, "limit": 3, **({"cursor": cursor} if cursor else {})},
            )
            assert page.status_code == 200
            assert page.headers["cache-control"] == "no-store"
            found.extend(page.json()["items"])
            cursor = page.json()["nextCursor"]
            if cursor is None:
                break
        assert cursor is None
        assert found == whole
        assert len({item["id"] for item in found}) == len(found)
        if sort == "NAME":
            assert [item["name"].lower() for item in whole] == sorted(
                item["name"].lower() for item in whole
            )
        elif sort == "RATING":
            scores = [item["currentRating"] for item in whole]
            assert scores == sorted(scores, key=lambda score: -(score or 0))
        else:
            dates = [item["lastConsumedDate"] for item in whole]
            assert dates == sorted(dates, key=lambda value: value or "", reverse=True)
        if filters.get("rating") == "RATED":
            assert all(item["currentRating"] is not None for item in found)
        if filters.get("rating") == "UNRATED":
            assert all(item["currentRating"] is None for item in found)
        if "vintage" in filters:
            assert all(item["vintageStatus"] == filters["vintage"] for item in found)


def test_search_fields_literal_patterns_and_cursor_scope(
    search_client: tuple[TestClient, UUID],
) -> None:
    client, _ = search_client
    matches = client.get("/api/v1/me/wines", params={"q": " north  2022 reserve "}).json()["items"]
    assert len(matches) == 2 and all(item["year"] == 2022 for item in matches)
    for query in ["not-here", "%", "_", "' OR 1=1 --"]:
        assert client.get("/api/v1/me/wines", params={"q": query}).json()["items"] == []
    first = client.get("/api/v1/me/wines", params={"limit": 1}).json()
    for change in [{"sort": "NAME"}, {"rating": "RATED"}, {"vintage": "YEAR"}, {"q": "Label"}]:
        assert (
            client.get(
                "/api/v1/me/wines", params={"cursor": first["nextCursor"], **change}
            ).status_code
            == 422
        )
    for invalid in [
        {"sort": "wrong"},
        {"rating": "wrong"},
        {"vintage": "wrong"},
        {"q": "x" * 201},
        {"q": "\x00"},
        {"cursor": "x" * 2049},
    ]:
        assert client.get("/api/v1/me/wines", params=invalid).status_code == 422


def test_literal_and_long_unicode_names_paginate(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://unicode.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        for name in [
            "100% estate_Name",
            "100% estate_Name",
            "葡萄" * 100,
            "葡萄" * 100,
            "İstanbul",
        ]:
            assert (
                client.post(
                    "/api/v1/entries",
                    json={"manualWine": {"name": name}, "consumedDate": "2026-09-29"},
                    headers={"Idempotency-Key": str(uuid4())},
                ).status_code
                == 200
            )
        for pattern in ["%", "_"]:
            assert len(client.get("/api/v1/me/wines", params={"q": pattern}).json()["items"]) == 2
        cursor = None
        ids = []
        for _ in range(5):
            result = client.get(
                "/api/v1/me/wines",
                params={"sort": "NAME", "limit": 1, **({"cursor": cursor} if cursor else {})},
            )
            assert result.status_code == 200
            ids.append(result.json()["items"][0]["id"])
            cursor = result.json()["nextCursor"]
        assert len(set(ids)) == 5 and cursor is None


def test_fresh_filter_results_follow_entry_and_rating_changes(
    search_client: tuple[TestClient, UUID],
) -> None:
    client, _ = search_client
    wine = client.get("/api/v1/me/wines", params={"rating": "RATED", "limit": 1}).json()["items"][0]
    wine_url = f"/api/v1/me/wines/{wine['id']}"
    client.put(wine_url + "/rating", json={"version": wine["ratingVersion"], "score": None})
    assert wine["id"] not in {
        item["id"]
        for item in client.get("/api/v1/me/wines", params={"rating": "RATED"}).json()["items"]
    }
    entry = client.get(wine_url + "/entries").json()["items"][0]
    client.patch(
        f"/api/v1/entries/{entry['id']}", json={"version": 1, "consumedDate": "2027-01-01"}
    )
    assert client.get("/api/v1/me/wines").json()["items"][0]["id"] == wine["id"]
    client.delete(f"/api/v1/entries/{entry['id']}", params={"version": 2})
    result = client.get("/api/v1/me/wines", params={"rating": "UNRATED", "limit": 100}).json()[
        "items"
    ]
    assert next(item for item in result if item["id"] == wine["id"])["lastConsumedDate"] is None


def test_filtered_queries_remain_single_owner_scoped_reads(
    search_client: tuple[TestClient, UUID], database_urls: dict[str, SecretStr]
) -> None:
    _, owner = search_client
    engine = database_engine(database_urls["runtime"])
    statements = 0

    def count(*args: object) -> None:
        nonlocal statements
        statements += 1

    try:
        event.listen(engine, "before_cursor_execute", count)
        with Session(engine) as session:
            result = list_wines(session, owner, 20, None, WineFilters(q="north", sort="RATING"))
            assert len(result.items) == 20
        assert statements == 1
        event.remove(engine, "before_cursor_execute", count)
        # Compile/explain the actual production query, with synthetic fixture values only.
        with Session(engine) as session:
            statement = filtered_wine_query(owner, WineFilters(q="north", sort="NAME"))
            statement = statement.order_by(
                statement.selected_columns.sort_value, UserWine.id
            ).limit(21)
            sql = str(statement.compile(engine, compile_kwargs={"literal_binds": True}))
            plan = session.execute(text("EXPLAIN (FORMAT JSON) " + sql)).scalar_one()
            assert plan[0]["Plan"]["Node Type"] == "Limit"
    finally:
        engine.dispose()
