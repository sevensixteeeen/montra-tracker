"""Reads and writes expenses. The only module that contains SQL queries.

Every function that touches expenses takes the owner's `user_id` and only ever
reads or changes that person's rows.
"""

from dataclasses import replace
from datetime import date

import psycopg

from montra.models import Expense


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """First day of the month and first day of the next one."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def _to_expense(row: dict) -> Expense:
    return Expense(
        id=row["id"],
        spent_on=row["spent_on"],
        amount_minor=row["amount_minor"],
        category=row["category"],
        note=row["note"],
    )


def ensure_owner(conn: psycopg.Connection) -> int:
    """Id of the person this copy of the app belongs to, created on first use.

    Until people sign in with their own accounts there is exactly one person.
    """
    with conn.transaction():
        row = conn.execute("SELECT MIN(id) AS id FROM users").fetchone()
        if row["id"] is not None:
            return row["id"]
        row = conn.execute(
            "INSERT INTO users (name) VALUES ('') RETURNING id"
        ).fetchone()
        return row["id"]


def add_expense(conn: psycopg.Connection, user_id: int, expense: Expense) -> Expense:
    """Save an expense for this person and return it with its new id."""
    row = conn.execute(
        "INSERT INTO expenses (user_id, spent_on, amount_minor, category, note)"
        " VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (
            user_id,
            expense.spent_on,
            expense.amount_minor,
            expense.category,
            expense.note,
        ),
    ).fetchone()
    return replace(expense, id=row["id"])


def list_expenses(
    conn: psycopg.Connection, user_id: int, year: int, month: int
) -> list[Expense]:
    """This person's expenses in the given month, newest first."""
    rows = conn.execute(
        "SELECT id, spent_on, amount_minor, category, note FROM expenses"
        " WHERE user_id = %s AND spent_on >= %s AND spent_on < %s"
        " ORDER BY spent_on DESC, id DESC",
        (user_id, *_month_bounds(year, month)),
    ).fetchall()
    return [_to_expense(row) for row in rows]


def delete_expense(conn: psycopg.Connection, user_id: int, expense_id: int) -> bool:
    """Delete one of this person's expenses.

    Returns False if there is no such expense, or it belongs to someone else.
    """
    cursor = conn.execute(
        "DELETE FROM expenses WHERE id = %s AND user_id = %s",
        (expense_id, user_id),
    )
    return cursor.rowcount > 0
