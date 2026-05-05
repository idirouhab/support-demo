from fastapi.testclient import TestClient

from app.main import app
from app.models import CANONICAL_TICKET_STATUSES


client = TestClient(app)


def test_openapi_title_is_support_api() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Support API"


def test_list_tickets_contract() -> None:
    response = client.get("/api/tickets")

    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) == 4

    for ticket in tickets:
        assert set(ticket) == {
            "id",
            "title",
            "requester",
            "priority",
            "status",
            "created_at",
        }


def test_in_progress_is_canonical_api_status() -> None:
    response = client.get("/api/tickets")
    tickets = response.json()
    ticket_by_id = {ticket["id"]: ticket for ticket in tickets}

    assert ticket_by_id["T-102"]["status"] == "in_progress"
    assert "in_progress" in CANONICAL_TICKET_STATUSES


def test_all_returned_statuses_are_canonical() -> None:
    response = client.get("/api/tickets")
    tickets = response.json()
    returned_statuses = {ticket["status"] for ticket in tickets}

    assert returned_statuses <= set(CANONICAL_TICKET_STATUSES)
