"""Tests for gridnotes.data.race_history."""

from gridnotes.data.race_history import (
    count_driver_race_history,
    fetch_driver_race_history,
    fetch_drivers_with_race_history,
)


def test_fetch_drivers_with_race_history(memory_conn):
    memory_conn.executemany(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (?, ?)",
        [(1, "Alice"), (2, "Bob"), (3, "Charlie")],
    )
    memory_conn.executemany(
        "INSERT INTO race_results (cust_id, subsession_id) VALUES (?, ?)",
        [(1, 100), (3, 0)],
    )
    memory_conn.commit()
    drivers = fetch_drivers_with_race_history(memory_conn)
    assert drivers == [(1, "Alice")]


def test_fetch_driver_race_history_with_player(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'Alice'), (2, 'Bob')"
    )
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, reason_out_id, series_name, race_at
        )
        VALUES (?, ?, ?, 0, 'Test Series', ?)
        """,
        [
            (1, 100, 1, "2026-01-02T00:00:00+00:00"),
            (2, 100, 3, "2026-01-02T00:00:00+00:00"),
            (2, 101, 2, "2026-01-01T00:00:00+00:00"),
        ],
    )
    memory_conn.commit()
    assert count_driver_race_history(memory_conn, 2) == 2
    entries = fetch_driver_race_history(
        memory_conn,
        2,
        player_cust_id=1,
        limit=10,
        offset=0,
    )
    assert len(entries) == 2
    assert entries[0].subsession_id == 100
    assert entries[0].player_finish == 1
    assert entries[0].finish_position == 3
