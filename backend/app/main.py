from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import Ticket, TicketUpdate
from .tickets import find_ticket, list_tickets, update_ticket


app = FastAPI(title="Support API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tickets", response_model=list[Ticket])
def get_tickets() -> list[Ticket]:
    return list_tickets()


@app.get("/api/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: str) -> Ticket:
    ticket = find_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.put("/api/tickets/{ticket_id}", response_model=Ticket)
def put_ticket(ticket_id: str, changes: TicketUpdate) -> Ticket:
    ticket = update_ticket(ticket_id, changes)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
