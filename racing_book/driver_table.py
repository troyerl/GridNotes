"""Driver table column layout and Safety Index cell styling."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

from .safety_index import (
    SafetyIndex,
    safety_tooltip,
    tier_qcolor,
    unknown_history_message,
)

PREF_DATA_ROLE = Qt.ItemDataRole.UserRole + 1
RISK_DATA_ROLE = Qt.ItemDataRole.UserRole + 2
SAFETY_TIER_DATA_ROLE = Qt.ItemDataRole.UserRole + 3

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


def make_table_item(value) -> QTableWidgetItem:
    item = QTableWidgetItem()
    if value is None:
        item.setText("N/A")
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
        item.setText("—")
        item.setData(Qt.ItemDataRole.EditRole, -1)
        item.setToolTip(unknown_history_message(safety.total_races, for_table=True))
        item.setForeground(tier_qcolor("unknown"))
    else:
        item.setText(f"{safety.score:.0f}")
        item.setData(Qt.ItemDataRole.EditRole, safety.score)
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
