from datetime import date

from montra.models import Expense
from montra.repository import add_expense, delete_expense, list_expenses


def test_add_expense_assigns_id_and_round_trips(conn):
    saved = add_expense(conn, Expense(date(2026, 10, 13), 24950, "Food", "lunch"))

    assert saved.id is not None
    assert list_expenses(conn, 2026, 10) == [saved]


def test_list_expenses_only_returns_the_requested_month(conn):
    for day in (
        date(2026, 9, 30),
        date(2026, 10, 1),
        date(2026, 10, 31),
        date(2026, 11, 1),
    ):
        add_expense(conn, Expense(day, 100, "Other"))

    october = list_expenses(conn, 2026, 10)

    assert [e.spent_on for e in october] == [date(2026, 10, 31), date(2026, 10, 1)]


def test_list_expenses_handles_december(conn):
    add_expense(conn, Expense(date(2026, 12, 31), 100, "Other"))
    add_expense(conn, Expense(date(2027, 1, 1), 100, "Other"))

    assert [e.spent_on for e in list_expenses(conn, 2026, 12)] == [date(2026, 12, 31)]


def test_delete_expense(conn):
    saved = add_expense(conn, Expense(date(2026, 10, 13), 500, "Transport"))

    assert delete_expense(conn, saved.id) is True
    assert delete_expense(conn, saved.id) is False
    assert list_expenses(conn, 2026, 10) == []
