"""
SQLite connection factory. Provides a context-managed connection
with WAL mode enabled for concurrent read performance.
"""
import sqlite3
from contextlib import contextmanager
from typing import Generator

from backend.config import DB_PATH


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # rows accessible as dicts
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _get_connection()
    try:
        yield conn
    finally:
        conn.close()
