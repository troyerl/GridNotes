"""Data retention settings and purge logic for race history."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

SETTING_KEY = "data_retention_days"
DEFAULT_RETENTION = "never"

# (stored value, display label)
RETENTION_OPTIONS: tuple[tuple[str, str], ...] = (
    ("never", "Never delete"),
    ("90", "3 months"),
    ("180", "6 months"),
    ("365", "1 year"),
    ("730", "2 years"),
    ("1095", "3 years"),
    ("1825", "5 years"),
)


def retention_label(value: str | None) -> str:
    for stored, label in RETENTION_OPTIONS:
        if stored == (value or DEFAULT_RETENTION):
            return label
    return RETENTION_OPTIONS[0][1]


def retention_cutoff_iso(retention_days: str) -> str | None:
    if not retention_days or retention_days == "never":
        return None
    try:
        days = int(retention_days)
    except ValueError:
        return None
    if days <= 0:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.isoformat()


def purge_expired_race_results(conn: sqlite3.Connection, retention_days: str) -> int:
    """
    Delete race_results older than the retention window.
    Rows with NULL race_at are kept (unknown import date).
    Returns number of rows deleted.
    """
    cutoff = retention_cutoff_iso(retention_days)
    if cutoff is None:
        return 0

    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM race_results
        WHERE race_at IS NOT NULL
          AND race_at < ?
        """,
        (cutoff,),
    )
    deleted = cursor.rowcount
    if deleted:
        _refresh_driver_last_seen(cursor)
        logger.info(
            "Data retention (%s): removed %s race result(s) before %s",
            retention_label(retention_days),
            deleted,
            cutoff,
        )
    return deleted


def _refresh_driver_last_seen(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        UPDATE drivers
        SET last_seen_at = (
            SELECT MAX(r.race_at)
            FROM race_results r
            WHERE r.cust_id = drivers.cust_id
              AND r.race_at IS NOT NULL
        )
        WHERE EXISTS (
            SELECT 1 FROM race_results r WHERE r.cust_id = drivers.cust_id
        )
        """
    )
    cursor.execute(
        """
        UPDATE drivers
        SET last_seen_at = NULL
        WHERE NOT EXISTS (
            SELECT 1 FROM race_results r WHERE r.cust_id = drivers.cust_id
        )
        """
    )
