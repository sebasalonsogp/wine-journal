from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.catalog.schemas import ManualWine
from wine_journal.catalog.service import create_manual_release
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.journal.models import UserWine
from wine_journal.journal.queries import list_wines
from wine_journal.main import create_app


def test_history_sort_pagination_and_owner_isolation(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://reads.test", uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        owner_id = UUID(client.post("/api/v1/me", json={}).json()["id"])

        def save(payload: dict[str, object]) -> dict[str, object]:
            response = client.post(
                "/api/v1/entries", json=payload, headers={"Idempotency-Key": str(uuid4())}
            )
            assert response.status_code == 200
            return dict(response.json())

        first = save({"manualWine": {"name": "Older"}, "consumedDate": "2026-01-01"})
        second = save({"manualWine": {"name": "Newer"}, "consumedDate": "2026-09-01"})
        first_wine = client.get(f"/api/v1/me/wines/{first['userWineId']}").json()
        save({"releaseId": first_wine["releaseId"], "consumedDate": "2025-01-01"})
        save({"releaseId": first_wine["releaseId"], "consumedDate": "2026-01-01"})
        page = client.get("/api/v1/me/wines?limit=1").json()
        assert page["items"][0]["id"] == second["userWineId"]
        following = client.get(
            "/api/v1/me/wines", params={"limit": 1, "cursor": page["nextCursor"]}
        ).json()
        assert following["items"][0]["id"] == first["userWineId"]
        assert following["items"][0]["entryCount"] == 3
        assert following["items"][0]["lastConsumedDate"] == "2026-01-01"
        assert following["nextCursor"] is None
        items = []
        cursor = ""
        for _ in range(3):
            result = client.get(
                f"/api/v1/me/wines/{first['userWineId']}/entries",
                params={"limit": 1, "cursor": cursor},
            ).json()
            items.extend(result["items"])
            cursor = result["nextCursor"]
        assert cursor is None
        assert len({item["id"] for item in items}) == 3
        assert [item["consumedDate"] for item in items] == [
            "2026-01-01",
            "2026-01-01",
            "2025-01-01",
        ]
        assert client.get("/api/v1/me/wines?cursor=bad").status_code == 422
        assert client.get("/api/v1/me/wines?limit=101").status_code == 422

        engine = database_engine(database_urls["runtime"])
        try:
            with Session(engine) as session, session.begin():
                release = create_manual_release(session, owner_id, ManualWine(name="Empty history"))
                session.add(UserWine(owner_id=owner_id, release_id=release.id))
            query_count = 0

            def count(*args: object) -> None:
                nonlocal query_count
                query_count += 1

            event.listen(engine, "before_cursor_execute", count)
            with Session(engine) as session:
                wines = list_wines(session, owner_id, 20, None)
            assert query_count == 1
            assert wines.items[-1].last_consumed_date is None
            assert wines.items[-1].entry_count == 0
            assert wines.items[0].last_consumed_date == date(2026, 9, 1)
        finally:
            engine.dispose()

        other = Principal(principal.issuer, uuid4())
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        assert client.get("/api/v1/me/wines").json()["items"] == []
        assert client.get(f"/api/v1/me/wines/{first['userWineId']}").status_code == 404
        assert client.get(f"/api/v1/me/wines/{first['userWineId']}/entries").status_code == 404
        assert (
            client.get("/api/v1/me/wines", params={"cursor": page["nextCursor"]}).status_code == 422
        )


def test_same_day_wine_pages_have_stable_ties(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    try:
        with Session(engine, expire_on_commit=False) as session:
            owner = bootstrap_account(session, Principal("https://ties.test", uuid4()))
            with session.begin():
                for _ in range(3):
                    release = create_manual_release(
                        session, owner.id, ManualWine(name="Similar label")
                    )
                    session.add(UserWine(owner_id=owner.id, release_id=release.id))
            first = list_wines(session, owner.id, 2, None)
            last = list_wines(session, owner.id, 2, first.nextCursor)
            assert len({item.id for item in first.items + last.items}) == 3
            assert last.nextCursor is None
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "path", ["/me/wines", f"/me/wines/{uuid4()}", f"/me/wines/{uuid4()}/entries"]
)
def test_private_history_requires_auth(path: str) -> None:
    with TestClient(create_app(Settings.model_construct())) as client:
        assert client.get("/api/v1" + path).status_code == 401
