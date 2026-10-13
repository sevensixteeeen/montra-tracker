"""One-off: copy the expenses and PIN from the old laptop file into Postgres.

    uv run python -m montra.sqlite_import

The old file is only read, never changed. Everything in it belonged to one
person, so every expense is handed to the app's owner.
"""

import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg

from montra.auth import has_pin
from montra.config import PROJECT_ROOT
from montra.db import connect, create_tables
from montra.money import format_money
from montra.repository import ensure_owner

OLD_FILE = PROJECT_ROOT / "data" / "expenses.db"


def _read_old_file(old_file: Path) -> tuple[list[sqlite3.Row], sqlite3.Row | None]:
    """The expenses and the PIN row (if any) from the old SQLite file."""
    with closing(
        sqlite3.connect(f"file:{old_file.as_posix()}?mode=ro", uri=True)
    ) as old:
        old.row_factory = sqlite3.Row
        expenses = old.execute(
            "SELECT spent_on, amount_minor, category, note, created_at"
            " FROM expenses ORDER BY id"
        ).fetchall()
        has_auth_table = old.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'auth'"
        ).fetchone()
        pin = None
        if has_auth_table:
            pin = old.execute("SELECT salt, hash, n, r, p FROM auth").fetchone()
    return expenses, pin


def copy_from_sqlite(old_file: Path, conn: psycopg.Connection) -> dict:
    """Copy everything across in one go and report what was copied.

    Refuses to run if the Postgres database already holds expenses, so running
    it twice cannot create duplicates. If anything fails, nothing is copied.
    """
    expenses, pin = _read_old_file(old_file)

    with conn.transaction():
        if conn.execute("SELECT 1 FROM expenses LIMIT 1").fetchone():
            raise RuntimeError(
                "The online database already has expenses, so nothing was copied."
            )
        owner = ensure_owner(conn)
        for row in expenses:
            conn.execute(
                "INSERT INTO expenses"
                " (user_id, spent_on, amount_minor, category, note, created_at)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    owner,
                    date.fromisoformat(row["spent_on"]),
                    row["amount_minor"],
                    row["category"],
                    row["note"],
                    # The old file stored times in UTC without saying so.
                    datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
                ),
            )
        pin_copied = False
        if pin is not None and not has_pin(conn):
            conn.execute(
                "INSERT INTO auth (id, salt, hash, n, r, p)"
                " VALUES (1, %s, %s, %s, %s, %s)",
                (pin["salt"], pin["hash"], pin["n"], pin["r"], pin["p"]),
            )
            pin_copied = True

        saved = conn.execute(
            "SELECT COUNT(*) AS count, COALESCE(SUM(amount_minor), 0) AS total"
            " FROM expenses WHERE user_id = %s",
            (owner,),
        ).fetchone()
        expected_total = sum(row["amount_minor"] for row in expenses)
        if (saved["count"], saved["total"]) != (len(expenses), expected_total):
            raise RuntimeError(
                "The copy does not match the old file; nothing was kept."
            )

    return {"expenses": len(expenses), "total_minor": expected_total, "pin": pin_copied}


if __name__ == "__main__":
    if not OLD_FILE.exists():
        raise SystemExit(f"No old database file found at {OLD_FILE}")
    with closing(connect()) as connection:
        create_tables(connection)
        result = copy_from_sqlite(OLD_FILE, connection)
    print(
        f"Copied {result['expenses']} expense(s) worth"
        f" {format_money(result['total_minor'])}."
        f" PIN copied: {'yes' if result['pin'] else 'no'}."
    )
    print(f"The old file was not changed: {OLD_FILE}")
