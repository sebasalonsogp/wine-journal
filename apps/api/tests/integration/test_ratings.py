from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.core.errors import ApiError
from wine_journal.journal.models import RatingRevision, UserWine
from wine_journal.journal.ratings import change_rating
from wine_journal.main import create_app

RatingClient = tuple[TestClient, Principal, dict[str, Any]]


@pytest.fixture
def rating_client(database_urls: dict[str, SecretStr]) -> Iterator[RatingClient]:
    principal = Principal("https://ratings.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        entry = client.post(
            "/api/v1/entries",
            json={"consumedDate": "2026-09-29", "manualWine": {"name": "Rating wine"}},
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        yield client, principal, entry


def test_rating_changes_noop_clear_erase_and_entries(rating_client: RatingClient) -> None:
    client, _, entry = rating_client
    url = f"/api/v1/me/wines/{entry['userWineId']}"
    assert client.get(url).json()["currentRating"] is None
    assert client.get(url).json()["ratingVersion"] == 0
    for version, score in enumerate([4, 4.5]):
        response = client.put(url + "/rating", json={"version": version, "score": score})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {"score": score, "version": version + 1}
    assert client.put(url + "/rating", json={"version": 2, "score": 4.5}).json()["version"] == 2
    assert client.put(url + "/rating", json={"version": 1, "score": 4.5}).status_code == 409
    history = client.get(url + "/rating-history")
    assert history.headers["cache-control"] == "no-store"
    assert [item["score"] for item in history.json()["items"]] == [4.5, 4]
    assert all(item["changedAt"] for item in history.json()["items"])
    assert client.get("/api/v1/me/wines").json()["items"][0]["currentRating"] == 4.5
    assert client.get(url).json()["entryCount"] == 1
    client.delete(f"/api/v1/entries/{entry['id']}", params={"version": 1})
    assert client.get(url).json()["currentRating"] == 4.5
    assert client.put(url + "/rating", json={"version": 2, "score": None}).json()["version"] == 3
    assert [item["score"] for item in client.get(url + "/rating-history").json()["items"]] == [
        None,
        4.5,
        4,
    ]
    assert client.delete(url + "/rating-history", params={"version": 2}).status_code == 409
    erased = client.delete(url + "/rating-history", params={"version": 3})
    assert erased.headers["cache-control"] == "no-store"
    assert erased.json() == {"score": None, "version": 4}
    assert client.get(url + "/rating-history").json()["items"] == []
    assert client.put(url + "/rating", json={"version": 0, "score": 5}).status_code == 409
    assert client.put(url + "/rating", json={"version": 4, "score": 5}).json()["version"] == 5
    assert client.get(url).json()["entryCount"] == 0


def test_rating_validation_and_bounded_history(rating_client: RatingClient) -> None:
    client, _, entry = rating_client
    url = f"/api/v1/me/wines/{entry['userWineId']}"
    for score in [0, 0.5, 5.5, -1, 4.2, True, "4"]:
        assert client.put(url + "/rating", json={"version": 0, "score": score}).status_code == 422
    for body in [
        {"version": 0},
        {"version": True, "score": 4},
        {"version": -1, "score": 4},
        {"version": 0, "score": 4, "ownerId": str(uuid4())},
    ]:
        assert client.put(url + "/rating", json=body).status_code == 422
    for version, score in enumerate([1, 5, 1.5, 4]):
        assert (
            client.put(url + "/rating", json={"version": version, "score": score}).status_code
            == 200
        )
    first = client.get(url + "/rating-history", params={"limit": 2}).json()
    assert [item["score"] for item in first["items"]] == [4, 1.5]
    # An intervening new rating must not cause a duplicate on the next page.
    client.put(url + "/rating", json={"version": 4, "score": 3})
    second = client.get(
        url + "/rating-history", params={"limit": 2, "beforeVersion": first["nextBeforeVersion"]}
    ).json()
    assert [item["score"] for item in second["items"]] == [5, 1]
    assert second["nextBeforeVersion"] is None
    assert client.get(url + "/rating-history", params={"limit": 101}).status_code == 422
    assert client.get(url + "/rating-history", params={"beforeVersion": 0}).status_code == 422


def test_rating_owner_and_release_isolation(rating_client: RatingClient) -> None:
    client, principal, entry = rating_client
    url = f"/api/v1/me/wines/{entry['userWineId']}"
    client.put(url + "/rating", json={"version": 0, "score": 4})
    other_entry = client.post(
        "/api/v1/entries",
        json={
            "consumedDate": "2026-09-29",
            "manualWine": {"name": "Rating wine", "vintageStatus": "YEAR", "year": 2022},
        },
        headers={"Idempotency-Key": str(uuid4())},
    ).json()
    assert (
        client.get(f"/api/v1/me/wines/{other_entry['userWineId']}").json()["currentRating"] is None
    )
    other = Principal(principal.issuer, uuid4())
    cast(FastAPI, client.app).dependency_overrides[require_principal] = lambda: other
    client.post("/api/v1/me", json={})
    assert client.get(url + "/rating-history").status_code == 404
    assert client.put(url + "/rating", json={"version": 1, "score": 5}).status_code == 404
    assert client.delete(url + "/rating-history", params={"version": 1}).status_code == 404


def test_concurrent_ratings_have_one_winner(
    rating_client: RatingClient, database_urls: dict[str, SecretStr]
) -> None:
    client, principal, entry = rating_client
    engine = database_engine(database_urls["runtime"])
    barrier = Barrier(2)

    def change(score: float) -> int:
        with Session(engine, expire_on_commit=False) as session:
            barrier.wait(timeout=5)
            try:
                change_rating(session, principal, UUID(entry["userWineId"]), 0, score)
                return 200
            except ApiError as error:
                return error.status

    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            assert sorted(workers.map(change, [4, 4.5])) == [200, 409]
        history = client.get(f"/api/v1/me/wines/{entry['userWineId']}/rating-history").json()
        assert len(history["items"]) == 1
    finally:
        engine.dispose()


def test_revision_failure_rolls_back_current_rating(
    rating_client: RatingClient, database_urls: dict[str, SecretStr]
) -> None:
    _, principal, entry = rating_client
    engine = database_engine(database_urls["runtime"])

    def reject_revision(*args: object) -> None:
        raise RuntimeError("Injected revision failure")

    event.listen(RatingRevision, "before_insert", reject_revision)
    try:
        with Session(engine, expire_on_commit=False) as session, pytest.raises(RuntimeError):
            change_rating(session, principal, UUID(entry["userWineId"]), 0, 4)
        with Session(engine) as session:
            wine = session.get(UserWine, UUID(entry["userWineId"]))
            assert wine is not None and wine.rating_units is None and wine.rating_version == 0
            assert (
                session.scalar(select(RatingRevision).where(RatingRevision.user_wine_id == wine.id))
                is None
            )
    finally:
        event.remove(RatingRevision, "before_insert", reject_revision)
        engine.dispose()


def test_rating_upgrade_preserves_wines_and_limits_grants(
    rating_client: RatingClient, database_urls: dict[str, SecretStr], migrate: Callable[..., None]
) -> None:
    client, _, entry = rating_client
    migrate("downgrade", "0005_entry_deletion")
    migrate("upgrade", "head")
    migrate("check")
    wine = client.get(f"/api/v1/me/wines/{entry['userWineId']}").json()
    assert wine["currentRating"] is None and wine["ratingVersion"] == 0 and wine["entryCount"] == 1
    engine = database_engine(database_urls["runtime"])
    try:
        for statement in [
            "UPDATE app.user_wines SET owner_id = owner_id",
            "UPDATE app.rating_revisions SET rating_units = 2",
        ]:
            with engine.begin() as connection, pytest.raises(ProgrammingError):
                connection.execute(text(statement))
    finally:
        engine.dispose()
