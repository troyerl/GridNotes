"""Tests for gridnotes.core.timestamps."""

from datetime import datetime, timezone

from gridnotes.core.timestamps import format_last_seen, parse_race_timestamp


def test_parse_race_timestamp_iso_z():
    dt = parse_race_timestamp("2026-01-15T20:00:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.tzinfo is not None


def test_parse_race_timestamp_unix():
    ts = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc).timestamp()
    dt = parse_race_timestamp(ts)
    assert dt is not None
    assert dt.year == 2026


def test_parse_race_timestamp_invalid():
    assert parse_race_timestamp("") is None
    assert parse_race_timestamp("not-a-date") is None


def test_format_last_seen_invalid():
    assert format_last_seen(None) == "N/A"
    assert format_last_seen("bad") == "N/A"
