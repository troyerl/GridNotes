"""Tests for import history queries."""

from gridnotes.data.import_history import (
    count_import_history,
    count_imported_sessions,
    fetch_import_history,
)


def test_fetch_import_history_groups_by_subsession(memory_conn):
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents,
            series_name, race_at
        )
        VALUES (?, ?, 1, 0, ?, ?)
        """,
        [
            (1, 100, "Formula Vee", "2026-01-01T12:00:00Z"),
            (2, 100, "Formula Vee", "2026-01-01T12:00:00Z"),
            (3, 200, "GT3 Fixed", "2026-02-01T12:00:00Z"),
        ],
    )
    memory_conn.commit()

    history = fetch_import_history(memory_conn)
    assert len(history) == 2
    assert history[0].subsession_id == 200
    assert history[0].session_name == "GT3 Fixed"
    assert history[0].driver_count == 1
    assert history[1].subsession_id == 100
    assert history[1].driver_count == 2


def test_fetch_import_history_ignores_missing_subsession_id(memory_conn):
    memory_conn.execute(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (1, 0, 1, 0)
        """
    )
    memory_conn.commit()
    assert fetch_import_history(memory_conn) == []
    assert count_imported_sessions(memory_conn) == 0


def test_fetch_import_history_unknown_session_name(memory_conn):
    memory_conn.execute(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (1, 55, 1, 0)
        """
    )
    memory_conn.commit()
    history = fetch_import_history(memory_conn)
    assert len(history) == 1
    assert history[0].session_name == "Unknown session"


def test_fetch_import_history_filters_by_session_id(memory_conn):
    memory_conn.executemany(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (?, ?, 1, 0)
        """,
        [(1, 12345678), (2, 87654321), (3, 12349999)],
    )
    memory_conn.commit()

    history = fetch_import_history(memory_conn, session_id_query="1234")
    assert len(history) == 2
    assert {entry.subsession_id for entry in history} == {12345678, 12349999}

    exact = fetch_import_history(memory_conn, session_id_query="87654321")
    assert len(exact) == 1
    assert exact[0].subsession_id == 87654321

    missing = fetch_import_history(memory_conn, session_id_query="00000000")
    assert missing == []


def test_fetch_import_history_pagination(memory_conn):
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents, race_at
        )
        VALUES (?, ?, 1, 0, ?)
        """,
        [
            (1, 300, "2026-01-03T12:00:00Z"),
            (1, 200, "2026-01-02T12:00:00Z"),
            (1, 100, "2026-01-01T12:00:00Z"),
        ],
    )
    memory_conn.commit()

    assert count_import_history(memory_conn) == 3
    page1 = fetch_import_history(memory_conn, limit=2, offset=0)
    page2 = fetch_import_history(memory_conn, limit=2, offset=2)
    assert [entry.subsession_id for entry in page1] == [300, 200]
    assert [entry.subsession_id for entry in page2] == [100]


def test_count_imported_sessions_alias(memory_conn):
    memory_conn.execute(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (1, 42, 1, 0)
        """
    )
    memory_conn.commit()
    assert count_imported_sessions(memory_conn) == 1


def test_count_import_history_with_session_id_filter(memory_conn):
    memory_conn.executemany(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (?, ?, 1, 0)
        """,
        [(1, 111), (1, 222), (1, 112)],
    )
    memory_conn.commit()
    assert count_import_history(memory_conn) == 3
    assert count_import_history(memory_conn, session_id_query="11") == 2
    assert count_import_history(memory_conn, session_id_query="222") == 1
    assert count_import_history(memory_conn, session_id_query="999") == 0


def test_fetch_import_history_pagination_with_filter(memory_conn):
    memory_conn.executemany(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents, race_at
        )
        VALUES (?, ?, 1, 0, ?)
        """,
        [
            (1, 9100, "2026-01-04T12:00:00Z"),
            (1, 9200, "2026-01-03T12:00:00Z"),
            (1, 9300, "2026-01-02T12:00:00Z"),
            (1, 8100, "2026-01-01T12:00:00Z"),
        ],
    )
    memory_conn.commit()

    assert count_import_history(memory_conn, session_id_query="9") == 3
    page = fetch_import_history(
        memory_conn,
        limit=2,
        offset=1,
        session_id_query="9",
    )
    assert [entry.subsession_id for entry in page] == [9200, 9300]


def test_fetch_import_history_rejects_invalid_limit_and_offset(memory_conn):
    memory_conn.execute(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (1, 1, 1, 0)
        """
    )
    memory_conn.commit()
    assert fetch_import_history(memory_conn, limit=0) == []
    rows = fetch_import_history(memory_conn, limit=10, offset=-5)
    assert len(rows) == 1
    assert rows[0].subsession_id == 1
