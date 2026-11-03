from contextlib import closing

from inventory_db import backup_database, connect
from seed_db import COUNT_ROWS_SQL


def row_counts(connection):
    return connection.execute(COUNT_ROWS_SQL).fetchall()


def test_backup_passes_the_integrity_check_and_has_the_same_row_counts(db, tmp_path):
    backup_path = tmp_path / "backup.db"
    backup_database(db, backup_path)

    with closing(connect(backup_path)) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert [tuple(row) for row in row_counts(backup)] == [
            tuple(row) for row in row_counts(db)
        ]


def test_backup_keeps_the_data_as_it_was_at_the_time(db, tmp_path):
    backup_path = tmp_path / "backup.db"
    backup_database(db, backup_path)
    db.execute("DELETE FROM sale_items")  # a change made after the backup

    with closing(connect(backup_path)) as backup:
        assert backup.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0] == 12
