"""Shared fixtures for GridNotes unit tests."""

from __future__ import annotations

import sqlite3
from typing import Iterator

import pytest

from gridnotes.data.db import connect_db, create_memory_database, init_db


@pytest.fixture
def memory_conn() -> Iterator[sqlite3.Connection]:
    conn = create_memory_database()
    yield conn
    conn.close()


@pytest.fixture
def file_db(tmp_path, monkeypatch) -> Iterator[tuple[str, sqlite3.Connection]]:
    """On-disk DB with full schema (settings, migrations)."""
    db_path = str(tmp_path / "driver_history.db")
    monkeypatch.setattr("gridnotes.data.db.DB_NAME", db_path)
    monkeypatch.setattr("gridnotes.data.backup.get_db_path", lambda: db_path)
    init_db(db_path)
    conn = connect_db(db_path)
    yield db_path, conn
    conn.close()


@pytest.fixture(scope="session")
def qapp():
    """Qt application instance required before constructing widgets."""
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def make_driver_sql_row(
    *,
    name: str = "Test Driver",
    avg_inc: float | None = 2.0,
    avg_fin: float | None = 5.0,
    total_races: int = 10,
    last_ir: int | None = 1500,
    last_sr: float | None = 3.5,
    last_series: str | None = "Formula Vee",
    avg_pos_delta: float | None = 0.5,
    cust_id: int = 42,
    race_preference: int | None = None,
    dnf_total: int = 1,
    disc: int = 0,
    eject: int = 0,
    quit_: int = 1,
    dq: int = 0,
    other: int = 0,
    has_notes: int = 0,
) -> tuple:
    return (
        name,
        avg_inc,
        avg_fin,
        total_races,
        last_ir,
        last_sr,
        last_series,
        avg_pos_delta,
        cust_id,
        race_preference,
        dnf_total,
        disc,
        eject,
        quit_,
        dq,
        other,
        has_notes,
    )


SAMPLE_EVENT_RESULT = {
    "type": "event_result",
    "data": {
        "subsession_id": 12345,
        "series_name": "Formula Vee",
        "start_time": "2026-01-15T20:00:00Z",
        "session_results": [
            {
                "simsession_type_name": "Race",
                "results": [
                    {
                        "cust_id": 1001,
                        "name": "Alice Racer",
                        "finish": 0,
                        "starting_position": 2,
                        "incidents": 4,
                        "oldi_rating": 1500,
                        "newi_rating": 1520,
                        "new_sub_level": 350,
                        "new_license_level": 12,
                        "reason_out": "Running",
                        "reason_out_id": 0,
                        "license": "C 3.50",
                    },
                    {
                        "cust_id": 1002,
                        "name": "Bob Racer",
                        "finish": 1,
                        "starting_position": 0,
                        "incidents": 8,
                        "reason_out": "Disconnected",
                        "reason_out_id": 1,
                    },
                ],
            }
        ],
    },
}


class MockIRacing:
    """Minimal dict-like SDK stub for telemetry tests."""

    def __init__(self, data: dict | None = None) -> None:
        self._data = data or {}

    def __getitem__(self, key: str):
        if key not in self._data:
            raise KeyError(key)
        return self._data[key]

    def get(self, key: str, default=None):
        return self._data.get(key, default)
