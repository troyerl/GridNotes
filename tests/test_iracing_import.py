"""Tests for gridnotes.iracing.iracing_import."""

from tests.conftest import SAMPLE_EVENT_RESULT

from gridnotes.iracing.iracing_import import (
    REASON_OUT_DISCONNECTED,
    REASON_OUT_RUNNING,
    import_race_entries,
    normalize_reason_out_id,
    parse_iracing_event_result,
    parse_races_from_json,
    sync_live_session_drivers,
)


def test_normalize_reason_out_id():
    assert normalize_reason_out_id(0, None) == REASON_OUT_RUNNING
    assert normalize_reason_out_id(None, "Disconnected") == REASON_OUT_DISCONNECTED
    assert normalize_reason_out_id(None, "unknown") is None


def test_parse_iracing_event_result():
    races, series, ts = parse_iracing_event_result(SAMPLE_EVENT_RESULT)
    assert len(races) == 1
    assert races[0]["subsession_id"] == 12345
    assert series == "Formula Vee"
    assert ts == "2026-01-15T20:00:00Z"


def test_parse_races_from_json_event_result():
    races, series, ts = parse_races_from_json(SAMPLE_EVENT_RESULT)
    assert len(races) == 1
    assert series == "Formula Vee"


def test_parse_races_from_json_races_wrapper():
    data = {"races": [{"subsession_id": 9, "results": []}]}
    races, _, _ = parse_races_from_json(data)
    assert len(races) == 1


def test_parse_races_from_json_list():
    data = [{"subsession_id": 1, "results": []}]
    races, _, _ = parse_races_from_json(data)
    assert len(races) == 1


def test_import_race_entries(memory_conn):
    races, series, ts = parse_races_from_json(SAMPLE_EVENT_RESULT)
    imported, results_in, updated, skipped, affected = import_race_entries(
        memory_conn.cursor(),
        races,
        series,
        ts,
        None,
    )
    assert imported >= 1
    assert results_in >= 2
    assert 1001 in affected
    assert 1002 in affected
    name = memory_conn.execute(
        "SELECT driver_name FROM drivers WHERE cust_id = 1001"
    ).fetchone()[0]
    assert name == "Alice Racer"
    memory_conn.commit()

    # Re-import same subsession updates existing rows
    _, _, updated2, skipped2, _ = import_race_entries(
        memory_conn.cursor(),
        races,
        series,
        ts,
        None,
    )
    assert updated2 >= 2
    assert skipped2 == 0

    types = {
        row[0]
        for row in memory_conn.execute(
            "SELECT DISTINCT racing_type FROM race_results WHERE racing_type IS NOT NULL"
        ).fetchall()
    }
    assert types == {"formula"}


def test_sync_live_session_drivers(memory_conn):
    added = sync_live_session_drivers(
        memory_conn.cursor(),
        [{"cust_id": 500, "name": "Live Driver"}],
    )
    assert 500 in added
    added_again = sync_live_session_drivers(
        memory_conn.cursor(),
        [{"cust_id": 500, "name": "Live Driver"}],
    )
    assert added_again == []
