"""SQLite persistence for deposits — no UI dependencies."""
import sqlite3
from datetime import date

from depositcalc.models import Deposit

_SCHEMA = """
CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank TEXT NOT NULL,
    date_from TEXT NOT NULL,
    date_to TEXT NOT NULL,
    amount REAL NOT NULL,
    rate REAL NOT NULL,
    term_days INTEGER NOT NULL,
    inflation REAL NOT NULL
)
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    conn.commit()
    return conn


def _row_to_deposit(row: sqlite3.Row) -> Deposit:
    return Deposit(
        id=row["id"],
        bank=row["bank"],
        date_from=date.fromisoformat(row["date_from"]),
        date_to=date.fromisoformat(row["date_to"]),
        amount=row["amount"],
        rate=row["rate"],
        term_days=row["term_days"],
        inflation=row["inflation"],
    )


def add_deposit(conn: sqlite3.Connection, deposit: Deposit) -> int:
    cursor = conn.execute(
        "INSERT INTO deposits (bank, date_from, date_to, amount, rate, term_days, inflation) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            deposit.bank,
            deposit.date_from.isoformat(),
            deposit.date_to.isoformat(),
            deposit.amount,
            deposit.rate,
            deposit.term_days,
            deposit.inflation,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_all_deposits(conn: sqlite3.Connection) -> list[Deposit]:
    rows = conn.execute("SELECT * FROM deposits ORDER BY id").fetchall()
    return [_row_to_deposit(row) for row in rows]


def get_deposit(conn: sqlite3.Connection, deposit_id: int) -> Deposit | None:
    row = conn.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,)).fetchone()
    return _row_to_deposit(row) if row else None


def update_deposit(conn: sqlite3.Connection, deposit: Deposit) -> None:
    if deposit.id is None:
        raise ValueError("Cannot update a deposit without an id")
    conn.execute(
        "UPDATE deposits SET bank = ?, date_from = ?, date_to = ?, amount = ?, "
        "rate = ?, term_days = ?, inflation = ? WHERE id = ?",
        (
            deposit.bank,
            deposit.date_from.isoformat(),
            deposit.date_to.isoformat(),
            deposit.amount,
            deposit.rate,
            deposit.term_days,
            deposit.inflation,
            deposit.id,
        ),
    )
    conn.commit()


def delete_deposit(conn: sqlite3.Connection, deposit_id: int) -> None:
    conn.execute("DELETE FROM deposits WHERE id = ?", (deposit_id,))
    conn.commit()
