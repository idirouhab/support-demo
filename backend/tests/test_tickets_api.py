from datetime import datetime

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
    ticket_ids = [ticket["id"] for ticket in tickets]
    assert len(set(ticket_ids)) == len(ticket_ids)
    assert set(ticket_ids) == {"T-101", "T-102", "T-103", "T-104"}

    for ticket in tickets:
        assert set(ticket) == {
            "id",
            "title",
            "description",
            "requester",
            "priority",
            "status",
            "created_at",
        }


def test_seeded_tickets_keep_expected_statuses() -> None:
    response = client.get("/api/tickets")

    assert response.status_code == 200
    assert {ticket["id"]: ticket["status"] for ticket in response.json()} == {
        "T-101": "open",
        "T-102": "in_progress",
        "T-103": "pending",
        "T-104": "resolved",
    }


def test_ticket_timestamps_are_parseable_and_include_timezone() -> None:
    response = client.get("/api/tickets")

    assert response.status_code == 200
    tickets = response.json()
    assert tickets
    for ticket in tickets:
        created_at = datetime.fromisoformat(ticket["created_at"])
        assert created_at.utcoffset() is not None, ticket["id"]


def test_in_progress_is_canonical_api_status() -> None:
    response = client.get("/api/tickets")

    assert response.status_code == 200
    tickets = response.json()
    ticket_by_id = {ticket["id"]: ticket for ticket in tickets}

    assert ticket_by_id["T-102"]["status"] == "in_progress"
    assert "in_progress" in CANONICAL_TICKET_STATUSES


def test_list_tickets_includes_resolved_tickets() -> None:
    response = client.get("/api/tickets")

    assert response.status_code == 200
    ticket_by_id = {ticket["id"]: ticket for ticket in response.json()}

    assert "T-104" in ticket_by_id
    assert ticket_by_id["T-104"]["status"] == "resolved"


def test_all_returned_statuses_are_canonical() -> None:
    response = client.get("/api/tickets")

    assert response.status_code == 200
    tickets = response.json()
    returned_statuses = {ticket["status"] for ticket in tickets}

    assert returned_statuses <= set(CANONICAL_TICKET_STATUSES)
