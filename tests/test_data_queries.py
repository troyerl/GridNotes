"""Tests for gridnotes.data.queries and driver_cleanup."""

from gridnotes.data.driver_cleanup import count_zero_race_drivers, purge_zero_race_drivers
from gridnotes.data.queries import (
    _chunked_ints,
    driver_detail_sql,
    fetch_recent_races_by_cust_ids,
    table_data_for_cust_ids_sql,
    table_data_sql,
)


def test_chunked_ints():
    assert _chunked_ints([], 10) == []
    assert _chunked_ints([1, 2, 3], 2) == [[1, 2], [3]]


def test_table_data_sql_returns_rows(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (?, ?)", (5, "Eve")
    )
    memory_conn.execute(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (5, 100, 1, 2)
        """,
    )
    memory_conn.commit()
    sql = table_data_sql()
    rows = memory_conn.execute(sql).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Eve"


def test_table_data_for_cust_ids(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'A'), (2, 'B')"
    )
    memory_conn.commit()
    sql, params = table_data_for_cust_ids_sql([1])
    rows = memory_conn.execute(sql, params).fetchall()
    assert len(rows) == 1


def test_fetch_recent_races(memory_conn):
    memory_conn.executemany(
        """
        INSERT INTO race_results (cust_id, subsession_id, incidents, finish_position, race_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, 1, 2, 5, "2026-01-01T00:00:00+00:00"),
            (1, 2, 4, 8, "2026-02-01T00:00:00+00:00"),
        ],
    )
    memory_conn.commit()
    by_cust = fetch_recent_races_by_cust_ids(memory_conn, [1], limit=5)
    assert len(by_cust[1]) == 2


def test_driver_detail_sql(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name, notes) VALUES (7, 'Dan', 'Note')"
    )
    memory_conn.commit()
    sql = driver_detail_sql()
    row = memory_conn.execute(sql, (7, 7)).fetchone()
    assert row is not None


def test_purge_zero_race_drivers(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'Ghost'), (2, 'Active')"
    )
    memory_conn.execute(
        "INSERT INTO race_results (cust_id, subsession_id) VALUES (2, 1)"
    )
    memory_conn.commit()
    assert count_zero_race_drivers(memory_conn) == 1
    removed = purge_zero_race_drivers(memory_conn)
    assert removed == 1
    assert memory_conn.execute("SELECT COUNT(*) FROM drivers").fetchone()[0] == 1
