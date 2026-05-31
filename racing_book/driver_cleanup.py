"""Remove drivers that have no imported race results."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def count_zero_race_drivers(conn: sqlite3.Connection) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM drivers d
        WHERE NOT EXISTS (
            SELECT 1 FROM race_results r WHERE r.cust_id = d.cust_id
        )
        """
    )
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def purge_zero_race_drivers(conn: sqlite3.Connection) -> int:
    """Delete drivers with no race_results rows. Returns drivers removed."""
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM drivers
        WHERE cust_id NOT IN (
            SELECT DISTINCT cust_id FROM race_results WHERE cust_id IS NOT NULL
        )
        """
    )
    deleted = cursor.rowcount
    if deleted:
        logger.info("Removed %s driver(s) with zero races", deleted)
    return deleted
