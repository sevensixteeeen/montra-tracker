import psycopg
import pytest

from montra import config
from montra.db import create_tables


def test_creating_the_tables_twice_changes_nothing(conn, user_id):
    create_tables(conn)

    assert conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 1


def test_every_expense_must_have_an_owner(conn):
    with pytest.raises(psycopg.IntegrityError):
        conn.execute(
            "INSERT INTO expenses (spent_on, amount_minor, category)"
            " VALUES ('2026-10-14', 100, 'Other')"
        )


def test_an_amount_must_be_more_than_zero(conn, user_id):
    with pytest.raises(psycopg.IntegrityError):
        conn.execute(
            "INSERT INTO expenses (user_id, spent_on, amount_minor, category)"
            " VALUES (%s, '2026-10-14', 0, 'Other')",
            (user_id,),
        )


def test_database_address_comes_from_the_environment_first(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/db")

    assert config.database_url() == "postgresql://example.invalid/db"


def test_database_address_is_read_from_the_private_settings_file(monkeypatch, tmp_path):
    settings = tmp_path / "secrets.toml"
    # Notepad on Windows may add an invisible marker at the start of the file.
    settings.write_text(
        'DATABASE_URL = "postgresql://example.invalid/db"\n', encoding="utf-8-sig"
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "SECRETS_FILE", settings)

    assert config.database_url() == "postgresql://example.invalid/db"


def test_a_placeholder_address_is_refused_with_a_clear_message(monkeypatch, tmp_path):
    settings = tmp_path / "secrets.toml"
    settings.write_text('DATABASE_URL = "PASTE-YOUR-NEON-CONNECTION-STRING-HERE"\n')
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "SECRETS_FILE", settings)

    with pytest.raises(RuntimeError, match="No database address found"):
        config.database_url()
