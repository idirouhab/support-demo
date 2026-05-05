from .models import Ticket


TICKETS = [
    Ticket(
        id="T-101",
        title="Cannot download invoice",
        requester="Maya Patel",
        priority="high",
        status="open",
        created_at="2026-05-01T09:15:00Z",
    ),
    Ticket(
        id="T-102",
        title="Refund request needs manager approval",
        requester="Owen Chen",
        priority="medium",
        status="in_progress",
        created_at="2026-05-02T14:40:00Z",
    ),
    Ticket(
        id="T-103",
        title="Update billing email",
        requester="Sofia Garcia",
        priority="low",
        status="pending",
        created_at="2026-05-03T11:05:00Z",
    ),
    Ticket(
        id="T-104",
        title="Login issue resolved after password reset",
        requester="Leo Martin",
        priority="medium",
        status="resolved",
        created_at="2026-05-04T16:20:00Z",
    ),
]


def list_tickets() -> list[Ticket]:
    return [ticket for ticket in TICKETS if ticket.status != "resolved"]
