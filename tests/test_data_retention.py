"""Tests for gridnotes.data.data_retention."""

from datetime import datetime, timedelta, timezone

from gridnotes.data.data_retention import (
    purge_expired_race_results,
    retention_cutoff_iso,
    retention_label,
)


def test_retention_label_never():
    assert retention_label("never") == "Never delete"
    assert retention_label(None) == "Never delete"


def test_retention_cutoff_iso():
    assert retention_cutoff_iso("never") is None
    cutoff = retention_cutoff_iso("90")
    assert cutoff is not None
    parsed = datetime.fromisoformat(cutoff)
    assert parsed.tzinfo is not None


def test_purge_expired_race_results(memory_conn):
    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name) VALUES (1, 'A')"
    )
    memory_conn.executemany(
        """
        INSERT INTO race_results (cust_id, subsession_id, race_at)
        VALUES (?, ?, ?)
        """,
        [(1, 1, old), (1, 2, recent), (1, 3, None)],
    )
    memory_conn.commit()
    deleted = purge_expired_race_results(memory_conn, "365")
    assert deleted == 1
    remaining = memory_conn.execute(
        "SELECT COUNT(*) FROM race_results"
    ).fetchone()[0]
    assert remaining == 2


def test_purge_never_deletes_nothing(memory_conn):
    memory_conn.execute(
        "INSERT INTO race_results (cust_id, subsession_id, race_at) VALUES (1, 1, '2000-01-01T00:00:00+00:00')"
    )
    memory_conn.commit()
    assert purge_expired_race_results(memory_conn, "never") == 0
