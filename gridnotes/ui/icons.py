"""Font Awesome Free (solid) icons for GridNotes UI."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

FONT_FAMILY = "Font Awesome 6 Free"
FONT_WEIGHT = QFont.Weight.Black
BUTTON_ICON_TEXT_GAP = 8

# Font Awesome 6 Free Solid (SIL OFL) — see gridnotes/assets/fonts/LICENSE.txt
_GLYPHS: dict[str, str] = {
    "arrow-right": "\uf061",
    "arrow-trend-down": "\ue097",
    "arrow-trend-up": "\ue098",
    "arrows-rotate": "\uf021",
    "book-open": "\uf518",
    "chevron-down": "\uf078",
    "chevron-left": "\uf053",
    "chevron-right": "\uf054",
    "chevron-up": "\uf077",
    "circle-question": "\uf059",
    "circle-stop": "\uf28d",
    "clock-rotate-left": "\uf1da",
    "cloud-arrow-down": "\uf0ed",
    "database": "\uf1c0",
    "download": "\uf019",
    "eraser": "\uf12d",
    "eye-slash": "\uf070",
    "file-import": "\uf56f",
    "flag-checkered": "\uf11e",
    "floppy-disk": "\uf0c7",
    "folder-open": "\uf07c",
    "gauge-high": "\uf625",
    "gear": "\uf013",
    "grip": "\uf58d",
    "link-slash": "\uf127",
    "minus": "\uf068",
    "note-sticky": "\uf249",
    "palette": "\uf53f",
    "pen": "\uf304",
    "pen-to-square": "\uf044",
    "plug": "\uf1e6",
    "plus": "\uf067",
    "road": "\uf018",
    "satellite-dish": "\uf7c0",
    "scale-balanced": "\uf24e",
    "stop": "\uf04d",
    "table-cells": "\uf00a",
    "tag": "\uf02b",
    "tower-broadcast": "\uf519",
    "trash": "\uf1f8",
    "trash-can": "\uf2ed",
    "triangle-exclamation": "\uf071",
    "trophy": "\uf091",
    "upload": "\uf093",
    "user-plus": "\uf234",
    "user-secret": "\uf21b",
    "users": "\uf0c0",
    "window-minimize": "\uf2d1",
    "wrench": "\uf0ad",
    "xmark": "\uf00d",
    "thumbs-down": "\uf165",
    "thumbs-up": "\uf164",
}

_TREND_ICONS = {
    "improving": "arrow-trend-up",
    "worsening": "arrow-trend-down",
    "stable": "arrow-right",
}

_SETTINGS_SECTION_ICONS = {
    "Auto-import": "cloud-arrow-down",
    "Appearance": "palette",
    "Data": "database",
    "Live Mode": "flag-checkered",
    "Maintenance": "wrench",
    "Legal": "scale-balanced",
}

_MAIN_TAB_ICONS = {
    "Drivers": "users",
    "Import history": "clock-rotate-left",
    "Leagues": "trophy",
    "Settings": "gear",
}

_font_loaded = False


def _assets_root() -> Path:
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "gridnotes"
    return Path(__file__).resolve().parent.parent


def _font_path() -> Path:
    return _assets_root() / "assets" / "fonts" / "fa-solid-900.ttf"


def load_font() -> bool:
    """Register Font Awesome with Qt. Safe to call multiple times."""
    global _font_loaded
    if _font_loaded:
        return True
    path = _font_path()
    if not path.is_file():
        return False
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id < 0:
        return False
    _font_loaded = True
    return True


def fa(name: str) -> str:
    """Return a single solid icon glyph, or empty string if unknown."""
    return _GLYPHS.get(name, "")


def trend_icon_name(direction: str) -> str | None:
    return _TREND_ICONS.get(direction)


def settings_section_icon(title: str) -> str | None:
    return _SETTINGS_SECTION_ICONS.get(title)


def main_tab_icon(title: str) -> str | None:
    return _MAIN_TAB_ICONS.get(title)


def solid_font(*, pixel_size: int = 14) -> QFont:
    font = QFont(FONT_FAMILY)
    font.setPixelSize(pixel_size)
    font.setWeight(FONT_WEIGHT)
    return font


def apply_solid_font(widget: QWidget, *, pixel_size: int | None = None) -> None:
    base = widget.font()
    size = pixel_size if pixel_size is not None else max(base.pixelSize(), 13)
    widget.setFont(solid_font(pixel_size=size))


def fa_rich_span(
    name: str,
    *,
    color: str | None = None,
    pixel_size: int | None = None,
) -> str:
    glyph = fa(name)
    if not glyph:
        return ""
    style = f'font-family:"{FONT_FAMILY}";font-weight:900;'
    if color:
        style += f"color:{color};"
    if pixel_size is not None:
        style += f"font-size:{pixel_size}px;"
    return f'<span style="{style}">{glyph}</span>'


def trend_rich_span(direction: str, *, color: str | None = None, pixel_size: int = 13) -> str:
    icon = trend_icon_name(direction)
    if not icon:
        return ""
    return fa_rich_span(icon, color=color, pixel_size=pixel_size)


@lru_cache(maxsize=256)
def fa_icon(
    name: str,
    size: int = 16,
    color_key: str = "",
    text_gap: int = 0,
) -> QIcon:
    glyph = fa(name)
    if not glyph:
        return QIcon()
    color = QColor(color_key) if color_key else QColor()
    if not color.isValid():
        app = QApplication.instance()
        if app is not None:
            color = app.palette().color(app.palette().ColorRole.ButtonText)
        else:
            color = QColor("#e8e8e8")
    font = solid_font(pixel_size=size)
    metrics = QFontMetrics(font)
    rect = metrics.boundingRect(glyph)
    gap = max(0, text_gap)
    icon_w = max(rect.width(), size)
    pm = QPixmap(icon_w + gap, max(rect.height(), size))
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setFont(font)
    painter.setPen(color)
    painter.drawText(
        0,
        0,
        icon_w,
        pm.height(),
        int(Qt.AlignmentFlag.AlignCenter),
        glyph,
    )
    painter.end()
    return QIcon(pm)


def set_button_fa_icon(
    button: QPushButton,
    name: str,
    *,
    text: str | None = None,
    icon_size: int = 15,
    icon_only: bool = False,
) -> None:
    has_text = text is not None and text != ""
    gap = BUTTON_ICON_TEXT_GAP if has_text else 0
    button.setIcon(fa_icon(name, size=icon_size, text_gap=gap))
    if has_text:
        button.setText(text)
    elif icon_only:
        button.setText("")
    button.setProperty("iconOnly", icon_only and not has_text)
    button.style().unpolish(button)
    button.style().polish(button)


def set_label_fa_icon(label: QLabel, name: str, *, pixel_size: int = 14) -> None:
    label.setText(fa(name))
    apply_solid_font(label, pixel_size=pixel_size)


def driver_mark_glyphs(pref: int | None, risky: bool) -> str:
    """Compact icon string for liked / disliked / risky marks."""
    parts: list[str] = []
    if pref == 1:
        parts.append(fa("thumbs-up"))
    elif pref == -1:
        parts.append(fa("thumbs-down"))
    if risky:
        parts.append(fa("triangle-exclamation"))
    return " ".join(parts)


def mark_item_font() -> QFont:
    return solid_font(pixel_size=13)


def clear_icon_cache() -> None:
    fa_icon.cache_clear()


def wire_main_tabs(tab_widget) -> None:
    """Add icons to the main application tab bar."""
    from PyQt6.QtWidgets import QTabWidget

    if not isinstance(tab_widget, QTabWidget):
        return
    for index in range(tab_widget.count()):
        icon_name = main_tab_icon(tab_widget.tabText(index))
        if icon_name:
            tab_widget.setTabIcon(index, fa_icon(icon_name, size=15))
