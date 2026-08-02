import os
import sqlite3
from pathlib import Path

# Ensure the backend module is importable
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.main import DB_PATH, init_db


def test_database_initialisation_and_tables(tmp_path: Path):
    """Run the migration and verify that all expected tables exist.

    The test creates a temporary SQLite file to avoid interfering with the
    development database. ``init_db`` is patched to use this temporary path.
    """
    # Point the DB_PATH to a temporary location for isolation
    original_db_path = DB_PATH
    try:
        # Override the global DB_PATH used by init_db
        backend_main = sys.modules["backend.main"]
        backend_main.DB_PATH = tmp_path / "test_app.db"
        # Initialise (runs migration script)
        init_db()
        # Verify the file was created
        assert backend_main.DB_PATH.exists()
        # Connect and check tables
        conn = sqlite3.connect(backend_main.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        expected = {"users", "boards", "columns", "cards"}
        assert expected.issubset(tables)
    finally:
        # Restore original path to avoid side effects
        backend_main.DB_PATH = original_db_path