import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime

import pytest

from montra.auth import has_pin
from montra.repository import ensure_owner, list_expenses
from montra.sqlite_import import copy_from_sqlite

# The laptop file as it was before expenses had an owner.
OLD_FORMAT = """
CREATE TABLE expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    spent_on     TEXT    NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    category     TEXT    NOT NULL,
    note         TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE auth (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    salt BLOB NOT NULL, hash BLOB NOT NULL,
    n INTEGER NOT NULL, r INTEGER NOT NULL, p INTEGER NOT NULL
);
INSERT INTO expenses (id, spent_on, amount_minor, category, note, created_at)
    VALUES (1, '2026-10-13', 17500, 'Transport', 'auto', '2026-10-13 08:00:00'),
           (5, '2026-10-02', 99900, 'Rent', '', '2026-10-02 09:30:00');
INSERT INTO auth (id, salt, hash, n, r, p) VALUES (1, x'0102', x'0304', 16, 8, 1);
"""

# The same file after step 1 added owners.
OWNER_FORMAT = """
CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, name TEXT);
CREATE TABLE expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users (id),
    spent_on     TEXT    NOT NULL,
    amount_minor INTEGER NOT NULL,
    category     TEXT    NOT NULL,
    note         TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO users (name) VALUES ('');
INSERT INTO expenses (user_id, spent_on, amount_minor, category, note, created_at)
    VALUES (1, '2026-10-13', 17500, 'Transport', 'auto', '2026-10-13 08:00:00');
"""


def make_file(path, script):
    with closing(sqlite3.connect(path)) as raw:
        raw.executescript(script)
    return path


def test_old_file_is_copied_to_the_owner(conn, tmp_path):
    old = make_file(tmp_path / "old.db", OLD_FORMAT)

    result = copy_from_sqlite(old, conn)

    owner = ensure_owner(conn)
    copied = list_expenses(conn, owner, 2026, 10)
    assert result == {"expenses": 2, "total_minor": 117400, "pin": True}
    assert [(e.spent_on, e.amount_minor, e.category, e.note) for e in copied] == [
        (date(2026, 10, 13), 17500, "Transport", "auto"),
        (date(2026, 10, 2), 99900, "Rent", ""),
    ]
    created = conn.execute(
        "SELECT created_at FROM expenses ORDER BY spent_on DESC LIMIT 1"
    ).fetchone()["created_at"]
    assert created == datetime(2026, 10, 13, 8, 0, tzinfo=UTC)


def test_the_pin_comes_across_unchanged(conn, tmp_path):
    old = make_file(tmp_path / "old.db", OLD_FORMAT)

    copy_from_sqlite(old, conn)

    row = conn.execute("SELECT salt, hash, n, r, p FROM auth").fetchone()
    assert has_pin(conn) is True
    assert (bytes(row["salt"]), bytes(row["hash"])) == (b"\x01\x02", b"\x03\x04")
    assert (row["n"], row["r"], row["p"]) == (16, 8, 1)


def test_file_that_already_has_owners_is_copied_too(conn, tmp_path):
    old = make_file(tmp_path / "old.db", OWNER_FORMAT)

    result = copy_from_sqlite(old, conn)

    assert result == {"expenses": 1, "total_minor": 17500, "pin": False}
    assert conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 1


def test_copying_twice_is_refused_and_adds_nothing(conn, tmp_path):
    old = make_file(tmp_path / "old.db", OLD_FORMAT)
    copy_from_sqlite(old, conn)

    with pytest.raises(RuntimeError, match="already has expenses"):
        copy_from_sqlite(old, conn)

    assert conn.execute("SELECT COUNT(*) AS n FROM expenses").fetchone()["n"] == 2


def test_new_expenses_get_ids_after_the_copied_ones(conn, tmp_path):
    old = make_file(tmp_path / "old.db", OLD_FORMAT)
    copy_from_sqlite(old, conn)

    row = conn.execute(
        "INSERT INTO expenses (user_id, spent_on, amount_minor, category)"
        " VALUES (%s, '2026-10-14', 100, 'Other') RETURNING id",
        (ensure_owner(conn),),
    ).fetchone()

    assert row["id"] == 3


def test_the_old_file_is_not_changed(conn, tmp_path):
    old = make_file(tmp_path / "old.db", OLD_FORMAT)
    before = old.read_bytes()

    copy_from_sqlite(old, conn)

    assert old.read_bytes() == before
