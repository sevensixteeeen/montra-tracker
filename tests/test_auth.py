from datetime import UTC, date, datetime, timedelta

import pytest

from montra import auth
from montra.auth import (
    LOCK_MINUTES,
    MAX_WRONG_TRIES,
    check_pin,
    has_pin,
    is_valid_pin,
    minutes_locked,
    reset_pin,
    set_pin,
    tries_left,
)
from montra.models import Expense
from montra.repository import add_expense, list_expenses

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    """Real hashing is slow on purpose; a small cost keeps the tests quick."""
    monkeypatch.setattr(auth, "SCRYPT_N", 2**4)


def test_no_pin_at_first(conn):
    assert has_pin(conn) is False
    assert check_pin(conn, "1234") is False


@pytest.mark.parametrize("pin", ["0000", "4821", "0042"])
def test_four_digits_are_a_valid_pin(pin):
    assert is_valid_pin(pin) is True


@pytest.mark.parametrize(
    "pin", ["", "123", "12345", "12a4", " 123", "12.4", "１２３４"]
)
def test_anything_else_is_not_a_valid_pin(conn, pin):
    assert is_valid_pin(pin) is False
    with pytest.raises(ValueError):
        set_pin(conn, pin)
    assert has_pin(conn) is False


def test_right_pin_is_accepted_and_wrong_one_rejected(conn):
    set_pin(conn, "0042")

    assert has_pin(conn) is True
    assert check_pin(conn, "0042") is True
    assert check_pin(conn, "0043") is False
    assert check_pin(conn, "42") is False


def test_pin_itself_is_never_stored(conn):
    set_pin(conn, "4821")

    row = conn.execute("SELECT salt, hash FROM auth").fetchone()
    assert b"4821" not in bytes(row["salt"]) + bytes(row["hash"])


def test_same_pin_gives_a_different_hash_each_time(conn):
    set_pin(conn, "4821")
    first = bytes(conn.execute("SELECT hash FROM auth").fetchone()["hash"])
    set_pin(conn, "4821")
    second = bytes(conn.execute("SELECT hash FROM auth").fetchone()["hash"])

    assert first != second


def test_wrong_pins_count_down_and_a_right_one_resets_the_count(conn):
    set_pin(conn, "4821")
    assert tries_left(conn) == MAX_WRONG_TRIES

    check_pin(conn, "0000", NOW)
    check_pin(conn, "1111", NOW)
    assert tries_left(conn) == MAX_WRONG_TRIES - 2

    assert check_pin(conn, "4821", NOW) is True
    assert tries_left(conn) == MAX_WRONG_TRIES


def test_input_that_is_not_a_pin_is_not_counted(conn):
    set_pin(conn, "4821")

    for attempt in ["", "12", "abcd", "123456"]:
        assert check_pin(conn, attempt, NOW) is False

    assert tries_left(conn) == MAX_WRONG_TRIES


def test_too_many_wrong_pins_lock_the_app(conn):
    set_pin(conn, "4821")

    for _ in range(MAX_WRONG_TRIES):
        assert minutes_locked(conn, NOW) == 0
        check_pin(conn, "0000", NOW)

    assert minutes_locked(conn, NOW) == LOCK_MINUTES
    assert check_pin(conn, "4821", NOW) is False  # even the right PIN is refused
    assert minutes_locked(conn, NOW + timedelta(minutes=2, seconds=30)) == 3


def test_lock_ends_after_the_waiting_time(conn):
    set_pin(conn, "4821")
    for _ in range(MAX_WRONG_TRIES):
        check_pin(conn, "0000", NOW)

    later = NOW + timedelta(minutes=LOCK_MINUTES, seconds=1)

    assert minutes_locked(conn, later) == 0
    assert tries_left(conn) == MAX_WRONG_TRIES
    assert check_pin(conn, "4821", later) is True


def test_reset_clears_the_pin_and_the_lock_but_keeps_expenses(conn, user_id):
    saved = add_expense(conn, user_id, Expense(date(2026, 10, 13), 17500, "Food"))
    set_pin(conn, "4821")
    for _ in range(MAX_WRONG_TRIES):
        check_pin(conn, "0000", NOW)

    assert reset_pin(conn) is True
    assert reset_pin(conn) is False
    assert has_pin(conn) is False
    assert minutes_locked(conn, NOW) == 0
    assert list_expenses(conn, user_id, 2026, 10) == [saved]


def test_setting_a_new_pin_replaces_the_old_one(conn):
    set_pin(conn, "1111")
    set_pin(conn, "2222")

    assert check_pin(conn, "1111") is False
    assert check_pin(conn, "2222") is True
