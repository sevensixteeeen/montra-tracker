from datetime import date

import psycopg
import pytest

from montra.models import Expense
from montra.repository import (
    add_expense,
    delete_expense,
    ensure_owner,
    list_expenses,
)


def test_ensure_owner_creates_one_person_and_keeps_returning_them(conn):
    first = ensure_owner(conn)

    assert ensure_owner(conn) == first
    assert conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 1


def test_add_expense_assigns_id_and_round_trips(conn, user_id):
    saved = add_expense(
        conn, user_id, Expense(date(2026, 10, 13), 24950, "Food", "lunch")
    )

    assert saved.id is not None
    assert list_expenses(conn, user_id, 2026, 10) == [saved]


def test_list_expenses_only_returns_the_requested_month(conn, user_id):
    for day in (
        date(2026, 9, 30),
        date(2026, 10, 1),
        date(2026, 10, 31),
        date(2026, 11, 1),
    ):
        add_expense(conn, user_id, Expense(day, 100, "Other"))

    october = list_expenses(conn, user_id, 2026, 10)

    assert [e.spent_on for e in october] == [date(2026, 10, 31), date(2026, 10, 1)]


def test_list_expenses_handles_december(conn, user_id):
    add_expense(conn, user_id, Expense(date(2026, 12, 31), 100, "Other"))
    add_expense(conn, user_id, Expense(date(2027, 1, 1), 100, "Other"))

    december = list_expenses(conn, user_id, 2026, 12)

    assert [e.spent_on for e in december] == [date(2026, 12, 31)]


def test_expenses_on_the_same_day_come_newest_first(conn, user_id):
    first = add_expense(conn, user_id, Expense(date(2026, 10, 13), 100, "Food"))
    second = add_expense(conn, user_id, Expense(date(2026, 10, 13), 200, "Food"))

    assert list_expenses(conn, user_id, 2026, 10) == [second, first]


def test_delete_expense(conn, user_id):
    saved = add_expense(conn, user_id, Expense(date(2026, 10, 13), 500, "Transport"))

    assert delete_expense(conn, user_id, saved.id) is True
    assert delete_expense(conn, user_id, saved.id) is False
    assert list_expenses(conn, user_id, 2026, 10) == []


def test_people_only_see_their_own_expenses(conn, user_id, friend_id):
    mine = add_expense(conn, user_id, Expense(date(2026, 10, 13), 500, "Food"))
    theirs = add_expense(conn, friend_id, Expense(date(2026, 10, 13), 900, "Rent"))

    assert list_expenses(conn, user_id, 2026, 10) == [mine]
    assert list_expenses(conn, friend_id, 2026, 10) == [theirs]


def test_people_cannot_delete_each_others_expenses(conn, user_id, friend_id):
    theirs = add_expense(conn, friend_id, Expense(date(2026, 10, 13), 900, "Rent"))

    assert delete_expense(conn, user_id, theirs.id) is False
    assert list_expenses(conn, friend_id, 2026, 10) == [theirs]


def test_an_expense_cannot_be_saved_for_a_person_who_does_not_exist(conn, user_id):
    with pytest.raises(psycopg.IntegrityError):
        add_expense(conn, user_id + 999, Expense(date(2026, 10, 13), 500, "Food"))


def test_a_note_with_awkward_characters_is_stored_as_typed(conn, user_id):
    note = '50% off; it\'s "new" -- DROP TABLE expenses; ₹ %s'
    saved = add_expense(conn, user_id, Expense(date(2026, 10, 13), 500, "Food", note))

    assert list_expenses(conn, user_id, 2026, 10) == [saved]
    assert saved.note == note
