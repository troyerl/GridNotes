"""Driver table column layout and Safety Index cell styling."""

from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
)

from .appearance import get_theme_id
from ..safety.safety_index import (
    SafetyIndex,
    tier_qcolor,
)
from ..safety.safety_trend import SafetyTrend, combined_safety_tooltip
from ..core.utils import sqlite_row_to_int
from ..data.leagues import compact_league_indicator
from ..data.driver_models import DriverTableRow
from .a11y import driver_mark_label
from .icons import current_icon_fg, driver_mark_glyphs, fa, mark_item_font
from .theme import table_row_color

PREF_DATA_ROLE = Qt.ItemDataRole.UserRole + 1
RISK_DATA_ROLE = Qt.ItemDataRole.UserRole + 2
SAFETY_TIER_DATA_ROLE = Qt.ItemDataRole.UserRole + 3
SAFETY_SORT_DATA_ROLE = Qt.ItemDataRole.UserRole + 4
SAFETY_TREND_DIRECTION_ROLE = Qt.ItemDataRole.UserRole + 5
REAL_NAME_DATA_ROLE = Qt.ItemDataRole.UserRole + 6
UNKNOWN_SAFETY_SORT = -1
EMPTY_CELL = "—"
_MISSING_NUMERIC = float("-inf")


def table_row_sort_key(
    row: tuple,
    column: int,
    *,
    head_to_head: tuple[int, int, int] | None = None,
) -> tuple:
    """Sort key for a driver SQL row and table column (matches table sort semantics)."""
    driver = DriverTableRow.from_sql_row(row)
    safety = driver.safety
    if column == COL_NAME:
        return (0, (driver.name or "").lower())
    if column == COL_MARK:
        label = driver_mark_label(driver.race_preference, safety.risky) or ""
        return (0, label.lower())
    if column == COL_LEAGUE:
        return (0, "")
    if column == COL_RACES:
        return (0, driver.total_races)
    if column == COL_VS_YOU:
        if head_to_head is None:
            return (1, 0)
        wins, losses, ties = head_to_head
        if wins + losses + ties <= 0:
            return (1, 0)
        return (0, wins - losses, wins)
    if column == COL_SAFETY:
        if safety.tier == "unknown":
            return (1, 0)
        return (0, safety.score)
    if column == COL_AVG_INC:
        return (0, driver.avg_inc if driver.avg_inc is not None else _MISSING_NUMERIC)
    if column == COL_AVG_FINISH:
        return (0, driver.avg_fin if driver.avg_fin is not None else _MISSING_NUMERIC)
    if column == COL_AVG_POS:
        return (0, driver.avg_pos_delta if driver.avg_pos_delta is not None else _MISSING_NUMERIC)
    if column == COL_DNFS:
        return (0, driver.dnf_total)
    if column == COL_LAST_SR:
        return (0, driver.last_sr if driver.last_sr is not None else _MISSING_NUMERIC)
    if column == COL_LAST_IR:
        return (0, driver.last_ir if driver.last_ir is not None else _MISSING_NUMERIC)
    if column == COL_SERIES:
        return (0, (driver.last_series or "").lower())
    if column == COL_DNF_BREAKDOWN:
        return (0, (driver.dnf_breakdown or "").lower())
    if column == COL_NOTE:
        return (0, 0 if driver.has_notes else 1)
    if column == COL_CUST_ID:
        return (0, driver.cust_id)
    return (0, "")


COL_NAME = 0
COL_MARK = 1
COL_LEAGUE = 2
COL_RACES = 3
COL_VS_YOU = 4
COL_SAFETY = 5
COL_AVG_INC = 6
COL_AVG_FINISH = 7
COL_AVG_POS = 8
COL_DNFS = 9
COL_LAST_SR = 10
COL_LAST_IR = 11
COL_SERIES = 12
COL_DNF_BREAKDOWN = 13
COL_NOTE = 14
COL_CUST_ID = 15

COLUMN_COUNT = 16
NOTE_HAS_TEXT = "Notes"

DRIVER_TABLE_HEADERS = [
    "Driver Name",
    "Mark",
    "League",
    "Races",
    "You vs them",
    "Safety Index",
    "Avg Incidents",
    "Avg Finish",
    "Avg +/- Pos",
    "DNFs",
    "Last SR",
    "Last iRating",
    "Last Series",
    "DNF Breakdown",
    "Note",
    "ID",
]

