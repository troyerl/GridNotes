"""SQL queries for driver stats and details."""

from __future__ import annotations

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

_LAST_SEEN_EXPR = """
    COALESCE(
        NULLIF(TRIM(d.last_seen_at), ''),
        (
            SELECT MAX(r.race_at)
            FROM race_results r
            WHERE r.cust_id = d.cust_id
              AND r.race_at IS NOT NULL
              AND TRIM(r.race_at) != ''
        )
    )
"""


def table_data_sql() -> str:
    return f"""
        WITH agg AS (
            SELECT {_RACE_AGG_SELECT}
            FROM race_results
            GROUP BY cust_id
        )
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
        ORDER BY d.driver_name ASC
    """


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
