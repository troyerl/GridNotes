"""Tests for live session context parsing from iRacing SDK-shaped data."""

from gridnotes.iracing.session_context import (
    format_session_context_banner,
    parse_session_context,
)


def _fake_ir(payload: dict) -> dict:
    """Minimal dict the parser reads via ``ir[key]``."""
    return payload


def test_parse_session_context_reads_track_category_series_and_laps():
    ir = _fake_ir(
        {
            "SessionNum": 0,
            "WeekendInfo": {
                "TrackDisplayName": "Daytona International Speedway",
                "Category": "oval",
                "SeriesName": "NASCAR Cup Series",
            },
            "SessionInfo": {
                "Sessions": [{"SessionLaps": 25}],
            },
        }
    )
    ctx = parse_session_context(ir)
    assert ctx["track"] == "Daytona International Speedway"
    assert ctx["category"] == "Oval"
    assert ctx["series"] == "NASCAR Cup Series"
    assert ctx["laps"] == "25"


def test_parse_session_context_uses_timed_minutes_when_no_laps():
    ir = _fake_ir(
        {
            "SessionNum": 0,
            "WeekendInfo": {"Category": "road"},
            "SessionInfo": {
                "Sessions": [{"SessionTime": "45.0"}],
            },
        }
    )
    ctx = parse_session_context(ir)
    assert ctx["category"] == "Road"
    assert ctx["timed_minutes"] == "45"
    assert "laps" not in ctx


def test_format_session_context_banner_includes_series_context():
    banner = format_session_context_banner(
        "race",
        {
            "laps": "30",
            "track": "Spa",
            "category": "Road",
            "series": "GT3 Challenge",
        },
    )
    assert banner == "Race · 30 laps · Spa · Road"
