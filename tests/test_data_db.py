"""Tests for gridnotes.data.db and settings."""

import sqlite3

from gridnotes.data.db import (
    create_memory_database,
    get_setting,
    set_setting,
)


def test_memory_database_has_core_tables(memory_conn):
    tables = {
        row[0]
        for row in memory_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "drivers" in tables
    assert "race_results" in tables
    assert "app_settings" in tables


def test_settings_round_trip(file_db):
    db_path, conn = file_db
    set_setting("test_key", "hello", db_name=db_path)
    assert get_setting("test_key", db_name=db_path) == "hello"
    assert get_setting("missing", "default", db_name=db_path) == "default"
    conn.close()


def test_create_memory_database_isolated():
    a = create_memory_database()
    b = create_memory_database()
    a.execute("INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'A')")
    a.commit()
    count_b = b.execute("SELECT COUNT(*) FROM drivers").fetchone()[0]
    assert count_b == 0
    a.close()
    b.close()


def test_backfill_racing_type_classifies_from_series_name(memory_conn):
    from gridnotes.data.db import _backfill_racing_type

    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'A')"
    )
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents, series_name, racing_type
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1, 1, 3, 2, "NASCAR Cup Series", "dirt"),
            (1, 2, 5, 4, "GT3 Challenge", None),
            (1, 3, 2, 1, "World of Outlaws Sprint Cars", ""),
        ],
    )
    memory_conn.commit()
    _backfill_racing_type(memory_conn.cursor())
    memory_conn.commit()
    rows = memory_conn.execute(
        """
        SELECT series_name, racing_type
        FROM race_results
        ORDER BY subsession_id
        """
    ).fetchall()
    assert rows[0] == ("NASCAR Cup Series", "oval")
    assert rows[1] == ("GT3 Challenge", "road")
    assert rows[2] == ("World of Outlaws Sprint Cars", "dirt")
