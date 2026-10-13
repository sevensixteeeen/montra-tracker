"""Calculations on top of the stored expenses (totals, breakdowns)."""

import sqlite3
from dataclasses import dataclass

from montra.repository import list_expenses


@dataclass(frozen=True, slots=True)
class MonthlySummary:
    year: int
    month: int
    count: int
    total_minor: int
    by_category: dict[str, int]  # category -> paise, biggest spend first


def monthly_summary(conn: sqlite3.Connection, year: int, month: int) -> MonthlySummary:
    expenses = list_expenses(conn, year, month)
    totals: dict[str, int] = {}
    for expense in expenses:
        totals[expense.category] = (
            totals.get(expense.category, 0) + expense.amount_minor
        )
    by_category = dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))
    return MonthlySummary(
        year=year,
        month=month,
        count=len(expenses),
        total_minor=sum(totals.values()),
        by_category=by_category,
    )
