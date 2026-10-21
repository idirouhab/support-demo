from typing import get_args

import pytest
from pydantic import ValidationError

from app.models import CANONICAL_TICKET_STATUSES, Ticket, TicketStatus


@pytest.fixture
def ticket_data() -> dict[str, object]:
    return {
        "id": "T-200",
        "title": "Cannot update billing details",
        "requester": "Alex Rivera",
        "priority": "medium",
        "status": "open",
        "created_at": "2026-09-07T09:00:00Z",
    }


def test_status_definitions_match_the_api_contract() -> None:
    expected_statuses = {"open", "pending", "in_progress", "resolved"}

    assert set(CANONICAL_TICKET_STATUSES) == expected_statuses
    assert set(get_args(TicketStatus)) == expected_statuses


@pytest.mark.parametrize("status", ["open", "pending", "in_progress", "resolved"])
def test_ticket_preserves_canonical_status(
    ticket_data: dict[str, object], status: str
) -> None:
    ticket_data["status"] = status

    ticket = Ticket(**ticket_data)

    assert ticket.model_dump(mode="json")["status"] == status


@pytest.mark.parametrize("status", ["in-progress", "unknown", "OPEN", "", None, 1])
def test_ticket_rejects_noncanonical_status(
    ticket_data: dict[str, object], status: object
) -> None:
    ticket_data["status"] = status

    with pytest.raises(ValidationError) as error:
        Ticket(**ticket_data)

    assert [item["loc"] for item in error.value.errors()] == [("status",)]


@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_ticket_preserves_valid_priority(
    ticket_data: dict[str, object], priority: str
) -> None:
    ticket_data["priority"] = priority

    ticket = Ticket(**ticket_data)

    assert ticket.model_dump(mode="json")["priority"] == priority


@pytest.mark.parametrize("priority", ["urgent", "HIGH", "", None, 1])
def test_ticket_rejects_invalid_priority(
    ticket_data: dict[str, object], priority: object
) -> None:
    ticket_data["priority"] = priority

    with pytest.raises(ValidationError) as error:
        Ticket(**ticket_data)

    assert [item["loc"] for item in error.value.errors()] == [("priority",)]
