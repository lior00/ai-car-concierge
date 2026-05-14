"""
Policy enforcement layer.
Pure function — no DB access, no LLM calls, fully deterministic.
Called by the orchestrator after every SQL tool result.
"""
from enum import Enum
from backend.config import MINIMUM_SALE_YEAR, PENDING_DELISTING_LABEL


class PolicyResult(str, Enum):
    SELLABLE = "SELLABLE"
    PENDING_DELISTING = "PENDING_DELISTING"


def enforce(vehicle_year: int | None) -> PolicyResult:
    """
    Evaluate whether a vehicle is eligible for sale.

    Args:
        vehicle_year: The model year from the inventory record.

    Returns:
        PolicyResult.SELLABLE if year >= MINIMUM_SALE_YEAR (2022).
        PolicyResult.PENDING_DELISTING otherwise.

    Raises:
        ValueError: If vehicle_year is None or not an integer.
    """
    if vehicle_year is None:
        raise ValueError("vehicle_year is required for policy check")
    if not isinstance(vehicle_year, int):
        raise ValueError(f"vehicle_year must be int, got {type(vehicle_year)}")

    if vehicle_year >= MINIMUM_SALE_YEAR:
        return PolicyResult.SELLABLE
    return PolicyResult.PENDING_DELISTING


def is_sellable(vehicle_year: int | None) -> bool:
    """Convenience wrapper returning a bool."""
    return enforce(vehicle_year) == PolicyResult.SELLABLE


def label_vehicles(vehicles: list[dict]) -> list[dict]:
    """
    Add a 'policy_status' field to each vehicle dict in-place.
    Vehicles with PENDING_DELISTING are not removed — callers decide display logic.
    """
    for v in vehicles:
        year = v.get("year")
        try:
            v["policy_status"] = enforce(year).value
        except ValueError:
            v["policy_status"] = PolicyResult.PENDING_DELISTING.value
    return vehicles
