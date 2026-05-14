"""Unit tests for sql_tool.py — SQL validation and execution."""
import pytest
from unittest.mock import patch, MagicMock

from backend.agent.tools import sql_tool
from backend.agent.tools.sql_tool import _validate_sql, _BLOCKED_PATTERN


class TestValidateSQL:
    def test_valid_select_passes(self):
        sql = "SELECT * FROM inventory WHERE year >= 2022 LIMIT 10"
        assert _validate_sql(sql) == sql

    def test_update_blocked(self):
        with pytest.raises(ValueError, match="Blocked SQL"):
            _validate_sql("UPDATE inventory SET stock_count = 0")

    def test_delete_blocked(self):
        with pytest.raises(ValueError, match="Blocked SQL"):
            _validate_sql("DELETE FROM inventory")

    def test_drop_blocked(self):
        with pytest.raises(ValueError, match="Blocked SQL"):
            _validate_sql("DROP TABLE inventory")

    def test_insert_blocked(self):
        with pytest.raises(ValueError, match="Blocked SQL"):
            _validate_sql("INSERT INTO inventory VALUES (1, 'BMW')")

    def test_non_select_blocked(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_sql("PRAGMA table_info(inventory)")

    def test_case_insensitive_block(self):
        with pytest.raises(ValueError):
            _validate_sql("update inventory set price = 0")


class TestBlockedPattern:
    @pytest.mark.parametrize("keyword", ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"])
    def test_blocks_all_dml_ddl(self, keyword):
        assert _BLOCKED_PATTERN.search(f"{keyword} something") is not None


class TestQueryInventory:
    @patch.object(sql_tool, "_generate_sql", return_value="SELECT * FROM inventory WHERE fuel_type = 'Electric' LIMIT 10")
    @patch("backend.agent.tools.sql_tool.get_db")
    def test_returns_vehicles(self, mock_db, mock_sql):
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchall.return_value = [
            {"id": 1, "make": "Tesla", "model": "Model Y", "year": 2023,
             "price": 48000.0, "stock_count": 5, "fuel_type": "Electric",
             "trim": "LR", "color": "White", "mileage": 2000, "vin": "X", "description": ""}
        ]
        mock_db.return_value = mock_conn
        result = sql_tool.query_inventory("show me electric cars")
        assert result["count"] == 1
        assert result["vehicles"][0]["make"] == "Tesla"

    @patch.object(sql_tool, "_generate_sql", return_value="UNSUPPORTED")
    def test_unsupported_query(self, mock_sql):
        result = sql_tool.query_inventory("what is the weather today")
        assert result["count"] == 0
        assert result.get("unsupported") is True
