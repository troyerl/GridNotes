"""Tests for gridnotes.iracing.session_kind."""

from tests.conftest import MockIRacing

from gridnotes.iracing.session_kind import (
    SESSION_KIND_RACE,
    current_session_kind,
    is_live_scouting_session,
    is_race_session,
    normalize_session_kind,
    session_kind_label,
)


def test_normalize_session_kind_strings():
    assert normalize_session_kind("Race") == SESSION_KIND_RACE
    assert normalize_session_kind("Qualifying") == "qualify"
    assert normalize_session_kind("Practice") == "practice"


def test_normalize_session_kind_ints():
    assert normalize_session_kind(6) == SESSION_KIND_RACE
    assert normalize_session_kind(4) == "qualify"


def test_session_kind_label():
    assert session_kind_label(SESSION_KIND_RACE) == "Race"
    assert session_kind_label(None) == "Session"


def test_is_race_session():
    assert is_race_session(SESSION_KIND_RACE)
    assert not is_race_session("practice")


def test_is_live_scouting_session():
    assert is_live_scouting_session("practice")
    assert is_live_scouting_session(SESSION_KIND_RACE)


def test_current_session_kind_from_session_info():
    ir = MockIRacing(
        {
            "SessionNum": 0,
            "SessionInfo": {
                "Sessions": [{"SessionType": "Race", "SessionNum": 0}],
            },
        }
    )
    assert current_session_kind(ir) == SESSION_KIND_RACE
