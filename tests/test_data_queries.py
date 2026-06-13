"""Tests for gridnotes.data.queries and driver_cleanup."""

from gridnotes.data.driver_cleanup import count_zero_race_drivers, purge_zero_race_drivers
from gridnotes.data.queries import (
    _chunked_ints,
    driver_detail_sql,
    fetch_head_to_head_records,
    fetch_recent_races_by_cust_ids,
    fetch_shared_race_counts,
    table_data_for_cust_ids_by_racing_type_sql,
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
    sql, params = table_data_sql()
    rows = memory_conn.execute(sql, params).fetchall()
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


def test_table_data_sql_filters_by_racing_type(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'A'), (2, 'B')"
    )
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents, racing_type
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, 1, 3, 2, "oval"),
            (1, 2, 5, 8, "road"),
            (2, 3, 2, 1, "road"),
        ],
    )
    memory_conn.commit()
    sql, params = table_data_sql(racing_type="road")
    rows = memory_conn.execute(sql, params).fetchall()
    by_id = {int(row[8]): row for row in rows}
    assert int(by_id[1][3]) == 1
    assert int(by_id[2][3]) == 1


def test_table_racing_type_filter_excludes_zero_race_drivers(memory_conn):
    """Drivers tab hides rows with no races in the selected type."""
    from gridnotes.data.driver_models import DriverTableRow

    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'Oval only'), (2, 'Road only')"
    )
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents, racing_type
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, 1, 3, 2, "oval"),
            (2, 2, 5, 4, "road"),
        ],
    )
    memory_conn.commit()
    sql, params = table_data_sql(racing_type="oval")
    rows = memory_conn.execute(sql, params).fetchall()
    visible = [
        row
        for row in rows
        if DriverTableRow.from_sql_row(row).total_races > 0
    ]
    assert len(visible) == 1
    assert DriverTableRow.from_sql_row(visible[0]).cust_id == 1


def test_driver_detail_query_filters_by_racing_type(memory_conn):
    from gridnotes.data.queries import driver_detail_query

    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (7, 'Dan')"
    )
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents, racing_type
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (7, 1, 3, 2, "oval"),
            (7, 2, 5, 8, "oval"),
            (7, 3, 2, 1, "dirt"),
        ],
    )
    memory_conn.commit()
    sql, params = driver_detail_query(7, racing_type="dirt")
    row = memory_conn.execute(sql, params).fetchone()
    assert row is not None
    assert int(row[5]) == 1


def test_table_data_for_cust_ids_by_racing_type(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'A')"
    )
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents, racing_type
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, 1, 3, 2, "oval"),
            (1, 2, 5, 8, "road"),
            (1, 3, 2, 1, "oval"),
        ],
    )
    memory_conn.commit()
    sql, params = table_data_for_cust_ids_by_racing_type_sql([1], "oval")
    row = memory_conn.execute(sql, params).fetchone()
    assert row is not None
    assert int(row[3]) == 2  # total_races
    assert float(row[1]) == 1.5  # avg_inc


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


def test_fetch_head_to_head_records(memory_conn):
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, reason_out_id, incidents
        )
        VALUES (?, ?, ?, ?, 0)
        """,
        [
            (100, 1, 1, 0),
            (200, 1, 3, 0),
            (100, 2, 4, 0),
            (200, 2, 2, 0),
            (100, 3, 2, 0),
            (200, 3, 5, 0),
        ],
    )
    memory_conn.commit()
    records = fetch_head_to_head_records(memory_conn, 100, [200])
    assert records[200] == (2, 1, 0)


def test_fetch_shared_race_counts(memory_conn):
    memory_conn.executemany(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (?, ?, 1, 0)
        """,
        [
            (100, 1),
            (200, 1),
            (100, 2),
            (300, 2),
            (100, 3),
            (200, 3),
        ],
    )
    memory_conn.commit()
    counts = fetch_shared_race_counts(memory_conn, 100, [200, 300, 400])
    assert counts[200] == 2
    assert counts[300] == 1
    assert 400 not in counts