DEFAULT_DRIVER_TABLE_COLUMN_WIDTHS: dict[int, int] = {
    COL_NAME: 200,
    COL_MARK: 72,
    COL_LEAGUE: 72,
    COL_RACES: 64,
    COL_VS_YOU: 96,
    COL_SAFETY: 112,
    COL_AVG_INC: 100,
    COL_AVG_FINISH: 88,
    COL_AVG_POS: 92,
    COL_DNFS: 56,
    COL_LAST_SR: 72,
    COL_LAST_IR: 88,
    COL_SERIES: 180,
    COL_DNF_BREAKDOWN: 120,
    COL_NOTE: 56,
    COL_CUST_ID: 72,
}

TABLE_COLUMN_WIDTHS_KEY = "driver_table_column_widths"

ROW_BG_LIKED = QColor(42, 72, 52)
ROW_BG_LIKED_HOVER = QColor(54, 96, 66)
ROW_BG_LIKED_SELECTED = QColor(50, 88, 98)
ROW_BG_DISLIKED = QColor(72, 42, 42)
ROW_BG_DISLIKED_HOVER = QColor(96, 52, 52)
ROW_BG_DISLIKED_SELECTED = QColor(92, 52, 82)
ROW_BG_HOVER = QColor(45, 52, 64)
ROW_BG_RISKY = QColor(72, 62, 32)
ROW_BG_RISKY_HOVER = QColor(92, 80, 44)
ROW_BG_RISKY_SELECTED = QColor(78, 72, 58)
ROW_BG_ALTERNATE = QColor(30, 35, 43)
ROW_BG_BASE = QColor(26, 30, 36)
ROW_FG_HIGHLIGHT = QColor(232, 234, 237)
SELECTED_ROW_BG = QColor(45, 74, 122)
SELECTED_ROW_FG = QColor(255, 255, 255)


def configure_driver_table_theme(theme_id: str | None = None) -> None:
    """Update module-level row colors when the application theme changes."""
    global ROW_BG_LIKED, ROW_BG_LIKED_HOVER, ROW_BG_LIKED_SELECTED
    global ROW_BG_DISLIKED, ROW_BG_DISLIKED_HOVER, ROW_BG_DISLIKED_SELECTED
    global ROW_BG_HOVER, ROW_BG_RISKY, ROW_BG_RISKY_HOVER, ROW_BG_RISKY_SELECTED
    global ROW_BG_ALTERNATE, ROW_BG_BASE, ROW_FG_HIGHLIGHT
    global SELECTED_ROW_BG, SELECTED_ROW_FG

    tid = theme_id if theme_id is not None else get_theme_id()
    ROW_BG_LIKED = table_row_color(tid, "liked")
    ROW_BG_LIKED_HOVER = table_row_color(tid, "liked_hover")
    ROW_BG_LIKED_SELECTED = table_row_color(tid, "liked_selected")
    ROW_BG_DISLIKED = table_row_color(tid, "disliked")
    ROW_BG_DISLIKED_HOVER = table_row_color(tid, "disliked_hover")
    ROW_BG_DISLIKED_SELECTED = table_row_color(tid, "disliked_selected")
    ROW_BG_HOVER = table_row_color(tid, "hover")
    ROW_BG_RISKY = table_row_color(tid, "risky")
    ROW_BG_RISKY_HOVER = table_row_color(tid, "risky_hover")
    ROW_BG_RISKY_SELECTED = table_row_color(tid, "risky_selected")
    ROW_BG_ALTERNATE = table_row_color(tid, "alternate")
    ROW_BG_BASE = table_row_color(tid, "base")
    ROW_FG_HIGHLIGHT = table_row_color(tid, "highlight_fg")
    SELECTED_ROW_BG = table_row_color(tid, "selected_bg")
    SELECTED_ROW_FG = table_row_color(tid, "selected_fg")

TABLE_HOVER_ROW_PROPERTY = "hover_row"


def load_driver_table_column_widths() -> dict[int, int]:
    from ..data.db import get_db_path, get_setting

    raw = get_setting(TABLE_COLUMN_WIDTHS_KEY, db_name=get_db_path())
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    widths: dict[int, int] = {}
    for key, value in data.items():
        try:
            col = int(key)
            width = int(value)
        except (TypeError, ValueError):
            continue
        if col in DEFAULT_DRIVER_TABLE_COLUMN_WIDTHS and width >= 48:
            widths[col] = width
    return widths


