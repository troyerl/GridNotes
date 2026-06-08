"""SQL queries for driver stats and details."""

from __future__ import annotations

import sqlite3

# Stay below SQLite's default max bound variables (999).
_IN_CLAUSE_CHUNK_SIZE = 400

_RACE_AGG_SELECT = """
    cust_id,
    COUNT(id) AS total_races,
    ROUND(AVG(incidents), 1) AS avg_inc,
    ROUND(AVG(finish_position), 1) AS avg_fin,
    ROUND(
        AVG(
            CASE
                WHEN starting_position IS NOT NULL AND finish_position IS NOT NULL
                THEN (starting_position - finish_position)
            END
        ),
        1
    ) AS avg_pos_delta,
    SUM(CASE WHEN reason_out_id IN (1, 2, 3, 4) THEN 1 ELSE 0 END) AS dnf_total,
    SUM(CASE WHEN reason_out_id = 1 THEN 1 ELSE 0 END) AS disc,
    SUM(CASE WHEN reason_out_id = 2 THEN 1 ELSE 0 END) AS eject,
    SUM(CASE WHEN reason_out_id = 3 THEN 1 ELSE 0 END) AS quit_,
    SUM(CASE WHEN reason_out_id = 4 THEN 1 ELSE 0 END) AS dq,
    SUM(
        CASE
            WHEN reason_out_id IS NOT NULL AND reason_out_id NOT IN (0, 1, 2, 3, 4)
            THEN 1
            ELSE 0
        END
    ) AS other
"""

_DNF_COALESCE = """
    COALESCE(a.dnf_total, 0),
    COALESCE(a.disc, 0),
    COALESCE(a.eject, 0),
    COALESCE(a.quit_, 0),
    COALESCE(a.dq, 0),
    COALESCE(a.other, 0)
"""

# last_seen_at is maintained on import; avoid per-row race_results subqueries.
_LAST_SEEN_EXPR = "NULLIF(TRIM(d.last_seen_at), '')"

_RECENT_RACE_ORDER = """
    CASE WHEN race_at IS NULL OR TRIM(race_at) = '' THEN 1 ELSE 0 END,
    race_at DESC,
    id DESC
"""


def _chunked_ints(values: list[int], size: int) -> list[list[int]]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    return [values[i : i + size] for i in range(0, len(values), size)]


def _race_agg_cte(
    *,
    cust_ids: list[int] | None = None,
) -> tuple[str, list[int]]:
    """
    Build the agg CTE. When *cust_ids* is set, aggregate only those drivers
    (much faster for Live Mode than scanning all race_results).
    """
    if cust_ids is not None and not cust_ids:
        return "agg AS (SELECT NULL AS cust_id WHERE 0)", []

    if cust_ids is None:
        body = f"""
            agg AS (
                SELECT {_RACE_AGG_SELECT}
                FROM race_results
                GROUP BY cust_id
            )
        """
        return body.strip(), []

    placeholders = ",".join("?" * len(cust_ids))
    body = f"""
        agg AS (
            SELECT {_RACE_AGG_SELECT}
            FROM race_results
            WHERE cust_id IN ({placeholders})
            GROUP BY cust_id
        )
    """
    return body.strip(), list(cust_ids)


def _table_select_body() -> str:
    return f"""
        SELECT
            d.driver_name,
            a.avg_inc,
            a.avg_fin,
            COALESCE(a.total_races, 0) AS total_races,
            d.last_irating,
            d.last_safety,
            d.last_series,
            a.avg_pos_delta,
            d.cust_id,
            d.race_preference,
            {_DNF_COALESCE},
            CASE WHEN TRIM(COALESCE(d.notes, '')) != '' THEN 1 ELSE 0 END AS has_notes
        FROM drivers d
        LEFT JOIN agg a ON d.cust_id = a.cust_id
    """


def table_data_sql() -> str:
    agg_cte, _ = _race_agg_cte()
    return f"""
        WITH {agg_cte}
        {_table_select_body().strip()}
        ORDER BY d.driver_name ASC
    """


