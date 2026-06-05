"""Tests for gridnotes.services.audio_spotter message logic."""

from gridnotes.safety.safety_index import compute_safety_index
from gridnotes.services.audio_spotter import (
    SpotterDriverInfo,
    build_spotter_message,
    is_audio_spotter_setting_enabled,
    should_warn_driver,
)


def _risky_info(**kwargs) -> SpotterDriverInfo:
    safety = compute_safety_index(
        avg_inc=kwargs.get("avg_inc", 7.0),
        total_races=kwargs.get("total_races", 15),
        dnf_total=kwargs.get("dnf_total", 5),
        avg_pos_delta=kwargs.get("avg_pos_delta", -3.0),
    )
    return SpotterDriverInfo(
        name=kwargs.get("name", "Rival"),
        notes=kwargs.get("notes", ""),
        race_preference=kwargs.get("race_preference"),
        safety=safety,
    )


def test_is_audio_spotter_setting_enabled():
    assert is_audio_spotter_setting_enabled("1")
    assert not is_audio_spotter_setting_enabled("0")


def test_should_warn_disliked():
    info = _risky_info(race_preference=-1, avg_inc=1.0, dnf_total=0, avg_pos_delta=0.0)
    assert should_warn_driver(info)


def test_should_warn_high_risk():
    info = _risky_info()
    assert should_warn_driver(info)


def test_should_not_warn_clean_liked():
    safety = compute_safety_index(
        avg_inc=1.0, total_races=10, dnf_total=0, avg_pos_delta=0.0
    )
    info = SpotterDriverInfo("Clean", "", 1, safety)
    assert not should_warn_driver(info)


def test_build_spotter_message_disliked():
    info = _risky_info(race_preference=-1, notes="Late divebombs.")
    msg = build_spotter_message(info)
    assert "disliked" in msg.lower()
    assert "Late divebombs" in msg


def test_build_spotter_message_streamer_name():
    info = _risky_info(race_preference=-1)
    msg = build_spotter_message(info, announce_name="Driver #14")
    assert "Driver #14" in msg
