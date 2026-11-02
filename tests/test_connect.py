from contextlib import closing

from inventory_db import DEFAULT_DB, connect, create_tables, get_db_path


def test_connect_turns_foreign_keys_on():
    with closing(connect(":memory:")) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_connect_rows_are_readable_by_column_name():
    with closing(connect(":memory:")) as connection:
        row = connection.execute("SELECT 42 AS answer").fetchone()
        assert row["answer"] == 42


def test_connect_uses_the_path_it_is_given(tmp_path):
    db_file = tmp_path / "given.db"  # a real file here, other tests use :memory:
    with closing(connect(db_file)) as connection:
        create_tables(connection)
    assert db_file.exists()


def test_connect_creates_a_missing_folder(tmp_path):
    db_file = tmp_path / "data" / "new.db"
    with closing(connect(db_file)):
        pass
    assert db_file.exists()


def test_database_path_comes_from_the_variable():
    path = "/data/inventory.db"
    assert get_db_path({"INVENTORY_DB": path}) == path


def test_database_path_falls_back_in_the_data_folder():
    assert get_db_path({}) == DEFAULT_DB