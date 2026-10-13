import os
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse

import pgserver
import pytest

from montra.db import connect, create_tables
from montra.repository import ensure_owner

# The tests run against a small Postgres server that lives only on this
# computer, in a folder git ignores. They never touch the real online database.
TEST_SERVER_FILES = Path(__file__).resolve().parents[1] / "data" / "test-postgres"


@pytest.fixture(scope="session")
def test_database_url():
    server = pgserver.get_server(TEST_SERVER_FILES, cleanup_mode="stop")
    url = server.get_uri()
    # Each test empties the tables, so make very sure this is the local server.
    assert urlparse(url).hostname in ("127.0.0.1", "localhost", None), url

    # Anything that connects without being told where also gets the test server.
    real_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    with closing(connect(url)) as conn:
        create_tables(conn)
    yield url
    if real_url is None:
        del os.environ["DATABASE_URL"]
    else:
        os.environ["DATABASE_URL"] = real_url
    server.cleanup()


@pytest.fixture
def conn(test_database_url):
    """A connection to the test database, emptied before each test."""
    connection = connect(test_database_url)
    connection.execute(
        "TRUNCATE users, expenses, auth, login_attempts RESTART IDENTITY CASCADE"
    )
    yield connection
    connection.close()


@pytest.fixture
def user_id(conn):
    """The person most tests act as."""
    return ensure_owner(conn)


@pytest.fixture
def friend_id(conn, user_id):
    """A second person, for checking that people cannot reach each other's data."""
    row = conn.execute(
        "INSERT INTO users (name) VALUES ('friend') RETURNING id"
    ).fetchone()
    return row["id"]
