from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from wine_journal.accounts.models import AppUser
from wine_journal.accounts.service import bootstrap_account
from wine_journal.core.auth import Principal, require_principal
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.main import create_app


def test_guest_requests_cannot_reach_private_account() -> None:
    with TestClient(create_app(Settings.model_construct())) as client:
        for method in ("GET", "POST"):
            response = client.request(method, "/api/v1/me", json={} if method == "POST" else None)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "UNAUTHENTICATED"
            assert response.headers["www-authenticate"] == "Bearer"
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["error"]["requestId"] == response.headers["x-request-id"]


def test_bootstrap_reads_and_two_account_isolation(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://identity.example/auth/v1", uuid4())
    other = Principal(principal.issuer, uuid4())
    app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        assert client.get("/api/v1/me").status_code == 404
        first = client.post("/api/v1/me", json={})
        assert first.status_code == 200
        assert set(first.json()) == {"id", "state", "createdAt"}
        assert client.post("/api/v1/me", json={}).json() == first.json()
        assert client.get("/api/v1/me").json() == first.json()
        assert first.headers["cache-control"] == "no-store"
        app.dependency_overrides[require_principal] = lambda: other
        # GET did not bootstrap either identity; the second still does not exist.
        assert client.get("/api/v1/me").status_code == 404
        assert client.post("/api/v1/me", json={"ownerId": first.json()["id"]}).status_code == 422
        assert client.get("/api/v1/me").status_code == 404
        second = client.post("/api/v1/me", json={})
        assert second.status_code == 200 and second.json()["id"] != first.json()["id"]
        assert (
            client.get("/api/v1/me", params={"ownerId": first.json()["id"]}).json() == second.json()
        )


def test_concurrent_bootstraps_create_one_identity(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://identity.example/auth/v1", uuid4())
    engine = database_engine(database_urls["runtime"])
    try:

        def create(_: int) -> str:
            with Session(engine, expire_on_commit=False) as session:
                return str(bootstrap_account(session, principal).id)

        with ThreadPoolExecutor(max_workers=4) as workers:
            identifiers = list(workers.map(create, range(8)))
        assert len(set(identifiers)) == 1
        with Session(engine) as session:
            rows = session.scalars(
                select(AppUser).where(AppUser.auth_subject == principal.subject)
            ).all()
            assert len(rows) == 1
    finally:
        engine.dispose()


def test_disabled_account_cannot_read_or_rebootstrap(database_urls: dict[str, SecretStr]) -> None:
    principal = Principal("https://identity.example/auth/v1", uuid4())
    engine = database_engine(database_urls["runtime"])
    try:
        with Session(engine, expire_on_commit=False) as session:
            account = bootstrap_account(session, principal)
            with session.begin():
                session.execute(
                    update(AppUser).where(AppUser.id == account.id).values(state="DISABLED")
                )
        app = create_app(Settings.model_construct(database_url=database_urls["runtime"]))
        app.dependency_overrides[require_principal] = lambda: principal
        with TestClient(app) as client:
            for response in (client.get("/api/v1/me"), client.post("/api/v1/me", json={})):
                assert response.status_code == 403
                assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"
    finally:
        engine.dispose()


def test_internal_errors_hide_secrets_and_preserve_cors(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(Settings.model_construct())

    @app.get("/test-failure")
    def fail() -> None:
        raise RuntimeError("private credential should never be echoed")

    with TestClient(app) as client:
        response = client.get("/test-failure", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "private credential" not in response.text + caplog.text
