"""Per-driver race history queries."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .queries import _chunked_ints, _IN_CLAUSE_CHUNK_SIZE

_RACE_HISTORY_ORDER = """
    CASE WHEN rr.race_at IS NULL OR TRIM(rr.race_at) = '' THEN 1 ELSE 0 END,
    rr.race_at DESC,
    rr.id DESC
"""

_IMPORTED_RACE_FILTER = """
    rr.subsession_id IS NOT NULL AND rr.subsession_id != 0
"""

_DRIVER_LIST_SQL = f"""
    SELECT d.cust_id, d.driver_name
    FROM drivers d
    WHERE EXISTS (
        SELECT 1
        FROM race_results rr
        WHERE rr.cust_id = d.cust_id
          AND {_IMPORTED_RACE_FILTER}
    )
    ORDER BY d.driver_name COLLATE NOCASE ASC, d.cust_id ASC
"""


@dataclass(frozen=True)
class DriverRaceHistoryEntry:
    subsession_id: int
    series_name: str | None
    race_at: str | None
    starting_position: int | None
    finish_position: int | None
    incidents: int | None
    irating_change: int | None
    reason_out_id: int | None
    player_finish: int | None
    player_reason_out_id: int | None


def fetch_drivers_with_race_history(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """All drivers with at least one imported race, sorted by name."""
    rows = conn.execute(_DRIVER_LIST_SQL).fetchall()
    return [(int(cust_id), str(name or "")) for cust_id, name in rows]


def _history_where_clause(*, series_query: str | None) -> tuple[str, list[object]]:
    clauses = ["rr.cust_id = ?", _IMPORTED_RACE_FILTER]
    params: list[object] = []
    if series_query:
        clauses.append(
            "(CAST(rr.subsession_id AS TEXT) LIKE ? OR COALESCE(rr.series_name, '') LIKE ?)"
        )
        pattern = f"%{series_query}%"
        params.extend([pattern, pattern])
    return " AND ".join(clauses), params


def count_driver_race_history(
    conn: sqlite3.Connection,
    cust_id: int,
    *,
    series_query: str | None = None,
) -> int:
    where_sql, extra_params = _history_where_clause(series_query=series_query)
    sql = f"""
        SELECT COUNT(*)
        FROM race_results rr
        WHERE {where_sql}
    """
    row = conn.execute(sql, [int(cust_id), *extra_params]).fetchone()
    return int(row[0] if row else 0)


def fetch_driver_race_history(
    conn: sqlite3.Connection,
    cust_id: int,
    *,
    player_cust_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    series_query: str | None = None,
) -> list[DriverRaceHistoryEntry]:
    """Paginated race list for one driver, newest first."""
    if limit <= 0:
        return []

    where_sql, extra_params = _history_where_clause(series_query=series_query)
    player_join = ""
    player_select = "NULL AS player_finish, NULL AS player_reason_out_id"
    params: list[object] = []
    if player_cust_id is not None:
        player_join = """
            LEFT JOIN race_results rr_me
                ON rr_me.subsession_id = rr.subsession_id
               AND rr_me.cust_id = ?
        """
        player_select = "rr_me.finish_position, rr_me.reason_out_id"
        params.append(int(player_cust_id))
    params.append(int(cust_id))
    params.extend(extra_params)

    sql = f"""
        SELECT
            rr.subsession_id,
            rr.series_name,
            rr.race_at,
            rr.starting_position,
            rr.finish_position,
            rr.incidents,
            rr.irating_change,
            rr.reason_out_id,
            {player_select}
        FROM race_results rr
        {player_join}
        WHERE {where_sql}
        ORDER BY {_RACE_HISTORY_ORDER}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, max(0, offset)])
    rows = conn.execute(sql, params).fetchall()
    return [
        DriverRaceHistoryEntry(
            subsession_id=int(subsession_id or 0),
            series_name=series_name,
            race_at=race_at,
            starting_position=starting_position,
            finish_position=finish_position,
            incidents=incidents,
            irating_change=irating_change,
            reason_out_id=reason_out_id,
            player_finish=player_finish,
            player_reason_out_id=player_reason_out_id,
        )
        for (
            subsession_id,
            series_name,
            race_at,
            starting_position,
            finish_position,
            incidents,
            irating_change,
            reason_out_id,
            player_finish,
            player_reason_out_id,
        ) in rows
    ]


def fetch_driver_names_by_cust_ids(
    conn: sqlite3.Connection,
    cust_ids: list[int],
) -> dict[int, str]:
    if not cust_ids:
        return {}
    names: dict[int, str] = {}
    unique = list(dict.fromkeys(int(cid) for cid in cust_ids))
    for chunk in _chunked_ints(unique, _IN_CLAUSE_CHUNK_SIZE):
        placeholders = ",".join("?" * len(chunk))
        sql = f"""
            SELECT cust_id, driver_name
            FROM drivers
            WHERE cust_id IN ({placeholders})
        """
        for cust_id, name in conn.execute(sql, chunk).fetchall():
            names[int(cust_id)] = str(name or "")
    return names
