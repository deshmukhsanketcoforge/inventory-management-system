import os
import sqlite3
from pathlib import Path

CODE_DIR = Path(__file__).parent
SCHEMA_PATH = CODE_DIR / "schema.sql"
DEFAULT_DB = str(CODE_DIR / "data" / "inventory.db")


def get_db_path(environ=os.environ):
    """Database file from INVENTORY_DB, or data/inventory.db next to the code."""
    return environ.get("INVENTORY_DB", DEFAULT_DB)


def connect(db_path=None):
    """Open the database with foreign keys on and rows readable by column name."""
    if db_path is None:
        db_path = get_db_path()
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)  # e.g. data/ on first run
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_tables(connection):
    """Run schema.sql. Safe to call again, existing tables and data are kept."""
    connection.executescript(SCHEMA_PATH.read_text())
