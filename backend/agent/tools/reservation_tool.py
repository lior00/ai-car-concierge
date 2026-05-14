"""
Reservation automation tool.
Decrements stock_count in SQLite when a user reserves a vehicle.
Validates: vehicle exists, year >= 2022 (policy), stock > 0.
"""
import logging

from backend.db.session import get_db
from backend.agent.tools.policy_guard import enforce, PolicyResult

logger = logging.getLogger(__name__)


def reserve_vehicle(vehicle_id: int) -> dict:
    """
    Reserve a vehicle by decrementing its stock_count.

    Returns:
        {
            "success": bool,
            "vehicle": dict | None,   # updated vehicle row
            "new_stock": int | None,
            "error": str | None,
        }
    """
    with get_db() as conn:
        # Fetch vehicle first
        cursor = conn.execute(
            "SELECT id, make, model, year, trim, color, price, stock_count FROM inventory WHERE id = ?",
            (vehicle_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return {"success": False, "vehicle": None, "new_stock": None,
                    "error": f"No vehicle found with ID {vehicle_id}."}

        vehicle = dict(row)

        # Policy check — enforce before any write
        policy = enforce(vehicle["year"])
        if policy == PolicyResult.PENDING_DELISTING:
            return {
                "success": False,
                "vehicle": vehicle,
                "new_stock": None,
                "error": (
                    f"Cannot reserve the {vehicle['year']} {vehicle['make']} {vehicle['model']} — "
                    "it is Pending De-listing per the 2022+ Sales Policy."
                ),
            }

        # Stock check
        if vehicle["stock_count"] <= 0:
            return {
                "success": False,
                "vehicle": vehicle,
                "new_stock": 0,
                "error": f"The {vehicle['year']} {vehicle['make']} {vehicle['model']} is currently sold out.",
            }

        # Atomic decrement
        conn.execute(
            "UPDATE inventory SET stock_count = stock_count - 1 WHERE id = ? AND stock_count > 0",
            (vehicle_id,),
        )
        conn.commit()

        # Fetch updated stock
        updated = conn.execute(
            "SELECT stock_count FROM inventory WHERE id = ?", (vehicle_id,)
        ).fetchone()
        new_stock = updated["stock_count"] if updated else 0

        logger.info(
            f"Vehicle #{vehicle_id} ({vehicle['year']} {vehicle['make']} {vehicle['model']}) "
            f"reserved. Stock: {vehicle['stock_count']} → {new_stock}"
        )

        vehicle["stock_count"] = new_stock
        return {"success": True, "vehicle": vehicle, "new_stock": new_stock, "error": None}
