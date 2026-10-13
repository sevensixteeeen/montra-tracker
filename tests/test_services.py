from datetime import date

from montra.models import Expense
from montra.repository import add_expense, list_expenses
from montra.services import monthly_summary


def test_monthly_summary_totals_by_category():
    expenses = [
        Expense(date(2026, 10, 2), 15000, "Food"),
        Expense(date(2026, 10, 9), 5050, "Food"),
        Expense(date(2026, 10, 5), 1200000, "Rent"),
    ]

    summary = monthly_summary(expenses)

    assert summary.count == 3
    assert summary.total_minor == 1220050
    assert list(summary.by_category.items()) == [("Rent", 1200000), ("Food", 20050)]


def test_monthly_summary_of_empty_month():
    summary = monthly_summary([])

    assert summary.count == 0
    assert summary.total_minor == 0
    assert summary.by_category == {}


def test_a_persons_month_leaves_out_other_months_and_other_people(
    conn, user_id, friend_id
):
    add_expense(conn, user_id, Expense(date(2026, 10, 2), 15000, "Food"))
    add_expense(conn, user_id, Expense(date(2026, 9, 28), 99900, "Shopping"))
    add_expense(conn, friend_id, Expense(date(2026, 10, 2), 700000, "Rent"))

    summary = monthly_summary(list_expenses(conn, user_id, 2026, 10))

    assert summary.count == 1
    assert summary.total_minor == 15000
    assert summary.by_category == {"Food": 15000}
