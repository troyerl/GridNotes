"""Tests for Leagues tab UI."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)

from PyQt6.QtCore import Qt

from gridnotes.data.leagues import (
    add_members_to_season,
    create_league,
    create_season,
    ensure_driver_exists,
)
from gridnotes.ui.leagues_tab import LeaguesTab


def _seed_league_with_members(conn) -> tuple[int, int]:
    for cust_id, name in [(1, "Alice"), (2, "Bob"), (3, "Charlie")]:
        ensure_driver_exists(conn.cursor(), cust_id, name)
    league_id = create_league(conn, "Test League")
    season_id = create_season(conn, league_id, "2026 S1")
    add_members_to_season(conn, season_id, [(1, "Alice")])
    conn.commit()
    return league_id, season_id


@pytest.fixture
def leagues_tab(file_db, monkeypatch, qapp):
    db_path, conn = file_db
    monkeypatch.setattr("gridnotes.ui.leagues_tab.get_db_path", lambda: db_path)
    session_drivers = [(10, "Session Driver")]
    tab = LeaguesTab(session_drivers_provider=lambda: session_drivers)
    yield tab, conn
    tab.deleteLater()


def test_leagues_tab_empty_state(leagues_tab):
    tab, _conn = leagues_tab
    tab.refresh()
    assert tab.league_list.count() == 0
    assert tab.members_table.rowCount() == 0
    assert "Select a league and season" in tab.roster_title.text()
    assert tab.btn_add_session.text() == "Add current session (1)"


def test_leagues_tab_shows_roster(leagues_tab):
    tab, conn = leagues_tab
    _seed_league_with_members(conn)
    tab.refresh()

    assert tab.league_list.count() == 1
    assert tab.league_list.item(0).text() == "Test League"
    assert tab.season_list.count() == 1
    assert "2026 S1 (1)" in tab.season_list.item(0).text()
    assert tab.members_table.rowCount() == 1
    assert tab.members_table.item(0, 0).text() == "Alice"
    assert tab.members_table.item(0, 1).text() == "1"


def test_leagues_tab_candidate_checkboxes(leagues_tab):
    tab, conn = leagues_tab
    _seed_league_with_members(conn)
    tab.refresh()

    assert tab.candidates_table.rowCount() == 2
    assert tab.candidates_table.item(0, 1).text() == "Bob"
    assert tab.candidates_table.item(1, 1).text() == "Charlie"

    check_item = tab.candidates_table.item(0, 0)
    assert check_item.checkState() == Qt.CheckState.Unchecked
    check_item.setCheckState(Qt.CheckState.Checked)

    tab._add_selected_candidates()
    tab.refresh()

    names = {
        tab.members_table.item(row, 0).text()
        for row in range(tab.members_table.rowCount())
    }
    assert names == {"Alice", "Bob"}


def test_leagues_tab_add_current_session(leagues_tab):
    tab, conn = leagues_tab
    league_id = create_league(conn, "Live League")
    season_id = create_season(conn, league_id, "Tonight")
    conn.commit()
    tab.refresh()

    tab._add_current_session()
    tab.refresh()

    assert tab.members_table.rowCount() == 1
    assert tab.members_table.item(0, 0).text() == "Session Driver"
    assert tab.members_table.item(0, 1).text() == "10"
