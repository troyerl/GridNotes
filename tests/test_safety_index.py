"""Tests for gridnotes.safety.safety_index."""

from gridnotes.safety.safety_index import (
    MIN_RACES_FOR_SCORE,
    compute_safety_index,
    empty_safety,
    live_sort_score,
    safety_tooltip,
)


def test_insufficient_races_unknown_tier():
    safety = compute_safety_index(
        avg_inc=2.0,
        total_races=MIN_RACES_FOR_SCORE - 1,
        dnf_total=0,
        avg_pos_delta=0.0,
    )
    assert safety.tier == "unknown"
    assert not safety.risky


def test_clean_driver_low_tier():
    safety = compute_safety_index(
        avg_inc=1.0,
        total_races=20,
        dnf_total=1,
        avg_pos_delta=1.0,
    )
    assert safety.tier == "low"
    assert safety.score < 35


def test_high_incidents_high_tier():
    safety = compute_safety_index(
        avg_inc=7.0,
        total_races=30,
        dnf_total=10,
        avg_pos_delta=-4.0,
    )
    assert safety.tier == "high"
    assert safety.risky


def test_empty_safety():
    safety = empty_safety()
    assert safety.tier == "unknown"
    assert safety.total_races == 0


def test_live_sort_score_unknown_last():
    safety = empty_safety()
    assert live_sort_score(safety, 0) == -1.0
    assert live_sort_score(safety, 5) == 0.0


def test_safety_tooltip_contains_score():
    safety = compute_safety_index(
        avg_inc=2.0,
        total_races=10,
        dnf_total=2,
        avg_pos_delta=0.0,
    )
    tip = safety_tooltip(safety)
    assert "Safety Index" in tip
