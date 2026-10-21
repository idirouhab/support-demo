from fastapi.testclient import TestClient

from app.main import app as support_app
from security_lab.app import app as lab_app


def test_lab_search_filters_private_tickets_for_normal_input() -> None:
    with TestClient(lab_app) as client:
        response = client.get("/api/tickets/search", params={"q": "demo"})
        assert response.status_code == 200
        assert response.json() == [
            {"id": "LAB-PUBLIC", "title": "Public demo ticket"}
        ]

        response = client.get("/api/tickets/search", params={"q": "Private"})
        assert response.status_code == 200
        assert response.json() == []


def test_lab_sql_injection_exposes_synthetic_private_ticket() -> None:
    # This deliberately confirms the flaw, rather than asserting secure behavior.
    with TestClient(lab_app) as client:
        response = client.get(
            "/api/tickets/search", params={"q": "' OR 1=1 -- "}
        )

    assert response.status_code == 200
    assert {ticket["id"] for ticket in response.json()} == {
        "LAB-PUBLIC",
        "LAB-PRIVATE",
    }


def test_support_app_does_not_expose_security_lab_endpoint() -> None:
    with TestClient(support_app) as client:
        response = client.get(
            "/api/tickets/search", params={"q": "' OR 1=1 -- "}
        )

    assert response.status_code == 404
