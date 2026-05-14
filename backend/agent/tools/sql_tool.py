"""
Text-to-SQL tool: converts natural language to a safe SELECT query,
executes it against SQLite, and returns vehicle rows as dicts.
Read-only: only SELECT statements are permitted.
"""
import logging
import re
import sqlite3

import anthropic

from backend.config import ANTHROPIC_API_KEY, LLM_MODEL
from backend.db.session import get_db
from backend.agent.tools.policy_guard import label_vehicles

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_SCHEMA = """
Table: inventory
Columns: id (INTEGER), make (TEXT), model (TEXT), year (INTEGER), trim (TEXT),
color (TEXT), fuel_type (TEXT: 'Electric'|'Gasoline'|'Hybrid'),
transmission (TEXT), mileage (INTEGER), price (REAL),
stock_count (INTEGER), vin (TEXT), description (TEXT)
"""

_SQL_SYSTEM = f"""You are a SQL generator for a SQLite database.
Schema:
{_SCHEMA}

Rules:
- Output ONLY a valid SQLite SELECT statement — nothing else.
- No markdown, no explanation, no code fences.
- NEVER use DELETE, UPDATE, DROP, INSERT, or any DDL.
- Use LOWER() for case-insensitive string comparisons.
- Always include a LIMIT clause (default LIMIT 50, unless user asks for fewer).
- If the query cannot be answered from the schema, output exactly: UNSUPPORTED
- IMPORTANT: The inventory contains vehicles with model years 2019 through 2025. Do NOT add any implicit year ceiling. Never filter by year unless the user explicitly requests a year range.
"""

_BLOCKED_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


def _generate_sql(natural_language: str) -> str:
    response = _client.messages.create(
        model=LLM_MODEL,
        max_tokens=256,
        system=_SQL_SYSTEM,
        messages=[{"role": "user", "content": natural_language}],
    )
    return response.content[0].text.strip()


def _validate_sql(sql: str) -> str:
    if _BLOCKED_PATTERN.search(sql):
        raise ValueError(f"Blocked SQL operation detected: {sql[:80]}")
    if not sql.upper().startswith("SELECT"):
        raise ValueError(f"Only SELECT statements allowed. Got: {sql[:80]}")
    return sql


def query_inventory(natural_language: str) -> dict:
    """
    Convert natural language to SQL, execute, and return results.

    Returns:
        {
            "vehicles": [...],  # list of row dicts with policy_status added
            "sql": "...",       # generated SQL (for debugging)
            "count": int,
        }
    """
    sql = _generate_sql(natural_language)

    if sql == "UNSUPPORTED":
        return {"vehicles": [], "sql": None, "count": 0, "unsupported": True}

    try:
        sql = _validate_sql(sql)
    except ValueError as e:
        logger.warning(f"SQL validation failed: {e}")
        return {"vehicles": [], "sql": sql, "count": 0, "error": str(e)}

    try:
        with get_db() as conn:
            cursor = conn.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"SQL execution error: {e} | SQL: {sql}")
        return {"vehicles": [], "sql": sql, "count": 0, "error": str(e)}

    vehicles = label_vehicles(rows)
    return {"vehicles": vehicles, "sql": sql, "count": len(vehicles)}
