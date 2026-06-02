"""Driver table column layout and Safety Index cell styling."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QTableWidgetItem

from .appearance import get_theme_id
from ..safety.safety_index import (
    SafetyIndex,
    safety_tooltip,
    tier_qcolor,
    unknown_history_message,
)
from .theme import table_row_color
from ..core.utils import sqlite_row_to_int

PREF_DATA_ROLE = Qt.ItemDataRole.UserRole + 1
RISK_DATA_ROLE = Qt.ItemDataRole.UserRole + 2
SAFETY_TIER_DATA_ROLE = Qt.ItemDataRole.UserRole + 3
SAFETY_SORT_DATA_ROLE = Qt.ItemDataRole.UserRole + 4
UNKNOWN_SAFETY_SORT = -1
EMPTY_CELL = "—"

COL_NAME = 0
COL_RACES = 1
COL_SAFETY = 2
COL_AVG_INC = 3
COL_AVG_FINISH = 4
COL_AVG_POS = 5
COL_DNFS = 6
COL_LAST_SR = 7
COL_LAST_IR = 8
COL_SERIES = 9
COL_DNF_BREAKDOWN = 10
COL_NOTE = 11
COL_CUST_ID = 12

COLUMN_COUNT = 13
NOTE_INDICATOR = "+"

DRIVER_TABLE_HEADERS = [
    "Driver Name",
    "Races",
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

RESIZE_TO_CONTENTS_COLUMNS = (
    COL_RACES,
    COL_SAFETY,
    COL_AVG_INC,
    COL_AVG_FINISH,
    COL_AVG_POS,
    COL_DNFS,
    COL_LAST_SR,
    COL_LAST_IR,
    COL_NOTE,
    COL_DNF_BREAKDOWN,
)

ROW_BG_LIKED = QColor(42, 72, 52)
ROW_BG_DISLIKED = QColor(72, 42, 42)
ROW_BG_HOVER = QColor(45, 52, 64)
ROW_BG_RISKY = QColor(72, 62, 32)
ROW_BG_ALTERNATE = QColor(30, 35, 43)
ROW_BG_BASE = QColor(26, 30, 36)
ROW_FG_HIGHLIGHT = QColor(232, 234, 237)
SELECTED_ROW_BG = QColor(45, 74, 122)
SELECTED_ROW_FG = QColor(255, 255, 255)


def configure_driver_table_theme(theme_id: str | None = None) -> None:
    """Update module-level row colors when the application theme changes."""
    global ROW_BG_LIKED, ROW_BG_DISLIKED, ROW_BG_HOVER, ROW_BG_RISKY
    global ROW_BG_ALTERNATE, ROW_BG_BASE, ROW_FG_HIGHLIGHT
    global SELECTED_ROW_BG, SELECTED_ROW_FG

    tid = theme_id if theme_id is not None else get_theme_id()
    ROW_BG_LIKED = table_row_color(tid, "liked")
    ROW_BG_DISLIKED = table_row_color(tid, "disliked")
    ROW_BG_HOVER = table_row_color(tid, "hover")
    ROW_BG_RISKY = table_row_color(tid, "risky")
    ROW_BG_ALTERNATE = table_row_color(tid, "alternate")
    ROW_BG_BASE = table_row_color(tid, "base")
    ROW_FG_HIGHLIGHT = table_row_color(tid, "highlight_fg")
    SELECTED_ROW_BG = table_row_color(tid, "selected_bg")
    SELECTED_ROW_FG = table_row_color(tid, "selected_fg")

TABLE_HOVER_ROW_PROPERTY = "hover_row"


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
        if pref == 1:
            return ROW_BG_LIKED, ROW_FG_HIGHLIGHT
        if pref == -1:
            return ROW_BG_DISLIKED, ROW_FG_HIGHLIGHT
        if self._row_risky(index):
            return ROW_BG_RISKY, None

        hover_row = self._hover_row()
        if hover_row is not None and index.row() == hover_row:
            return ROW_BG_HOVER, None

        if option.state & QStyle.StateFlag.State_Selected:
            return SELECTED_ROW_BG, SELECTED_ROW_FG

        if index.row() % 2 == 1:
            return ROW_BG_ALTERNATE, None
        return ROW_BG_BASE, None

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        opt.state &= ~QStyle.StateFlag.State_HasFocus

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


def configure_driver_table_widget(table: QTableWidget) -> None:
    """Shared table behavior: row-only selection look (no cell focus ring)."""
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


def make_note_item(has_note: bool) -> QTableWidgetItem:
    item = QTableWidgetItem(NOTE_INDICATOR if has_note else "")
    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setData(Qt.ItemDataRole.UserRole, 1 if has_note else 0)
    if has_note:
        item.setToolTip("Has scouting notes")
    return item


def make_safety_item(safety: SafetyIndex) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setData(SAFETY_TIER_DATA_ROLE, safety.tier)

    if safety.tier == "unknown":
        item.setText(EMPTY_CELL)
        item.setData(SAFETY_SORT_DATA_ROLE, UNKNOWN_SAFETY_SORT)
        item.setToolTip(unknown_history_message(safety.total_races, for_table=True))
        item.setForeground(tier_qcolor("unknown"))
    else:
        item.setText(f"{safety.score:.0f}")
        item.setData(Qt.ItemDataRole.EditRole, safety.score)
        item.setData(SAFETY_SORT_DATA_ROLE, safety.score)
        item.setToolTip(safety_tooltip(safety))
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
    if tier:
        item.setForeground(tier_qcolor(tier))
