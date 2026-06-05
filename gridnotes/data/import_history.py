"""Queries for imported iRacing session history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

IMPORT_HISTORY_LIMIT = 500

_IMPORT_HISTORY_SQL = """
SELECT
    subsession_id,
    COALESCE(NULLIF(TRIM(MAX(series_name)), ''), 'Unknown session') AS session_name,
    MAX(race_at) AS race_at,
    COUNT(DISTINCT cust_id) AS driver_count
FROM race_results
WHERE subsession_id IS NOT NULL
  AND subsession_id != 0
{session_id_filter}
GROUP BY subsession_id
ORDER BY
    CASE WHEN MAX(race_at) IS NULL OR TRIM(MAX(race_at)) = '' THEN 1 ELSE 0 END,
    MAX(race_at) DESC,
    subsession_id DESC
LIMIT ?
"""


def _session_id_filter_sql(session_id_query: str | None) -> tuple[str, list[str]]:
    query = (session_id_query or "").strip()
    if not query:
        return "", []
    return " AND CAST(subsession_id AS TEXT) LIKE ?", [f"%{query}%"]


@dataclass(frozen=True)
class ImportHistoryEntry:
    subsession_id: int
    session_name: str
    race_at: str | None
    driver_count: int


def fetch_import_history(
    conn: sqlite3.Connection,
    *,
    limit: int = IMPORT_HISTORY_LIMIT,
    session_id_query: str | None = None,
) -> list[ImportHistoryEntry]:
    """Distinct imported subsessions, newest first."""
    if limit <= 0:
        return []
    filter_sql, filter_params = _session_id_filter_sql(session_id_query)
    sql = _IMPORT_HISTORY_SQL.format(session_id_filter=filter_sql)
    rows = conn.execute(sql, (*filter_params, limit)).fetchall()
    return [
        ImportHistoryEntry(
            subsession_id=int(row[0]),
            session_name=str(row[1] or "Unknown session"),
            race_at=row[2],
            driver_count=int(row[3] or 0),
        )
        for row in rows
    ]


def count_imported_sessions(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT subsession_id)
        FROM race_results
        WHERE subsession_id IS NOT NULL
          AND subsession_id != 0
        """
    ).fetchone()
    return int(row[0] or 0) if row else 0
