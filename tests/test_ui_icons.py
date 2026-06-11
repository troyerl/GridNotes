"""Tests for Font Awesome icon helpers."""

import pytest

pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)

from PyQt6.QtWidgets import QApplication

from gridnotes.ui.icons import (
    _resolve_icon_color,
    clear_icon_cache,
    driver_mark_glyphs,
    fa,
    fa_icon,
    load_font,
    trend_icon_name,
)
from gridnotes.ui.theme_tokens import THEME_LIGHT_ID


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_load_font(qapp):
    assert load_font() is True


def test_fa_known_glyph():
    assert fa("chevron-down") != ""
    assert fa("not-a-real-icon") == ""


def test_trend_icon_name():
    assert trend_icon_name("improving") == "arrow-trend-up"
    assert trend_icon_name("unknown") is None


def test_driver_mark_glyphs():
    text = driver_mark_glyphs(1, True)
    assert fa("thumbs-up") in text
    assert fa("triangle-exclamation") in text


def test_fa_icon_uses_active_light_theme_for_buttons(qapp, monkeypatch):
    from gridnotes.ui.appearance import THEME_DARK_ID, set_active_theme_id

    monkeypatch.setattr("gridnotes.ui.appearance.get_theme_id", lambda: THEME_DARK_ID)
    set_active_theme_id(THEME_LIGHT_ID)
    clear_icon_cache()
    from gridnotes.ui.icons import current_icon_button

    assert current_icon_button().lower() == "#4b5563"
    icon = fa_icon("gear", size=16, color_key=current_icon_button())
    assert not icon.isNull()
