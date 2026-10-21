from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


CANONICAL_TICKET_STATUSES = ("open", "pending", "in_progress", "resolved")

TicketStatus = Literal["open", "pending", "in_progress", "resolved"]
TicketPriority = Literal["low", "medium", "high"]


class Ticket(BaseModel):
    id: str
    title: str
    description: str = ""
    requester: str
    priority: TicketPriority
    status: TicketStatus
    created_at: str


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    description: str = Field(max_length=10000)
    status: TicketStatus
