"""Tests for racing-type classification helpers."""

from gridnotes.iracing.racing_type import (
    RACING_TYPE_FORMULA,
    RACING_TYPE_OVAL,
    RACING_TYPE_ROAD,
    classify_racing_type_from_category,
    classify_racing_type_from_series,
    racing_type_label,
    racing_type_stats_scope,
    resolve_racing_type,
)


def test_classify_formula_series():
    assert classify_racing_type_from_series("Formula Vee") == RACING_TYPE_FORMULA
    assert classify_racing_type_from_series("iRacing Formula iR-04") == RACING_TYPE_FORMULA


def test_classify_oval_series():
    assert classify_racing_type_from_series("NASCAR Cup Series") == RACING_TYPE_OVAL


def test_classify_dirt_series():
    from gridnotes.iracing.racing_type import RACING_TYPE_DIRT

    assert classify_racing_type_from_series("World of Outlaws Sprint Cars") == RACING_TYPE_DIRT
    assert classify_racing_type_from_series("Dirt Road Series") == RACING_TYPE_DIRT


def test_classify_road_series():
    assert classify_racing_type_from_series("GT3 Challenge") == RACING_TYPE_ROAD
    assert classify_racing_type_from_series("Porsche Cup") == RACING_TYPE_ROAD


def test_classify_from_category():
    from gridnotes.iracing.racing_type import RACING_TYPE_DIRT

    assert classify_racing_type_from_category("Oval") == RACING_TYPE_OVAL
    assert classify_racing_type_from_category("Dirt oval") == RACING_TYPE_DIRT
    assert classify_racing_type_from_category("Dirt road") == RACING_TYPE_DIRT
    assert classify_racing_type_from_category("Road") == RACING_TYPE_ROAD


def test_resolve_prefers_formula_series_over_road_category():
    assert (
        resolve_racing_type(category="Road", series_name="Formula Vee")
        == RACING_TYPE_FORMULA
    )


def test_resolve_uses_category_when_series_unknown():
    assert resolve_racing_type(category="Oval", series_name=None) == RACING_TYPE_OVAL
    from gridnotes.iracing.racing_type import RACING_TYPE_DIRT

    assert resolve_racing_type(category="Dirt oval", series_name=None) == RACING_TYPE_DIRT


def test_racing_type_label_and_stats_scope():
    assert racing_type_label("oval") == "Oval"
    assert racing_type_label("") == ""
    assert racing_type_stats_scope("formula") == "Formula stats"
    assert racing_type_stats_scope(None) == ""
