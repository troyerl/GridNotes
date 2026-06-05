"""Tests for gridnotes.safety.safety_trend."""

from gridnotes.safety.safety_index import compute_safety_index
from gridnotes.safety.safety_trend import (
    MIN_RACES_FOR_TREND,
    compute_safety_trend,
    safety_index_from_recent_races,
)


def test_safety_index_from_recent_races_empty():
    safety, count = safety_index_from_recent_races([])
    assert count == 0
    assert safety.tier == "unknown"


def test_safety_index_from_recent_races_dnf_counted():
    rows = [(4, 10, 5, 1), (2, 8, 6, 0), (1, 5, 4, 3)]
    safety, count = safety_index_from_recent_races(rows)
    assert count == 3
    assert safety.total_races == 3


def test_compute_safety_trend_improving():
    lifetime = compute_safety_index(
        avg_inc=5.0,
        total_races=20,
        dnf_total=5,
        avg_pos_delta=-1.0,
    )
    recent_rows = [(1, 5, 5, 0), (1, 4, 4, 0), (0, 3, 3, 0)]
    trend = compute_safety_trend(lifetime, recent_rows)
    assert trend.direction in ("improving", "stable", "worsening")
    assert trend.window_races == len(recent_rows)


def test_compute_safety_trend_unknown_short_window():
    lifetime = compute_safety_index(
        avg_inc=3.0,
        total_races=10,
        dnf_total=1,
        avg_pos_delta=0.0,
    )
    trend = compute_safety_trend(lifetime, [(2, 5, 5, 0)])
    assert trend.direction == "unknown"
    assert trend.window_races < MIN_RACES_FOR_TREND
