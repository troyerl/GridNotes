"""Tests for gridnotes.data.driver_models."""

from gridnotes.data.driver_models import (
    DriverTableRow,
    apply_racing_type_stats_to_live_entry,
    build_live_session_entries,
    compare_race_finish_outcome,
    format_dnf_breakdown,
    format_head_to_head_record,
    format_live_session_at_glance,
    format_vs_you_outcome,
)


def test_compare_race_finish_outcome():
    assert compare_race_finish_outcome(1, 0, 3, 0) == "win"
    assert compare_race_finish_outcome(4, 0, 2, 0) == "loss"
    assert compare_race_finish_outcome(3, 0, 3, 0) == "tie"
    assert compare_race_finish_outcome(5, 3, 2, 0) == "loss"
    assert compare_race_finish_outcome(5, 0, 2, 1) == "win"


def test_format_head_to_head_record():
    assert format_head_to_head_record(0, 0, 0) == "—"
    assert format_head_to_head_record(3, 2) == "You 3–2"
    assert format_head_to_head_record(1, 1, 1) == "You 1–1–1"
    assert format_vs_you_outcome("win") == "You won"
    assert format_vs_you_outcome("loss") == "You lost"


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


def test_live_mode_card_sort_by_race_count():
    from gridnotes.data.driver_models import sort_live_mode_card_entries

    entries = [
        {"cust_id": 1, "name": "New", "total_races": 0},
        {"cust_id": 2, "name": "Veteran", "total_races": 25},
        {"cust_id": 3, "name": "Regular", "total_races": 8},
    ]
    order = [e["cust_id"] for e in sort_live_mode_card_entries(entries)]
    assert order == [2, 3, 1]


def test_format_shared_races_label():
    from gridnotes.data.driver_models import format_shared_races_label

    assert format_shared_races_label(None) == ""
    assert format_shared_races_label(0) == "No shared races yet"
    assert format_shared_races_label(1) == "Raced together 1 time"
    assert format_shared_races_label(5) == "Raced together 5 times"


def test_format_live_session_at_glance_empty():
    assert format_live_session_at_glance([]) == ""


def _sample_table_row(*, total_races: int = 10, avg_inc: float = 2.0) -> DriverTableRow:
    return DriverTableRow.from_sql_row(
        (
            "Alice",
            avg_inc,
            5.0,
            total_races,
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


def test_apply_racing_type_stats_to_live_entry_uses_type_row():
    entry = {"cust_id": 42, "total_races": 99, "avg_inc": 9.9}
    type_row = _sample_table_row(total_races=4, avg_inc=1.5)
    apply_racing_type_stats_to_live_entry(
        entry,
        type_row,
        racing_type="oval",
        racing_type_label="Oval",
    )
    assert entry["racing_type"] == "oval"
    assert entry["racing_type_label"] == "Oval"
    assert entry["total_races"] == 4
    assert entry["avg_inc"] == 1.5
    assert entry["has_history"] is True
    assert entry["safety"].total_races == 4
    assert entry["dnf_breakdown"] == "Quit:1"


def test_apply_racing_type_stats_to_live_entry_clears_missing_history():
    entry = {"cust_id": 42, "total_races": 12, "avg_inc": 3.0}
    apply_racing_type_stats_to_live_entry(
        entry,
        None,
        racing_type="road",
        racing_type_label="Road",
    )
    assert entry["total_races"] == 0
    assert entry["avg_inc"] is None
    assert entry["safety"].tier == "unknown"
    assert entry["dnf_breakdown"] == ""
