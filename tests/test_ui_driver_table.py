"""Tests for gridnotes.ui.driver_table column width helpers."""

import json

import pytest

pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)

from PyQt6.QtWidgets import QTableWidget

from gridnotes.ui.driver_table import (
    COL_NAME,
    COL_SAFETY,
    DEFAULT_DRIVER_TABLE_COLUMN_WIDTHS,
    TABLE_COLUMN_WIDTHS_KEY,
    apply_driver_table_column_widths,
    load_driver_table_column_widths,
    make_league_item,
    save_driver_table_column_widths,
    table_row_sort_key,
)
from tests.conftest import make_driver_sql_row


def test_table_row_sort_key_name():
    row = make_driver_sql_row(name="Zebra")
    key_a = table_row_sort_key(row, COL_NAME)
    row_b = make_driver_sql_row(name="alpha")
    key_b = table_row_sort_key(row_b, COL_NAME)
    assert key_b < key_a


def test_make_league_item_uses_trophy_icon(qapp):
    item = make_league_item("Club A · 2026 S1")
    assert item.toolTip().startswith("League member:")
    assert item.text() != "Club A"

    empty = make_league_item("")
    assert empty.text() == "—"


def test_table_row_sort_key_safety_unknown():
    row = make_driver_sql_row(total_races=1)
    key = table_row_sort_key(row, COL_SAFETY)
    assert key[0] == 1  # unknown sorts after scored


def test_column_widths_round_trip(file_db, monkeypatch, qapp):
    db_path, _ = file_db
    monkeypatch.setattr("gridnotes.data.db.get_db_path", lambda: db_path)

    table = QTableWidget(0, len(DEFAULT_DRIVER_TABLE_COLUMN_WIDTHS))
    apply_driver_table_column_widths(table)
    table.setColumnWidth(COL_NAME, 250)
    save_driver_table_column_widths(table)

    from gridnotes.data.db import get_setting

    raw = get_setting(TABLE_COLUMN_WIDTHS_KEY, db_name=db_path)
    assert raw is not None
    data = json.loads(raw)
    assert str(COL_NAME) in data
    assert int(data[str(COL_NAME)]) == 250


def test_load_column_widths_invalid_ignored(file_db, monkeypatch):
    db_path, _ = file_db
    monkeypatch.setattr("gridnotes.data.db.get_db_path", lambda: db_path)
    from gridnotes.data.db import set_setting

    set_setting(TABLE_COLUMN_WIDTHS_KEY, "not-json", db_name=db_path)
    assert load_driver_table_column_widths() == {}