def save_driver_table_column_widths(table: QTableWidget) -> None:
    from ..data.db import get_db_path, set_setting

    widths = {
        str(col): table.columnWidth(col)
        for col in range(COLUMN_COUNT)
        if not table.isColumnHidden(col)
    }
    set_setting(
        TABLE_COLUMN_WIDTHS_KEY, json.dumps(widths), db_name=get_db_path()
    )


def apply_driver_table_column_widths(
    table: QTableWidget, saved: dict[int, int] | None = None
) -> None:
    stored = load_driver_table_column_widths() if saved is None else saved
    header = table.horizontalHeader()
    for col, default_w in DEFAULT_DRIVER_TABLE_COLUMN_WIDTHS.items():
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(col, stored.get(col, default_w))


def configure_driver_table_columns(table: QTableWidget) -> None:
    """User-resizable columns; widths restored from settings when available."""
    table.horizontalHeader().setStretchLastSection(False)
    apply_driver_table_column_widths(table)


def _brush_color(value) -> QColor | None:
    if value is None:
        return None
    if isinstance(value, QColor):
        return value if value.isValid() else None
    if isinstance(value, QBrush):
        color = value.color()
        return color if color.isValid() else None
    return None


class DriverTableDelegate(QStyledItemDelegate):
    """Paint row backgrounds from preference/risk/hover/selection data."""

    def __init__(self, table: QTableWidget) -> None:
        super().__init__(table)
        self._table = table

    def _name_index(self, index):
        return index.siblingAtColumn(COL_NAME)

    def _row_pref(self, index) -> int | None:
        pref = sqlite_row_to_int(self._name_index(index).data(PREF_DATA_ROLE))
        return pref if pref in (1, -1) else None

    def _row_risky(self, index) -> bool:
        return bool(self._name_index(index).data(RISK_DATA_ROLE))

    def _hover_row(self) -> int | None:
        value = self._table.property(TABLE_HOVER_ROW_PROPERTY)
        try:
            row = int(value)
        except (TypeError, ValueError):
            return None
        return row if row >= 0 else None

    def _row_colors(self, option, index) -> tuple[QColor, QColor | None]:
        pref = self._row_pref(index)
        risky = self._row_risky(index)
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hover = self._hover_row() == index.row()

        if pref == 1:
            if is_selected:
                return ROW_BG_LIKED_SELECTED, ROW_FG_HIGHLIGHT
            if is_hover:
                return ROW_BG_LIKED_HOVER, ROW_FG_HIGHLIGHT
            return ROW_BG_LIKED, ROW_FG_HIGHLIGHT
        if pref == -1:
            if is_selected:
                return ROW_BG_DISLIKED_SELECTED, ROW_FG_HIGHLIGHT
            if is_hover:
                return ROW_BG_DISLIKED_HOVER, ROW_FG_HIGHLIGHT
            return ROW_BG_DISLIKED, ROW_FG_HIGHLIGHT
        if risky:
            if is_selected:
                return ROW_BG_RISKY_SELECTED, None
            if is_hover:
                return ROW_BG_RISKY_HOVER, None
            return ROW_BG_RISKY, None

        if is_hover:
            return ROW_BG_HOVER, None
        if is_selected:
            return SELECTED_ROW_BG, SELECTED_ROW_FG

        if index.row() % 2 == 1:
            return ROW_BG_ALTERNATE, None
        return ROW_BG_BASE, None

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)

        bg_color, default_fg = self._row_colors(opt, index)

        painter.save()
        painter.fillRect(opt.rect, bg_color)

        opt.state &= ~QStyle.StateFlag.State_Selected
        opt.backgroundBrush = QBrush(Qt.BrushStyle.NoBrush)

        custom_fg = _brush_color(index.data(Qt.ItemDataRole.ForegroundRole))
        if custom_fg is not None:
            opt.palette.setColor(opt.palette.ColorRole.Text, custom_fg)
        elif default_fg is not None:
            opt.palette.setColor(opt.palette.ColorRole.Text, default_fg)

        super().paint(painter, opt, index)
        painter.restore()


def refresh_driver_table_icon_colors(table: QTableWidget) -> None:
    """Re-apply icon glyph colors after a theme change."""
    color = QColor(current_icon_fg())
    for row_idx in range(table.rowCount()):
        for col_idx in (COL_MARK, COL_NOTE):
            item = table.item(row_idx, col_idx)
            if item is None:
                continue
            text = item.text()
            if not text or text == EMPTY_CELL:
                continue
            item.setForeground(color)
    table.viewport().update()


