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
    racing_type: str | None = None,
) -> tuple[str, list[int]]:
    """
    Build the agg CTE. When *cust_ids* is set, aggregate only those drivers
    (much faster for Live Mode than scanning all race_results).
    When *racing_type* is set, only races in that bucket are counted.
    """
    if cust_ids is not None and not cust_ids:
        return "agg AS (SELECT NULL AS cust_id WHERE 0)", []

    filters: list[str] = []
    params: list[object] = []
    if cust_ids is not None:
        placeholders = ",".join("?" * len(cust_ids))
        filters.append(f"cust_id IN ({placeholders})")
        params.extend(cust_ids)
    if racing_type:
        filters.append("racing_type = ?")
        params.append(racing_type)

    where_sql = f" WHERE {' AND '.join(filters)}" if filters else ""

    if cust_ids is None and not racing_type:
        body = f"""
            agg AS (
                SELECT {_RACE_AGG_SELECT}
                FROM race_results
                GROUP BY cust_id
            )
        """
        return body.strip(), []

    body = f"""
        agg AS (
            SELECT {_RACE_AGG_SELECT}
            FROM race_results
            {where_sql}
            GROUP BY cust_id
        )
    """
    return body.strip(), params


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


def table_data_sql(*, racing_type: str | None = None) -> tuple[str, list[str]]:
    agg_cte, params = _race_agg_cte(racing_type=racing_type)
    sql = f"""
        WITH {agg_cte}
        {_table_select_body().strip()}
        ORDER BY d.driver_name ASC
    """
    return sql.strip(), params


def driver_detail_query(
    cust_id: int,
    *,
    racing_type: str | None = None,
) -> tuple[str, list[object]]:
    agg_filters = ["cust_id = ?"]
    params: list[object] = [int(cust_id)]
    if racing_type:
        agg_filters.append("racing_type = ?")
        params.append(racing_type)
    agg_where = " AND ".join(agg_filters)
    sql = f"""
        WITH agg AS (
            SELECT {_RACE_AGG_SELECT}
            FROM race_results
            WHERE {agg_where}
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
    params.append(int(cust_id))
    return sql.strip(), params


def driver_detail_sql() -> str:
    """Backward-compatible SQL for callers that only need the statement."""
    sql, _params = driver_detail_query(0)
    return sql


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


def table_data_for_cust_ids_by_racing_type_sql(
    cust_ids: list[int],
    racing_type: str,
) -> tuple[str, list[int]]:
    if not cust_ids or not racing_type:
        return ("SELECT NULL LIMIT 0", [])
    agg_cte, agg_params = _race_agg_cte(cust_ids=cust_ids, racing_type=racing_type)
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


_H2H_OUTCOME_EXPR = """
    CASE
        WHEN COALESCE(rr_me.reason_out_id, 0) IN (1, 2, 3, 4)
             AND COALESCE(rr_other.reason_out_id, 0) NOT IN (1, 2, 3, 4)
            THEN 0
        WHEN COALESCE(rr_other.reason_out_id, 0) IN (1, 2, 3, 4)
             AND COALESCE(rr_me.reason_out_id, 0) NOT IN (1, 2, 3, 4)
            THEN 1
        WHEN rr_me.finish_position IS NOT NULL
             AND rr_other.finish_position IS NOT NULL
             AND rr_me.finish_position < rr_other.finish_position
            THEN 1
        WHEN rr_me.finish_position IS NOT NULL
             AND rr_other.finish_position IS NOT NULL
             AND rr_me.finish_position > rr_other.finish_position
            THEN 0
        ELSE 2
    END
"""


def fetch_head_to_head_records(
    conn: sqlite3.Connection,
    player_cust_id: int,
    other_cust_ids: list[int],
) -> dict[int, tuple[int, int, int]]:
    """
    Win-loss-tie record for *player_cust_id* vs each other driver.

    Counts only subsessions where both drivers appear in race_results.
    Outcome uses finish position with DNF handling (reason_out_id 1–4).
    """
    player_id = int(player_cust_id)
    ids = sorted({int(c) for c in other_cust_ids if int(c) != player_id})
    if not ids:
        return {}

    records: dict[int, tuple[int, int, int]] = {}
    for chunk in _chunked_ints(ids, _IN_CLAUSE_CHUNK_SIZE):
        placeholders = ",".join("?" * len(chunk))
        sql = f"""
            SELECT
                shared.cust_id,
                SUM(CASE WHEN shared.outcome = 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN shared.outcome = 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN shared.outcome = 2 THEN 1 ELSE 0 END)
            FROM (
                SELECT
                    rr_other.cust_id AS cust_id,
                    {_H2H_OUTCOME_EXPR} AS outcome
                FROM race_results rr_other
                INNER JOIN race_results rr_me
                    ON rr_me.subsession_id = rr_other.subsession_id
                   AND rr_me.cust_id = ?
                WHERE rr_other.cust_id IN ({placeholders})
                  AND rr_other.subsession_id IS NOT NULL
                  AND rr_other.subsession_id != 0
            ) AS shared
            GROUP BY shared.cust_id
        """
        rows = conn.execute(sql, [player_id, *chunk]).fetchall()
        for cust_id, wins, losses, ties in rows:
            records[int(cust_id)] = (int(wins), int(losses), int(ties))
    return records


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
