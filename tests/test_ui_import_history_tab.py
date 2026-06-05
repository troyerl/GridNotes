"""Tests for Import history tab UI (search and pagination)."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)

from gridnotes.ui.import_history_tab import ImportHistoryTab
from gridnotes.ui.table_pagination import DEFAULT_PAGE_SIZE
from gridnotes.data.leagues import create_league, create_season, mark_session_league_race


def _seed_sessions(conn, count: int, *, start_id: int = 1000) -> None:
    for index in range(count):
        subsession_id = start_id + index
        conn.execute(
            """
            INSERT INTO race_results (
                cust_id, subsession_id, finish_position, incidents,
                series_name, race_at
            )
            VALUES (1, ?, 1, 0, ?, ?)
            """,
            (
                subsession_id,
                f"Series {subsession_id}",
                f"2026-01-01T12:00:{index:02d}Z",
            ),
        )
    conn.commit()


@pytest.fixture
def import_history_tab(file_db, monkeypatch, qapp):
    db_path, conn = file_db
    monkeypatch.setattr("gridnotes.ui.import_history_tab.get_db_path", lambda: db_path)
    tab = ImportHistoryTab()
    yield tab, conn
    tab.deleteLater()


def test_import_history_tab_defaults_to_page_size_50(import_history_tab):
    tab, _conn = import_history_tab
    assert tab._page_size == DEFAULT_PAGE_SIZE
    assert tab.pagination.page_size() == DEFAULT_PAGE_SIZE


def test_import_history_tab_empty_status(import_history_tab):
    tab, _conn = import_history_tab
    tab.refresh()
    assert tab.history_table.rowCount() == 0
    assert "No imported sessions yet" in tab.status_label.text()
    assert "No sessions match" in tab.pagination._summary.text()


def test_import_history_tab_shows_first_page(import_history_tab):
    tab, conn = import_history_tab
    _seed_sessions(conn, 55)
    tab.refresh()

    assert tab.history_table.rowCount() == 50
    assert tab.history_table.item(0, 0).text() == "1054"
    assert "Showing 1–50 of 55 sessions" in tab.pagination._summary.text()
    assert tab.pagination._btn_next.isEnabled()
    assert not tab.pagination._btn_prev.isEnabled()
    assert "55 imported session(s)" in tab.status_label.text()


def test_import_history_tab_next_page(import_history_tab):
    tab, conn = import_history_tab
    _seed_sessions(conn, 55)
    tab.refresh()
    tab._go_to_next_page()

    assert tab._page == 1
    assert tab.history_table.rowCount() == 5
    assert tab.history_table.item(0, 0).text() == "1004"
    assert "Showing 51–55 of 55 sessions" in tab.pagination._summary.text()
    assert tab.pagination._btn_prev.isEnabled()
    assert not tab.pagination._btn_next.isEnabled()


def test_import_history_tab_search_filters_and_resets_page(import_history_tab):
    tab, conn = import_history_tab
    _seed_sessions(conn, 55)
    tab._page = 1
    tab.search_input.setText("1005")
    tab.refresh()

    assert tab._page == 0
    assert tab.history_table.rowCount() == 1
    assert tab.history_table.item(0, 0).text() == "1005"
    assert "Filtered by session ID" in tab.status_label.text()
    assert "Showing 1–1 of 1 sessions" in tab.pagination._summary.text()


def test_import_history_tab_search_no_match(import_history_tab):
    tab, conn = import_history_tab
    _seed_sessions(conn, 3)
    tab.search_input.setText("99999999")
    tab.refresh()

    assert tab.history_table.rowCount() == 0
    assert "No imported sessions match session ID" in tab.status_label.text()


def test_import_history_tab_page_size_change_resets_page(import_history_tab):
    tab, conn = import_history_tab
    _seed_sessions(conn, 30)
    tab._page = 1
    tab._set_page_size(25)

    assert tab._page == 0
    assert tab._page_size == 25
    assert tab.history_table.rowCount() == 25
    assert "Showing 1–25 of 30 sessions" in tab.pagination._summary.text()


def test_import_history_tab_shows_league_tag(import_history_tab):
    tab, conn = import_history_tab
    conn.execute(
        """
        INSERT INTO race_results (
            cust_id, subsession_id, finish_position, incidents,
            series_name, race_at
        )
        VALUES (1, 4242, 1, 0, 'League Series', '2026-01-01T12:00:00Z')
        """
    )
    league_id = create_league(conn, "My League")
    season_id = create_season(conn, league_id, "2026 S1")
    mark_session_league_race(conn, 4242, league_id, season_id=season_id)
    conn.commit()

    tab.refresh()
    assert tab.history_table.rowCount() == 1
    assert tab.history_table.item(0, 2).text() == "My League · 2026 S1"
    tab.history_table.selectRow(0)
    assert tab.btn_clear_league.isEnabled()

    tab._clear_selected_league_race()
    tab.refresh()
    assert tab.history_table.item(0, 2).text() == "—"
    assert not tab.btn_clear_league.isEnabled()
