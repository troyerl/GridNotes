"""Export and import scouting database snapshots for broadcast."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..data.db import create_memory_database
from .protocol import SnapshotPayload


def _table_as_dicts(cursor: sqlite3.Cursor, table: str) -> list[dict[str, Any]]:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if not columns:
        return []
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    return [dict(zip(columns, row, strict=True)) for row in rows]


def export_database_snapshot(
    conn: sqlite3.Connection,
    *,
    broadcaster_name: str = "",
) -> SnapshotPayload:
    cursor = conn.cursor()
    return SnapshotPayload(
        broadcaster_name=broadcaster_name,
        drivers=_table_as_dicts(cursor, "drivers"),
        race_results=_table_as_dicts(cursor, "race_results"),
    )


def _replace_table_rows(
    cursor: sqlite3.Cursor,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    cursor.execute(f"DELETE FROM {table}")
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    col_sql = ", ".join(columns)
    cursor.executemany(
        f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})",
        [[row.get(col) for col in columns] for row in rows],
    )


def apply_snapshot_to_memory(snapshot: SnapshotPayload | dict[str, Any]) -> sqlite3.Connection:
    """Build a fresh in-memory database from a broadcast snapshot."""
    if isinstance(snapshot, dict):
        payload = SnapshotPayload(
            broadcaster_name=str(snapshot.get("broadcaster_name") or ""),
            drivers=list(snapshot.get("drivers") or []),
            race_results=list(snapshot.get("race_results") or []),
        )
    else:
        payload = snapshot

    conn = create_memory_database()
    cursor = conn.cursor()
    _replace_table_rows(cursor, "drivers", payload.drivers)
    _replace_table_rows(cursor, "race_results", payload.race_results)
    conn.commit()
    return conn
