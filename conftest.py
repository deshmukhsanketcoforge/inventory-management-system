from contextlib import closing

import pytest
from inventory_db import connect, create_tables
from seed_db import load_sample_data


@pytest.fixture
def empty_db():
    """A new in-memory database with the schema but no rows."""
    with closing(connect(":memory:")) as connection:
        create_tables(connection)
        yield connection  # the test runs here; closing() cleans up afterwards


@pytest.fixture
def db(empty_db):
    """The same database, filled with the sample suppliers, products and sales."""
    load_sample_data(empty_db)
    return empty_db