"""Calculations on top of the stored expenses (totals, breakdowns)."""

from dataclasses import dataclass

from montra.models import Expense


@dataclass(frozen=True, slots=True)
class MonthlySummary:
    count: int
    total_minor: int
    by_category: dict[str, int]  # category -> paise, biggest spend first


def monthly_summary(expenses: list[Expense]) -> MonthlySummary:
    """Totals for a list of expenses, usually one person's month.

    Works on a list that is already loaded, so it needs no trip to the database.
    """
    totals: dict[str, int] = {}
    for expense in expenses:
        totals[expense.category] = (
            totals.get(expense.category, 0) + expense.amount_minor
        )
    by_category = dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))
    return MonthlySummary(
        count=len(expenses),
        total_minor=sum(totals.values()),
        by_category=by_category,
    )
