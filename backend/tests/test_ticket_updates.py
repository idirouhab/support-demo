import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tickets import TICKETS


client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_tickets():
    original = [ticket.model_copy(deep=True) for ticket in TICKETS]
    yield
    TICKETS[:] = original


@pytest.mark.parametrize("status", ["open", "pending", "in_progress", "resolved"])
def test_update_ticket_and_read_saved_details(status: str) -> None:
    before = client.get("/api/tickets").json()
    update = {
        "title": "  Updated invoice issue  ",
        "description": "Invoice download fails.\nPlease investigate.",
        "status": status,
    }

    response = client.put("/api/tickets/T-101", json=update)

    assert response.status_code == 200
    expected = {**before[0], **update, "title": "Updated invoice issue"}
    assert response.json() == expected
    after = client.get("/api/tickets").json()
    assert after[0] == expected
    assert after[1:] == before[1:]
    assert client.get("/api/tickets/T-101").json() == expected


def test_read_ticket_details() -> None:
    expected = client.get("/api/tickets").json()[1]

    response = client.get("/api/tickets/T-102")

    assert response.status_code == 200
    assert response.json() == expected
    assert response.json()["description"]


def test_read_missing_ticket_returns_not_found() -> None:
    response = client.get("/api/tickets/T-999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_can_clear_a_description() -> None:
    response = client.put(
        "/api/tickets/T-101",
        json={"title": "Invoice issue", "description": "", "status": "open"},
    )

    assert response.status_code == 200
    assert response.json()["description"] == ""


@pytest.mark.parametrize("invalid", [
    {"title": ""}, {"title": "   "}, {"title": None}, {"title": "x" * 201},
    {"description": None}, {"description": "x" * 10001},
    {"status": "in-progress"}, {"status": "blocked"}, {"status": None},
    {"requester": "Someone else"}, {"id": "T-999"},
])
def test_rejects_invalid_updates_without_mutating_tickets(invalid: dict) -> None:
    before = client.get("/api/tickets").json()
    response = client.put(
        "/api/tickets/T-101",
        json={"title": "Updated", "description": "Details", "status": "pending", **invalid},
    )

    assert response.status_code == 422
    assert client.get("/api/tickets").json() == before


def test_rejects_incomplete_update() -> None:
    response = client.put("/api/tickets/T-101", json={"title": "Updated"})

    assert response.status_code == 422


def test_missing_ticket_returns_not_found() -> None:
    response = client.put(
        "/api/tickets/T-999",
        json={"title": "Updated", "description": "Details", "status": "open"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}
