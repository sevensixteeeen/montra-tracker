from datetime import date

from montra.models import Expense
from montra.repository import add_expense
from montra.services import monthly_summary


def test_monthly_summary_totals_by_category(conn):
    add_expense(conn, Expense(date(2026, 10, 2), 15000, "Food"))
    add_expense(conn, Expense(date(2026, 10, 9), 5050, "Food"))
    add_expense(conn, Expense(date(2026, 10, 5), 1200000, "Rent"))
    add_expense(conn, Expense(date(2026, 9, 28), 99900, "Shopping"))  # other month

    summary = monthly_summary(conn, 2026, 10)

    assert summary.count == 3
    assert summary.total_minor == 1220050
    assert list(summary.by_category.items()) == [("Rent", 1200000), ("Food", 20050)]


def test_monthly_summary_of_empty_month(conn):
    summary = monthly_summary(conn, 2026, 10)

    assert summary.count == 0
    assert summary.total_minor == 0
    assert summary.by_category == {}
