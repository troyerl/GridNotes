"""Tests for gridnotes.ui.theme helpers."""

import pytest

pytest.importorskip("PyQt6.QtGui", exc_type=ImportError)

from gridnotes.ui.theme import (
    build_stylesheet,
    configure_modal_dialog,
    status_message_color,
    table_row_color,
)
from gridnotes.ui.appearance import (
    THEME_DARK_ID,
    THEME_LIGHT_ID,
    set_active_theme_id,
)
from gridnotes.ui.icons import clear_icon_cache, current_icon_button


def test_table_row_color_known_keys():
    color = table_row_color(THEME_DARK_ID, "base")
    assert color.isValid()


def test_status_message_color():
    assert status_message_color(THEME_DARK_ID, ok=True)
    assert status_message_color(THEME_DARK_ID, ok=False)


def test_build_stylesheet_contains_driver_table():
    css = build_stylesheet(THEME_DARK_ID)
    assert "driverTable" in css
    assert "QDialog" in css
    assert "QFrame#appModalPanel" in css
    assert "border-radius: 14px" in css
    assert "{{" not in css


def test_configure_modal_dialog_wraps_content_in_rounded_panel(qapp):
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QDialog, QFrame, QLabel, QVBoxLayout

    dialog = QDialog()
    dialog.setObjectName("testModalDialog")
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(18, 16, 18, 16)
    label = QLabel("Hello")
    layout.addWidget(label)

    configure_modal_dialog(dialog)

    assert dialog.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    panel = dialog.findChild(QFrame, "appModalPanel")
    assert panel is not None
    assert label.parent() is panel
    assert getattr(dialog, "_modal_panel_wrapped", False)
    configure_modal_dialog(dialog)
    assert dialog.findChildren(QFrame, "appModalPanel") == [panel]


def test_build_stylesheet_light_mode_pref_tokens():
    css = build_stylesheet(THEME_LIGHT_ID)
    assert "pref_like_fg" not in css
    assert "#047857" in css
    assert "#374151" in css
    assert "{{" not in css


def test_active_theme_drives_button_icon_color(monkeypatch):
    monkeypatch.setattr(
        "gridnotes.ui.appearance.get_theme_id", lambda: THEME_DARK_ID
    )
    set_active_theme_id(THEME_LIGHT_ID)
    clear_icon_cache()
    assert current_icon_button() == "#4b5563"
    set_active_theme_id(THEME_DARK_ID)
    clear_icon_cache()
    assert current_icon_button() == "#e8eaed"
