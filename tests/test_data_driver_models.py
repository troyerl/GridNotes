"""Tests for gridnotes.data.driver_models."""

from gridnotes.data.driver_models import (
    DriverTableRow,
    build_live_session_entries,
    format_dnf_breakdown,
    format_live_session_at_glance,
)


def test_format_dnf_breakdown():
    assert format_dnf_breakdown(1, 0, 2, 0, 0) == "Disc:1, Quit:2"
    assert format_dnf_breakdown(0, 0, 0, 0, 0) == ""


def test_driver_table_row_safety():
    row = DriverTableRow.from_sql_row(
        (
            "Alice",
            2.0,
            5.0,
            10,
            1500,
            3.5,
            "Series",
            0.5,
            42,
            None,
            1,
            0,
            0,
            1,
            0,
            0,
            0,
        )
    )
    assert row.cust_id == 42
    assert row.safety.total_races == 10
    assert row.dnf_breakdown == "Quit:1"


def test_build_live_session_entries():
    row = DriverTableRow.from_sql_row(
        (
            "Alice",
            2.0,
            5.0,
            10,
            1500,
            3.5,
            "Series",
            0.5,
            1,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )
    )
    entries = build_live_session_entries({1}, {1: "Alice"}, [row])
    assert len(entries) == 1
    assert entries[0]["cust_id"] == 1


def test_format_live_session_at_glance_empty():
    assert format_live_session_at_glance([]) == ""
