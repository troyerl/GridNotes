"""Tests for gridnotes.ui.theme helpers."""

from gridnotes.ui.theme import (
    build_stylesheet,
    status_message_color,
    table_row_color,
)
from gridnotes.ui.theme_tokens import THEME_DARK_ID


def test_table_row_color_known_keys():
    color = table_row_color(THEME_DARK_ID, "base")
    assert color.isValid()


def test_status_message_color():
    assert status_message_color(THEME_DARK_ID, ok=True)
    assert status_message_color(THEME_DARK_ID, ok=False)


def test_build_stylesheet_contains_driver_table():
    css = build_stylesheet(THEME_DARK_ID)
    assert "driverTable" in css
    assert "{{" not in css
