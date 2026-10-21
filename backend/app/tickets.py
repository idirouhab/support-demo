from .models import Ticket, TicketUpdate


TICKETS = [
    Ticket(
        id="T-101",
        title="Cannot download invoice - B1",
        description="The invoice download shows an error. Please help the requester access their latest invoice.",
        requester="Maya Patel",
        priority="high",
        status="open",
        created_at="2026-05-01T09:15:00Z",
    ),
    Ticket(
        id="T-102",
        title="Refund request needs manager approval - B1",
        description="The refund request has been reviewed and is waiting for manager approval.",
        requester="Owen Chen",
        priority="medium",
        status="in_progress",
        created_at="2026-05-02T14:40:00Z",
    ),
    Ticket(
        id="T-103",
        title="Update billing email - B1",
        description="The requester would like to change the email address used for billing notifications.",
        requester="Sofia Garcia",
        priority="low",
        status="pending",
        created_at="2026-05-03T11:05:00Z",
    ),
    Ticket(
        id="T-104",
        title="Login issue resolved after password reset - B1",
        description="The requester can sign in again after resetting their password. No further action is needed.",
        requester="Leo Martin",
        priority="medium",
        status="resolved",
        created_at="2026-05-04T16:20:00Z",
    ),
]


def list_tickets() -> list[Ticket]:
    return [ticket for ticket in TICKETS if ticket.status != "resolved"]


def find_ticket(ticket_id: str) -> Ticket | None:
    return next((ticket for ticket in TICKETS if ticket.id == ticket_id), None)


def update_ticket(ticket_id: str, changes: TicketUpdate) -> Ticket | None:
    for index, ticket in enumerate(TICKETS):
        if ticket.id == ticket_id:
            updated = ticket.model_copy(update=changes.model_dump())
            TICKETS[index] = updated
            return updated
    return None