def table_data_for_cust_ids_sql(cust_ids: list[int]) -> tuple[str, list[int]]:
    if not cust_ids:
        return ("SELECT NULL LIMIT 0", [])
    agg_cte, agg_params = _race_agg_cte(cust_ids=cust_ids)
    placeholders = ",".join("?" * len(cust_ids))
    sql = f"""
        WITH {agg_cte}
        {_table_select_body().strip()}
        WHERE d.cust_id IN ({placeholders})
        ORDER BY d.driver_name ASC
    """
    return sql, [*agg_params, *cust_ids]


def _fetch_recent_races_chunk(
    conn: sqlite3.Connection,
    cust_ids: list[int],
    *,
    limit: int,
    into: dict[int, list[tuple]],
) -> None:
    placeholders = ",".join("?" * len(cust_ids))
    sql = f"""
        WITH ranked AS (
            SELECT
                cust_id,
                incidents,
                finish_position,
                starting_position,
                reason_out_id,
                ROW_NUMBER() OVER (
                    PARTITION BY cust_id
                    ORDER BY {_RECENT_RACE_ORDER}
                ) AS rn
            FROM race_results
            WHERE cust_id IN ({placeholders})
        )
        SELECT
            cust_id,
            incidents,
            finish_position,
            starting_position,
            reason_out_id
        FROM ranked
        WHERE rn <= ?
        ORDER BY cust_id ASC, rn ASC
    """
    cursor = conn.cursor()
    cursor.execute(sql, [*cust_ids, limit])
    for cust_id, incidents, finish, start, reason_out in cursor.fetchall():
        into[int(cust_id)].append((incidents, finish, start, reason_out))


def fetch_recent_races_by_cust_ids(
    conn: sqlite3.Connection,
    cust_ids: list[int],
    *,
    limit: int = 5,
) -> dict[int, list[tuple]]:
    """
    Last *limit* race results per driver (newest first).

    Each value is a list of
    (incidents, finish_position, starting_position, reason_out_id).
    """
    if not cust_ids or limit <= 0:
        return {}

    unique_ids = list(dict.fromkeys(int(cid) for cid in cust_ids))
    by_cust: dict[int, list[tuple]] = {cid: [] for cid in unique_ids}

    for chunk in _chunked_ints(unique_ids, _IN_CLAUSE_CHUNK_SIZE):
        _fetch_recent_races_chunk(conn, chunk, limit=limit, into=by_cust)

    return by_cust


def driver_detail_sql() -> str:
    return f"""
        WITH agg AS (
            SELECT {_RACE_AGG_SELECT}
            FROM race_results
            WHERE cust_id = ?
            GROUP BY cust_id
        )
        SELECT
            d.driver_name,
            {_LAST_SEEN_EXPR} AS last_seen_at,
            d.last_series,
            a.avg_inc,
            a.avg_fin,
            COALESCE(a.total_races, 0) AS total_races,
            d.last_irating,
            d.last_safety,
            a.avg_pos_delta,
            {_DNF_COALESCE}
        FROM drivers d
        LEFT JOIN agg a ON d.cust_id = a.cust_id
        WHERE d.cust_id = ?
    """


def fetch_shared_race_counts(
    conn: sqlite3.Connection,
    player_cust_id: int,
    other_cust_ids: list[int],
) -> dict[int, int]:
    """
    Count subsessions where *player_cust_id* and each other driver both appear.

    Uses imported race_results rows with a non-zero subsession_id.
    """
    player_id = int(player_cust_id)
    ids = sorted({int(c) for c in other_cust_ids if int(c) != player_id})
    if not ids:
        return {}

    counts: dict[int, int] = {}
    for chunk in _chunked_ints(ids, _IN_CLAUSE_CHUNK_SIZE):
        placeholders = ",".join("?" * len(chunk))
        sql = f"""
            SELECT rr_other.cust_id, COUNT(DISTINCT rr_other.subsession_id)
            FROM race_results rr_other
            INNER JOIN race_results rr_me
                ON rr_me.subsession_id = rr_other.subsession_id
               AND rr_me.cust_id = ?
            WHERE rr_other.cust_id IN ({placeholders})
              AND rr_other.subsession_id IS NOT NULL
              AND rr_other.subsession_id != 0
            GROUP BY rr_other.cust_id
        """
        rows = conn.execute(sql, [player_id, *chunk]).fetchall()
        for cust_id, count in rows:
            counts[int(cust_id)] = int(count)
    return counts
