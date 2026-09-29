from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.main import create_app


def test_deletion_preserves_wine_and_rejects_stale_or_foreign_requests(
    database_urls: dict[str, SecretStr],
) -> None:
    owner = Principal("https://deletion.test", uuid4())
    other = Principal(owner.issuer, uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: owner
    with TestClient(app) as client:
        client.post("/api/v1/me", json={})
        key = {"Idempotency-Key": str(uuid4())}
        body = {"consumedDate": "2026-09-29", "manualWine": {"name": "Keep this wine"}}
        first = client.post("/api/v1/entries", json=body, headers=key).json()
        wine_url = f"/api/v1/me/wines/{first['userWineId']}"
        release = client.get(wine_url).json()["releaseId"]
        second = client.post(
            "/api/v1/entries",
            json={
                "consumedDate": "2026-09-01",
                "releaseId": release,
            },
            headers={"Idempotency-Key": str(uuid4())},
        ).json()
        url = f"/api/v1/entries/{first['id']}"
        assert client.delete(url).status_code == 422
        assert client.delete(url, params={"version": 0}).status_code == 422
        client.patch(url, json={"version": 1, "notes": "A newer memory"})
        assert client.delete(url, params={"version": 1}).status_code == 409
        assert client.get(url).json()["notes"] == "A newer memory"
        app.dependency_overrides[require_principal] = lambda: other
        client.post("/api/v1/me", json={})
        assert client.delete(url, params={"version": 2}).status_code == 404
        app.dependency_overrides[require_principal] = lambda: owner
        removed = client.delete(url, params={"version": 2})
        assert removed.status_code == 200
        assert removed.json() == {"id": first["id"]}
        assert removed.headers["cache-control"] == "no-store"
        assert client.get(url).status_code == 404
        assert client.delete(url, params={"version": 2}).status_code == 404
        # A delayed create retry must not resurrect the deleted entry or report it saved.
        assert client.post("/api/v1/entries", json=body, headers=key).status_code == 409
        wine = client.get(wine_url).json()
        assert wine["entryCount"] == 1 and wine["lastConsumedDate"] == "2026-09-01"
        assert client.get(wine_url + "/entries").json()["items"][0]["id"] == second["id"]
        assert (
            client.delete(f"/api/v1/entries/{second['id']}", params={"version": 1}).status_code
            == 200
        )
        wine = client.get(wine_url).json()
        assert wine["entryCount"] == 0 and wine["lastConsumedDate"] is None
        assert client.get(wine_url + "/entries").json()["items"] == []
        assert client.get("/api/v1/me/wines").json()["items"][0]["id"] == first["userWineId"]
