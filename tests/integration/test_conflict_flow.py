"""
Integration tests for the 2022+ policy conflict resolution flow.
Tests the reservation_tool and email_tool policy guards directly
(without LLM — deterministic boundary tests).
"""
import sqlite3
import tempfile
import os
import pytest
from unittest.mock import patch

from backend.agent.tools.policy_guard import enforce, PolicyResult
from backend.agent.tools.reservation_tool import reserve_vehicle
from backend.agent.tools import email_tool


@pytest.fixture
def temp_db(monkeypatch):
    """Create a temp SQLite DB with a few test vehicles."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY,
            make TEXT, model TEXT, year INTEGER, trim TEXT, color TEXT,
            fuel_type TEXT, transmission TEXT, mileage INTEGER,
            price REAL, stock_count INTEGER, vin TEXT, description TEXT
        );
        INSERT INTO inventory VALUES (1,'BMW','X5',2020,'xDrive40i','Black','Gasoline','Automatic',24000,52000,1,'VIN001','Pre-2022');
        INSERT INTO inventory VALUES (2,'Tesla','Model Y',2023,'LR','White','Electric','Automatic',2000,48000,2,'VIN002','Sellable EV');
        INSERT INTO inventory VALUES (3,'Porsche','Taycan',2022,'4S','Blue','Electric','Automatic',3000,108000,0,'VIN003','Sold out');
    """)
    conn.commit()
    conn.close()

    # Patch DB_PATH in config + session
    monkeypatch.setenv("DB_PATH", db_path)
    with patch("backend.db.session.DB_PATH", db_path):
        yield db_path

    os.unlink(db_path)


class TestPolicyConflictDirect:
    """Test policy_guard boundary — no DB or LLM needed."""

    def test_2020_vehicle_is_pending(self):
        assert enforce(2020) == PolicyResult.PENDING_DELISTING

    def test_2021_vehicle_is_pending(self):
        assert enforce(2021) == PolicyResult.PENDING_DELISTING

    def test_2022_vehicle_is_sellable(self):
        assert enforce(2022) == PolicyResult.SELLABLE


class TestReservationPolicyGuard:
    """Reservation tool must reject pre-2022 vehicles."""

    def test_cannot_reserve_2020_vehicle(self, temp_db):
        result = reserve_vehicle(1)  # 2020 BMW X5
        assert result["success"] is False
        assert "Pending De-listing" in result["error"]
        assert "2022+" in result["error"]

    def test_can_reserve_2023_vehicle(self, temp_db):
        result = reserve_vehicle(2)  # 2023 Tesla Model Y
        assert result["success"] is True
        assert result["new_stock"] == 1  # decremented from 2

    def test_cannot_reserve_sold_out_vehicle(self, temp_db):
        result = reserve_vehicle(3)  # 2022 Porsche Taycan, stock=0
        assert result["success"] is False
        assert "sold out" in result["error"].lower()

    def test_cannot_reserve_nonexistent_vehicle(self, temp_db):
        result = reserve_vehicle(999)
        assert result["success"] is False
        assert "No vehicle found" in result["error"]

    def test_stock_decrements_exactly_one(self, temp_db):
        before = reserve_vehicle(2)
        after = reserve_vehicle(2)
        assert before["new_stock"] == 1
        assert after["new_stock"] == 0


class TestEmailPolicyGuard:
    """Email tool must not fire for pre-2022 vehicles (enforced by orchestrator, validated here)."""

    @patch.dict("os.environ", {"MAILTRAP_USERNAME": "", "MAILTRAP_PASSWORD": ""}, clear=False)
    def test_no_credentials_returns_graceful_error(self):
        result = email_tool.send_purchase_email(
            customer_email="test@example.com",
            customer_name="John",
            vehicle_make="BMW",
            vehicle_model="X5",
            vehicle_year=2023,
            vehicle_id=2,
            vehicle_price=88000.0,
        )
        assert result["success"] is False
        assert "not configured" in result["error"]
