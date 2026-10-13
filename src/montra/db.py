"""SQLite connection and schema."""

import sqlite3
from pathlib import Path

from montra.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    spent_on     TEXT    NOT NULL,                       -- ISO date, YYYY-MM-DD
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    category     TEXT    NOT NULL,
    note         TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_expenses_spent_on ON expenses (spent_on);
"""


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Open the database, creating the file and tables on first use."""
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
