"""Unit tests for policy_guard.py — the year eligibility rule."""
import pytest
from backend.agent.tools.policy_guard import enforce, is_sellable, label_vehicles, PolicyResult


class TestEnforce:
    def test_2022_is_sellable(self):
        assert enforce(2022) == PolicyResult.SELLABLE

    def test_2023_is_sellable(self):
        assert enforce(2023) == PolicyResult.SELLABLE

    def test_2025_is_sellable(self):
        assert enforce(2025) == PolicyResult.SELLABLE

    def test_2021_is_pending(self):
        assert enforce(2021) == PolicyResult.PENDING_DELISTING

    def test_2020_is_pending(self):
        assert enforce(2020) == PolicyResult.PENDING_DELISTING

    def test_2019_is_pending(self):
        assert enforce(2019) == PolicyResult.PENDING_DELISTING

    def test_2000_is_pending(self):
        assert enforce(2000) == PolicyResult.PENDING_DELISTING

    def test_none_raises_value_error(self):
        with pytest.raises(ValueError, match="required"):
            enforce(None)

    def test_string_year_raises_value_error(self):
        with pytest.raises(ValueError, match="must be int"):
            enforce("2022")  # type: ignore

    def test_float_year_raises_value_error(self):
        with pytest.raises(ValueError, match="must be int"):
            enforce(2022.0)  # type: ignore


class TestIsSellable:
    def test_2022_true(self):
        assert is_sellable(2022) is True

    def test_2021_false(self):
        assert is_sellable(2021) is False


class TestLabelVehicles:
    def test_labels_sellable(self):
        vehicles = [{"year": 2023, "make": "BMW"}]
        result = label_vehicles(vehicles)
        assert result[0]["policy_status"] == "SELLABLE"

    def test_labels_pending(self):
        vehicles = [{"year": 2020, "make": "BMW"}]
        result = label_vehicles(vehicles)
        assert result[0]["policy_status"] == "PENDING_DELISTING"

    def test_mixed_list(self):
        vehicles = [{"year": 2022}, {"year": 2021}, {"year": 2024}]
        result = label_vehicles(vehicles)
        statuses = [v["policy_status"] for v in result]
        assert statuses == ["SELLABLE", "PENDING_DELISTING", "SELLABLE"]

    def test_missing_year_defaults_to_pending(self):
        vehicles = [{"make": "Unknown"}]
        result = label_vehicles(vehicles)
        assert result[0]["policy_status"] == "PENDING_DELISTING"

    def test_empty_list(self):
        assert label_vehicles([]) == []
