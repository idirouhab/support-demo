from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import Ticket
from .tickets import list_tickets


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
