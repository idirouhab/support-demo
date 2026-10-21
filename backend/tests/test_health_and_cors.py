import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_reports_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_ticket_response_allows_configured_frontend_origin(origin: str) -> None:
    response = client.get("/api/tickets", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_preflight_allows_configured_frontend_origin(origin: str) -> None:
    response = client.options(
        "/api/tickets",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "GET" in response.headers["access-control-allow-methods"].split(", ")
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_ticket_response_does_not_allow_unrelated_origin() -> None:
    response = client.get(
        "/api/tickets", headers={"Origin": "https://unrelated.example"}
    )

    # CORS controls browser access to the response, not direct HTTP access.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_preflight_rejects_unrelated_origin() -> None:
    response = client.options(
        "/api/tickets",
        headers={
            "Origin": "https://unrelated.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
