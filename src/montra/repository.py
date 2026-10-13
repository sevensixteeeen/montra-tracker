"""Reads and writes expenses. The only module that contains SQL queries."""

import sqlite3
from dataclasses import replace
from datetime import date

from montra.models import Expense


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    """First day of the month and first day of the next one, as ISO strings."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


def _to_expense(row: sqlite3.Row) -> Expense:
    return Expense(
        id=row["id"],
        spent_on=date.fromisoformat(row["spent_on"]),
        amount_minor=row["amount_minor"],
        category=row["category"],
        note=row["note"],
    )


def add_expense(conn: sqlite3.Connection, expense: Expense) -> Expense:
    """Save an expense and return it with its new id."""
    with conn:
        cursor = conn.execute(
            "INSERT INTO expenses (spent_on, amount_minor, category, note)"
            " VALUES (?, ?, ?, ?)",
            (
                expense.spent_on.isoformat(),
                expense.amount_minor,
                expense.category,
                expense.note,
            ),
        )
    return replace(expense, id=cursor.lastrowid)


def list_expenses(conn: sqlite3.Connection, year: int, month: int) -> list[Expense]:
    """All expenses in the given month, newest first."""
    rows = conn.execute(
        "SELECT id, spent_on, amount_minor, category, note FROM expenses"
        " WHERE spent_on >= ? AND spent_on < ?"
        " ORDER BY spent_on DESC, id DESC",
        _month_bounds(year, month),
    ).fetchall()
    return [_to_expense(row) for row in rows]


def delete_expense(conn: sqlite3.Connection, expense_id: int) -> bool:
    """Delete an expense. Returns False if there was no such id."""
    with conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return cursor.rowcount > 0
