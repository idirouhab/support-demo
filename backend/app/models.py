from typing import Literal

from pydantic import BaseModel


CANONICAL_TICKET_STATUSES = ("open", "pending", "in_progress", "resolved")

TicketStatus = Literal["open", "pending", "in_progress", "resolved"]
TicketPriority = Literal["low", "medium", "high"]


class Ticket(BaseModel):
    id: str
    title: str
    requester: str
    priority: TicketPriority
    status: TicketStatus
    created_at: str
