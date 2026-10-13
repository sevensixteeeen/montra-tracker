import pytest

from montra.db import connect


@pytest.fixture
def conn():
    connection = connect(":memory:")
    yield connection
    connection.close()
