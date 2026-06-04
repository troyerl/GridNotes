"""Apply scouting edits received from broadcast receivers."""

from __future__ import annotations

import sqlite3
from typing import Any


def apply_driver_patch(conn: sqlite3.Connection, patch: dict[str, Any]) -> bool:
    """Update notes and/or race preference for one driver. Returns True if a row changed."""
    cust_id = patch.get("cust_id")
    try:
        cust_id_int = int(cust_id)
    except (TypeError, ValueError):
        return False

    updates: list[str] = []
    params: list[object] = []
    if "notes" in patch:
        updates.append("notes = ?")
        params.append(str(patch.get("notes") or ""))
    if "race_preference" in patch:
        updates.append("race_preference = ?")
        params.append(patch.get("race_preference"))

    if not updates:
        return False

    params.append(cust_id_int)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE drivers SET {', '.join(updates)} WHERE cust_id = ?",
        params,
    )
    return cursor.rowcount > 0
