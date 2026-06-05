"""Tests for gridnotes.privacy.streamer_mode."""

from gridnotes.privacy.streamer_mode import (
    display_driver_name,
    driver_alias_number,
    is_streamer_mode_enabled,
    mask_cust_id_display,
    streamer_display_name,
)
from gridnotes.safety.safety_index import compute_safety_index


def test_is_streamer_mode_enabled():
    assert is_streamer_mode_enabled("1")
    assert not is_streamer_mode_enabled("0")
    assert not is_streamer_mode_enabled(None)


def test_driver_alias_number_stable():
    assert driver_alias_number(1042) == 42
    assert driver_alias_number(42) == 42


def test_streamer_display_name_car_number():
    name = streamer_display_name(999, car_number="14")
    assert name == "Driver #14"


def test_streamer_display_name_with_risk():
    safety = compute_safety_index(
        avg_inc=6.0,
        total_races=10,
        dnf_total=3,
        avg_pos_delta=-2.0,
    )
    name = streamer_display_name(100, safety, compact=True)
    assert "Driver #" in name
    assert "(" in name


def test_display_driver_name_streamer_off():
    assert display_driver_name(1, "Real Name", None, streamer_mode=False) == "Real Name"


def test_display_driver_name_streamer_on():
    result = display_driver_name(42, "Real Name", None, streamer_mode=True)
    assert "Real Name" not in result
    assert "Driver #" in result


def test_mask_cust_id_display():
    assert mask_cust_id_display(12345, streamer_mode=True) == "—"
    assert mask_cust_id_display(12345, streamer_mode=False) == "12345"
