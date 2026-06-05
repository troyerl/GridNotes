"""Queries for imported iRacing session history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

_IMPORT_HISTORY_SQL = """
SELECT
    rr.subsession_id,
    COALESCE(NULLIF(TRIM(MAX(rr.series_name)), ''), 'Unknown session') AS session_name,
    MAX(rr.race_at) AS race_at,
    COUNT(DISTINCT rr.cust_id) AS driver_count,
    MAX(lrs.league_id) AS league_id,
    MAX(l.name) AS league_name,
    MAX(ls.name) AS season_name
FROM race_results rr
LEFT JOIN league_race_sessions lrs ON lrs.subsession_id = rr.subsession_id
LEFT JOIN leagues l ON l.id = lrs.league_id
LEFT JOIN league_seasons ls ON ls.id = lrs.season_id
WHERE rr.subsession_id IS NOT NULL
  AND rr.subsession_id != 0
{session_id_filter}
GROUP BY rr.subsession_id
ORDER BY
    CASE WHEN MAX(rr.race_at) IS NULL OR TRIM(MAX(rr.race_at)) = '' THEN 1 ELSE 0 END,
    MAX(rr.race_at) DESC,
    rr.subsession_id DESC
LIMIT ? OFFSET ?
"""


def _session_id_filter_sql(
    session_id_query: str | None,
    *,
    column: str = "subsession_id",
) -> tuple[str, list[str]]:
    query = (session_id_query or "").strip()
    if not query:
        return "", []
    return f" AND CAST({column} AS TEXT) LIKE ?", [f"%{query}%"]


def _import_history_where(session_id_query: str | None) -> tuple[str, list[str]]:
    filter_sql, filter_params = _session_id_filter_sql(session_id_query)
    return (
        "WHERE subsession_id IS NOT NULL AND subsession_id != 0" + filter_sql,
        filter_params,
    )


@dataclass(frozen=True)
class ImportHistoryEntry:
    subsession_id: int
    session_name: str
    race_at: str | None
    driver_count: int
    league_id: int | None = None
    league_name: str | None = None
    season_name: str | None = None


def fetch_import_history(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
    session_id_query: str | None = None,
) -> list[ImportHistoryEntry]:
    """Distinct imported subsessions, newest first."""
    if limit <= 0:
        return []
    if offset < 0:
        offset = 0
    filter_sql, filter_params = _session_id_filter_sql(
        session_id_query,
        column="rr.subsession_id",
    )
    sql = _IMPORT_HISTORY_SQL.format(session_id_filter=filter_sql)
    rows = conn.execute(sql, (*filter_params, limit, offset)).fetchall()
    return [
        ImportHistoryEntry(
            subsession_id=int(row[0]),
            session_name=str(row[1] or "Unknown session"),
            race_at=row[2],
            driver_count=int(row[3] or 0),
            league_id=int(row[4]) if row[4] is not None else None,
            league_name=str(row[5]) if row[5] is not None else None,
            season_name=str(row[6]) if row[6] is not None else None,
        )
        for row in rows
    ]


def count_import_history(
    conn: sqlite3.Connection,
    *,
    session_id_query: str | None = None,
) -> int:
    where_sql, params = _import_history_where(session_id_query)
    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT subsession_id
            FROM race_results
            {where_sql}
            GROUP BY subsession_id
        )
        """,
        params,
    ).fetchone()
    return int(row[0] or 0) if row else 0


def count_imported_sessions(conn: sqlite3.Connection) -> int:
    return count_import_history(conn)
