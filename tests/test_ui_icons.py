"""Tests for Font Awesome icon helpers."""

import pytest

pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)

from PyQt6.QtWidgets import QApplication

from gridnotes.ui.icons import (
    driver_mark_glyphs,
    fa,
    load_font,
    trend_icon_name,
)


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
