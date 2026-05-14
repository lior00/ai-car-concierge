"""
Run inventory.sql against SQLite to create/populate inventory.db.
Safe to re-run: skips migration if the table already has data.
"""
import sqlite3
import logging
from pathlib import Path

from backend.config import DB_PATH, INVENTORY_SQL_PATH

logger = logging.getLogger(__name__)


def run_migration() -> None:
    sql_path = Path(INVENTORY_SQL_PATH)
    if not sql_path.exists():
        raise FileNotFoundError(f"inventory.sql not found at {sql_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        # Idempotency check — skip if data already loaded
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory'")
        table_exists = cursor.fetchone() is not None

        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM inventory")
            count = cursor.fetchone()[0]
            if count > 0:
                logger.info(f"Migration skipped — inventory table already has {count} rows.")
                return

        sql_script = sql_path.read_text(encoding="utf-8")
        conn.executescript(sql_script)
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM inventory")
        total = cursor.fetchone()[0]
        logger.info(f"Migration complete — {total} vehicles loaded into {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    run_migration()
