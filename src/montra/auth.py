"""The app's login PIN.

Only a salted scrypt hash is stored, never the PIN itself. Too many wrong PINs
in a row lock the app for a few minutes. To clear a forgotten PIN (expenses are
kept), run:

    uv run python -m montra.auth reset
"""

import hashlib
import hmac
import math
import secrets
import sys
from contextlib import closing
from datetime import UTC, datetime, timedelta

import psycopg

from montra.db import connect

PIN_LENGTH = 4
MAX_WRONG_TRIES = 5
LOCK_MINUTES = 5

# scrypt cost settings. They are saved next to each hash, so they can be raised
# later without locking out a PIN that was saved with the old ones.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
HASH_BYTES = 32


def _hash(pin: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        pin.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=HASH_BYTES
    )


def _locked_until(conn: psycopg.Connection, now: datetime) -> datetime | None:
    row = conn.execute(
        "SELECT locked_until FROM login_attempts WHERE id = 1"
    ).fetchone()
    if row is None or row["locked_until"] is None:
        return None
    return row["locked_until"] if row["locked_until"] > now else None


def is_valid_pin(pin: str) -> bool:
    """True for exactly PIN_LENGTH ordinary digits (0-9)."""
    return len(pin) == PIN_LENGTH and pin.isascii() and pin.isdigit()


def has_pin(conn: psycopg.Connection) -> bool:
    return conn.execute("SELECT 1 FROM auth WHERE id = 1").fetchone() is not None


def set_pin(conn: psycopg.Connection, pin: str) -> None:
    """Save a new PIN, replacing any existing one and clearing any lock."""
    if not is_valid_pin(pin):
        raise ValueError(f"The PIN must be exactly {PIN_LENGTH} digits.")
    salt = secrets.token_bytes(16)
    digest = _hash(pin, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    with conn.transaction():
        conn.execute("DELETE FROM auth")
        conn.execute(
            "INSERT INTO auth (id, salt, hash, n, r, p) VALUES (1, %s, %s, %s, %s, %s)",
            (salt, digest, SCRYPT_N, SCRYPT_R, SCRYPT_P),
        )
        conn.execute("DELETE FROM login_attempts")


def tries_left(conn: psycopg.Connection) -> int:
    """How many more wrong PINs are allowed before the app locks."""
    row = conn.execute("SELECT failed FROM login_attempts WHERE id = 1").fetchone()
    return MAX_WRONG_TRIES - (row["failed"] if row else 0)


def minutes_locked(conn: psycopg.Connection, now: datetime | None = None) -> int:
    """Minutes until the lock ends, rounded up. 0 means the app is not locked."""
    now = now or datetime.now(UTC)
    end = _locked_until(conn, now)
    return math.ceil((end - now).total_seconds() / 60) if end else 0


def check_pin(conn: psycopg.Connection, pin: str, now: datetime | None = None) -> bool:
    """True only if a PIN is set, the app is not locked, and this is the PIN.

    Each wrong PIN is counted, and MAX_WRONG_TRIES in a row lock the app for
    LOCK_MINUTES. Input that is not a PIN at all (wrong length, letters) is
    refused without being counted.
    """
    now = now or datetime.now(UTC)
    if not is_valid_pin(pin) or _locked_until(conn, now) is not None:
        return False
    row = conn.execute("SELECT salt, hash, n, r, p FROM auth WHERE id = 1").fetchone()
    if row is None:
        return False

    attempt = _hash(pin, bytes(row["salt"]), row["n"], row["r"], row["p"])
    correct = hmac.compare_digest(attempt, bytes(row["hash"]))
    with conn.transaction():
        failed = MAX_WRONG_TRIES - tries_left(conn) + 1
        conn.execute("DELETE FROM login_attempts")
        if not correct:
            lock_end = None
            if failed >= MAX_WRONG_TRIES:
                # Start the lock, and a fresh count for when it ends.
                failed = 0
                lock_end = now + timedelta(minutes=LOCK_MINUTES)
            conn.execute(
                "INSERT INTO login_attempts (id, failed, locked_until)"
                " VALUES (1, %s, %s)",
                (failed, lock_end),
            )
    return correct


def reset_pin(conn: psycopg.Connection) -> bool:
    """Remove the saved PIN and any lock. Returns False if there was no PIN."""
    with conn.transaction():
        cursor = conn.execute("DELETE FROM auth")
        conn.execute("DELETE FROM login_attempts")
    return cursor.rowcount > 0


if __name__ == "__main__":
    if sys.argv[1:] == ["reset"]:
        with closing(connect()) as connection:
            removed = reset_pin(connection)
        if removed:
            print("PIN cleared. Open Montra to create a new one.")
        else:
            print("No PIN was set.")
    else:
        print("Usage: uv run python -m montra.auth reset")
