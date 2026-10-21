"""Intentional SQL injection fixture. Run separately with synthetic data only."""

import sqlite3
from contextlib import closing

from fastapi import FastAPI


app = FastAPI(title="Security Plugin Lab")


@app.get("/api/tickets/search")
def search_tickets(q: str = "") -> list[dict[str, object]]:
    # A fresh, in-memory database keeps this demo independent of application data.
    with closing(sqlite3.connect(":memory:")) as database:
        database.row_factory = sqlite3.Row
        database.execute(
            "CREATE TABLE tickets (id TEXT, title TEXT, is_private INTEGER)"
        )
        database.executemany(
            "INSERT INTO tickets VALUES (?, ?, ?)",
            [
                ("LAB-PUBLIC", "Public demo ticket", 0),
                ("LAB-PRIVATE", "Private synthetic ticket", 1),
            ],
        )

        # INTENTIONAL CWE-89: q can alter the query and bypass is_private = 0.
        query = (
            "SELECT id, title FROM tickets "
            f"WHERE is_private = 0 AND title LIKE '%{q}%'"
        )
        return [dict(row) for row in database.execute(query).fetchall()]
