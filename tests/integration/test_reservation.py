"""Integration tests for reservation_tool DB write behavior."""
import sqlite3
import tempfile
import os
import pytest
from unittest.mock import patch

from backend.agent.tools.reservation_tool import reserve_vehicle


@pytest.fixture
def fresh_db(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY, make TEXT, model TEXT, year INTEGER,
            trim TEXT, color TEXT, fuel_type TEXT, transmission TEXT,
            mileage INTEGER, price REAL, stock_count INTEGER, vin TEXT, description TEXT
        );
        INSERT INTO inventory VALUES (1,'Tesla','Model S',2022,'Plaid','Red','Electric','Automatic',6000,108000,3,'VIN_S1','');
    """)
    conn.commit()
    conn.close()

    with patch("backend.db.session.DB_PATH", db_path):
        yield db_path

    os.unlink(db_path)


def get_stock(db_path: str, vehicle_id: int) -> int:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT stock_count FROM inventory WHERE id = ?", (vehicle_id,)).fetchone()
    conn.close()
    return row[0] if row else -1


class TestReservationDBWrite:
    def test_stock_persists_after_reservation(self, fresh_db):
        reserve_vehicle(1)
        assert get_stock(fresh_db, 1) == 2

    def test_multiple_reservations_decrement_correctly(self, fresh_db):
        reserve_vehicle(1)
        reserve_vehicle(1)
        reserve_vehicle(1)
        assert get_stock(fresh_db, 1) == 0

    def test_fourth_reservation_fails_at_zero(self, fresh_db):
        reserve_vehicle(1)
        reserve_vehicle(1)
        reserve_vehicle(1)
        result = reserve_vehicle(1)
        assert result["success"] is False
        assert get_stock(fresh_db, 1) == 0  # no negative stock
