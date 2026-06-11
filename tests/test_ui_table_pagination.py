"""Tests for table pagination bar."""

import pytest

pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)

from gridnotes.ui.table_pagination import DEFAULT_PAGE_SIZE, TablePaginationBar


def test_table_pagination_default_page_size(qapp):
    bar = TablePaginationBar()
    assert bar.page_size() == DEFAULT_PAGE_SIZE


def test_table_pagination_update_state_sessions_label(qapp):
    bar = TablePaginationBar()
    bar.update_state(
        page=0,
        page_count=3,
        total=120,
        start=1,
        end=50,
        item_label="sessions",
    )
    assert bar._summary.text() == "Showing 1–50 of 120 sessions"
    assert bar._page_label.text() == "1 / 3"
    assert not bar._btn_prev.isEnabled()
    assert bar._btn_next.isEnabled()


def test_table_pagination_empty_state(qapp):
    bar = TablePaginationBar()
    bar.update_state(
        page=0,
        page_count=1,
        total=0,
        start=0,
        end=0,
        item_label="sessions",
    )
    assert bar._summary.text() == "No sessions match the current filters."
    assert not bar._btn_prev.isEnabled()
    assert not bar._btn_next.isEnabled()