def configure_driver_table_widget(table: QTableWidget) -> None:
    """Shared table behavior: row selection with keyboard focus on the table widget."""
    table.setItemDelegate(DriverTableDelegate(table))
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.setShowGrid(False)
    table.setAlternatingRowColors(False)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.setProperty(TABLE_HOVER_ROW_PROPERTY, -1)


def set_driver_table_hover_row(table: QTableWidget, row_idx: int | None) -> None:
    table.setProperty(TABLE_HOVER_ROW_PROPERTY, -1 if row_idx is None else row_idx)
    table.viewport().update()


def refresh_driver_table_row(table: QTableWidget, row_idx: int) -> None:
    if row_idx < 0 or row_idx >= table.rowCount():
        return
    name_item = table.item(row_idx, COL_NAME)
    if name_item is not None:
        pref = sqlite_row_to_int(name_item.data(PREF_DATA_ROLE))
        pref = pref if pref in (1, -1) else None
        risky = bool(name_item.data(RISK_DATA_ROLE))
        table.setItem(row_idx, COL_MARK, make_mark_item(pref, risky))
    reapply_safety_cell_style(table, row_idx)
    table.viewport().update()


def make_table_item(value) -> QTableWidgetItem:
    item = QTableWidgetItem()
    if value is None:
        item.setText(EMPTY_CELL)
    else:
        if isinstance(value, (int, float)):
            item.setData(Qt.ItemDataRole.EditRole, value)
        item.setText(str(value))
    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
    return item


def make_mark_item(pref: int | None, risky: bool) -> QTableWidgetItem:
    label = driver_mark_label(pref, risky)
    glyphs = driver_mark_glyphs(pref, risky)
    item = QTableWidgetItem()
    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    if glyphs:
        item.setText(glyphs)
        item.setFont(mark_item_font())
        item.setForeground(QColor(current_icon_fg()))
        item.setToolTip(label or "")
    else:
        item.setText(EMPTY_CELL)
    return item


def make_league_item(full_label: str) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    short = compact_league_indicator(full_label)
    if short:
        item.setText(short)
        item.setToolTip(f"League racer: {full_label}")
    else:
        item.setText(EMPTY_CELL)
    return item


def make_note_item(has_note: bool) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setData(Qt.ItemDataRole.UserRole, 1 if has_note else 0)
    if has_note:
        item.setText(fa("note-sticky"))
        item.setFont(mark_item_font())
        item.setForeground(QColor(current_icon_fg()))
        item.setToolTip("Has scouting notes")
    return item


def make_safety_item(
    safety: SafetyIndex,
    trend: SafetyTrend | None = None,
) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setData(SAFETY_TIER_DATA_ROLE, safety.tier)

    if safety.tier == "unknown":
        item.setText("")
        item.setData(SAFETY_SORT_DATA_ROLE, UNKNOWN_SAFETY_SORT)
        item.setToolTip("")
        return item

    text = f"{safety.score:.0f}"
    if trend is not None and trend.arrow:
        text = f"{text} {trend.arrow}"
    item.setText(text)
    item.setData(Qt.ItemDataRole.EditRole, safety.score)
    item.setData(SAFETY_SORT_DATA_ROLE, safety.score)
    item.setToolTip(combined_safety_tooltip(safety, trend))
    trend_dir = trend.direction if trend is not None else ""
    item.setData(SAFETY_TREND_DIRECTION_ROLE, trend_dir)
    if trend is not None and trend.direction in ("improving", "worsening"):
        item.setForeground(QColor(trend.color_hex))
    else:
        item.setForeground(tier_qcolor(safety.tier))

    font = item.font()
    font.setBold(True)
    item.setFont(font)
    return item


def reapply_safety_cell_style(table: QTableWidget, row_idx: int) -> None:
    item = table.item(row_idx, COL_SAFETY)
    if item is None:
        return
    tier = item.data(SAFETY_TIER_DATA_ROLE)
    trend_dir = item.data(SAFETY_TREND_DIRECTION_ROLE) or ""
    if trend_dir in ("improving", "worsening"):
        trend = SafetyTrend(trend_dir, None, None, 0)
        item.setForeground(QColor(trend.color_hex))
    elif tier and tier != "unknown":
        item.setForeground(tier_qcolor(tier))
