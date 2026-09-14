from fastapi.testclient import TestClient

from wine_journal.core.config import Settings
from wine_journal.main import create_app


def test_liveness_without_external_services() -> None:
    with TestClient(create_app(Settings(cors_origins=[]))) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_only_configured_browser_origin() -> None:
    with TestClient(create_app(Settings(cors_origins=["http://localhost:3000"]))) as client:
        cases = [("http://localhost:3000", 200), ("https://other.test", 400)]
        for origin, expected_status in cases:
            response = client.options(
                "/api/v1/health/live",
                headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
            )
            assert response.status_code == expected_status
            assert response.headers.get("access-control-allow-origin") == (
                origin if expected_status == 200 else None
            )
