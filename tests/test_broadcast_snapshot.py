"""Tests for broadcast patches and snapshots."""

from gridnotes.broadcast.patches import apply_driver_patch
from gridnotes.broadcast.protocol import SnapshotPayload
from gridnotes.broadcast.snapshot import apply_snapshot_to_memory, export_database_snapshot


def test_apply_driver_patch_updates_notes(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name, notes) VALUES (?, ?, ?)",
        (10, "Driver A", ""),
    )
    memory_conn.commit()
    changed = apply_driver_patch(
        memory_conn, {"cust_id": 10, "notes": "Late braking"}
    )
    assert changed is True
    row = memory_conn.execute(
        "SELECT notes FROM drivers WHERE cust_id = 10"
    ).fetchone()
    assert row[0] == "Late braking"


def test_apply_driver_patch_invalid_cust_id(memory_conn):
    assert apply_driver_patch(memory_conn, {"cust_id": "x"}) is False
    assert apply_driver_patch(memory_conn, {"cust_id": 1}) is False


def test_snapshot_export_and_import(memory_conn):
    memory_conn.execute(
        "INSERT INTO drivers (cust_id, driver_name, notes) VALUES (?, ?, ?)",
        (1, "Alice", "Clean"),
    )
    memory_conn.execute(
        """
        INSERT INTO race_results (cust_id, subsession_id, finish_position, incidents)
        VALUES (?, ?, ?, ?)
        """,
        (1, 100, 1, 2),
    )
    memory_conn.commit()

    snapshot = export_database_snapshot(memory_conn, broadcaster_name="Test")
    assert snapshot.broadcaster_name == "Test"
    assert len(snapshot.drivers) == 1
    assert len(snapshot.race_results) == 1

    receiver_conn = apply_snapshot_to_memory(snapshot)
    drivers = receiver_conn.execute("SELECT COUNT(*) FROM drivers").fetchone()[0]
    results = receiver_conn.execute("SELECT COUNT(*) FROM race_results").fetchone()[0]
    assert drivers == 1
    assert results == 1
    receiver_conn.close()


def test_apply_snapshot_from_dict():
    payload = {
        "broadcaster_name": "B",
        "drivers": [{"cust_id": 5, "driver_name": "Bob", "notes": ""}],
        "race_results": [],
    }
    conn = apply_snapshot_to_memory(payload)
    name = conn.execute(
        "SELECT driver_name FROM drivers WHERE cust_id = 5"
    ).fetchone()[0]
    assert name == "Bob"
    conn.close()
