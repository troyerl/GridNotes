"""Leagues tab — manage leagues, seasons, and bulk driver membership."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..data.db import connect_db, get_db_path
from .icons import set_button_fa_icon
from ..data.leagues import (
    DriverCandidate,
    add_members_to_season,
    create_league,
    create_season,
    delete_league,
    delete_season,
    fetch_driver_candidates,
    fetch_leagues,
    fetch_members,
    fetch_seasons,
    remove_members_from_season,
    rename_league,
)

SessionDriversProvider = Callable[[], list[tuple[int, str]]]


class LeaguesTab(QWidget):
    """Manage league rosters by season with bulk add/remove."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        session_drivers_provider: SessionDriversProvider | None = None,
    ) -> None:
        super().__init__(parent)
        self._session_drivers_provider = session_drivers_provider
        self._selected_league_id: int | None = None
        self._selected_season_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Leagues")
        title.setObjectName("appTitle")
        title.setStyleSheet("font-size: 18px;")
        root.addWidget(title)

        hint = QLabel(
            "Group drivers into leagues and seasons. Select a league and season, "
            "then add drivers in bulk from your scouting book or the current iRacing session."
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, stretch=1)

        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        league_label = QLabel("Leagues")
        league_label.setObjectName("statInlineLabel")
        left_layout.addWidget(league_label)

        self.league_list = QListWidget()
        self.league_list.currentItemChanged.connect(self._on_league_selected)
        left_layout.addWidget(self.league_list, stretch=1)

        league_btn_row = QHBoxLayout()
        self.btn_new_league = QPushButton("New league…")
        self.btn_new_league.clicked.connect(self._create_league)
        league_btn_row.addWidget(self.btn_new_league)
        self.btn_rename_league = QPushButton("Rename…")
        self.btn_rename_league.clicked.connect(self._rename_league)
        league_btn_row.addWidget(self.btn_rename_league)
        self.btn_delete_league = QPushButton("Delete")
        self.btn_delete_league.setObjectName("dangerBtn")
        self.btn_delete_league.clicked.connect(self._delete_league)
        league_btn_row.addWidget(self.btn_delete_league)
        left_layout.addLayout(league_btn_row)

        season_label = QLabel("Seasons")
        season_label.setObjectName("statInlineLabel")
        left_layout.addWidget(season_label)

        self.season_list = QListWidget()
        self.season_list.currentItemChanged.connect(self._on_season_selected)
        left_layout.addWidget(self.season_list, stretch=1)

        season_btn_row = QHBoxLayout()
        self.btn_new_season = QPushButton("New season…")
        self.btn_new_season.clicked.connect(self._create_season)
        season_btn_row.addWidget(self.btn_new_season)
        self.btn_delete_season = QPushButton("Delete")
        self.btn_delete_season.setObjectName("dangerBtn")
        self.btn_delete_season.clicked.connect(self._delete_season)
        season_btn_row.addWidget(self.btn_delete_season)
        left_layout.addLayout(season_btn_row)

        splitter.addWidget(left)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        self.roster_title = QLabel("Select a league and season")
        self.roster_title.setObjectName("appTitle")
        self.roster_title.setStyleSheet("font-size: 16px;")
        right_layout.addWidget(self.roster_title)

        member_toolbar = QHBoxLayout()
        self.btn_add_session = QPushButton("Add current session")
        self.btn_add_session.setObjectName("primaryBtn")
        self.btn_add_session.clicked.connect(self._add_current_session)
        member_toolbar.addWidget(self.btn_add_session)
        self.btn_remove_members = QPushButton("Remove selected")
        self.btn_remove_members.setObjectName("dangerBtn")
        self.btn_remove_members.clicked.connect(self._remove_selected_members)
        member_toolbar.addWidget(self.btn_remove_members)
        member_toolbar.addStretch()
        right_layout.addLayout(member_toolbar)

        self.members_table = QTableWidget()
        self.members_table.setObjectName("leagueMembersTable")
        self.members_table.setColumnCount(2)
        self.members_table.setHorizontalHeaderLabels(["Driver", "ID"])
        self._configure_table(self.members_table, multi_select=True)
        right_layout.addWidget(self.members_table, stretch=2)

        add_label = QLabel("Add from scouting book")
        add_label.setObjectName("statInlineLabel")
        right_layout.addWidget(add_label)

        candidate_toolbar = QHBoxLayout()
        self.candidate_search = QLineEdit()
        self.candidate_search.setPlaceholderText("Search drivers to add…")
        self.candidate_search.setClearButtonEnabled(True)
        self.candidate_search.textChanged.connect(self._refresh_candidates)
        candidate_toolbar.addWidget(self.candidate_search, stretch=1)
        self.btn_select_all_candidates = QPushButton("Select all shown")
        self.btn_select_all_candidates.clicked.connect(self._select_all_candidates)
        candidate_toolbar.addWidget(self.btn_select_all_candidates)
        self.btn_add_candidates = QPushButton("Add selected")
        self.btn_add_candidates.setObjectName("primaryBtn")
        self.btn_add_candidates.clicked.connect(self._add_selected_candidates)
        candidate_toolbar.addWidget(self.btn_add_candidates)
        right_layout.addLayout(candidate_toolbar)

        self.candidates_table = QTableWidget()
        self.candidates_table.setObjectName("leagueCandidatesTable")
        self.candidates_table.setColumnCount(3)
        self.candidates_table.setHorizontalHeaderLabels(["", "Driver", "ID"])
        self.candidates_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.candidates_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.candidates_table.setAlternatingRowColors(True)
        self.candidates_table.verticalHeader().setVisible(False)
        cand_header = self.candidates_table.horizontalHeader()
        cand_header.setStretchLastSection(False)
        cand_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cand_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cand_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        right_layout.addWidget(self.candidates_table, stretch=2)

        self.status_label = QLabel("")
        self.status_label.setObjectName("sectionHint")
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([280, 720])

        self._update_actions_enabled()
        self._apply_icons()
        self.refresh()

    def _apply_icons(self) -> None:
        set_button_fa_icon(self.btn_new_league, "plus", text="New league…")
        set_button_fa_icon(self.btn_rename_league, "pen-to-square", text="Rename…")
        set_button_fa_icon(self.btn_delete_league, "trash", text="Delete")
        set_button_fa_icon(self.btn_new_season, "plus", text="New season…")
        set_button_fa_icon(self.btn_delete_season, "trash", text="Delete")
        set_button_fa_icon(
            self.btn_add_session, "user-plus", text="Add current session"
        )
        set_button_fa_icon(self.btn_remove_members, "trash", text="Remove selected")
        set_button_fa_icon(
            self.btn_select_all_candidates, "table-cells", text="Select all shown"
        )
        set_button_fa_icon(self.btn_add_candidates, "plus", text="Add selected")

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    @staticmethod
    def _configure_table(table: QTableWidget, *, multi_select: bool) -> None:
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        if multi_select:
            table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            table.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
        else:
            table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            table.setSelectionMode(
                QAbstractItemView.SelectionMode.NoSelection
            )
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        if table.columnCount() > 1:
            header.setSectionResizeMode(
                table.columnCount() - 1,
                QHeaderView.ResizeMode.ResizeToContents,
            )

    def refresh(self) -> None:
        self._reload_leagues()
        self._reload_seasons()
        self._reload_members()
        self._refresh_candidates()
        self._update_session_button_label()

    def _db_conn(self):
        return connect_db(get_db_path())

    def _reload_leagues(self) -> None:
        selected_id = self._selected_league_id
        self.league_list.blockSignals(True)
        self.league_list.clear()
        conn = self._db_conn()
        try:
            leagues = fetch_leagues(conn)
        finally:
            conn.close()

        restore_row = 0
        for index, league in enumerate(leagues):
            item = QListWidgetItem(league.name)
            item.setData(Qt.ItemDataRole.UserRole, league.id)
            self.league_list.addItem(item)
            if league.id == selected_id:
                restore_row = index
        self.league_list.blockSignals(False)

        if leagues:
            self.league_list.setCurrentRow(restore_row)
            item = self.league_list.currentItem()
            self._selected_league_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        else:
            self._selected_league_id = None

    def _reload_seasons(self) -> None:
        selected_id = self._selected_season_id
        self.season_list.blockSignals(True)
        self.season_list.clear()
        if self._selected_league_id is None:
            self.season_list.blockSignals(False)
            self._selected_season_id = None
            return

        conn = self._db_conn()
        try:
            seasons = fetch_seasons(conn, self._selected_league_id)
        finally:
            conn.close()

        restore_row = 0
        for index, season in enumerate(seasons):
            label = f"{season.name} ({season.member_count})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, season.id)
            self.season_list.addItem(item)
            if season.id == selected_id:
                restore_row = index
        self.season_list.blockSignals(False)

        if seasons:
            self.season_list.setCurrentRow(restore_row)
            item = self.season_list.currentItem()
            self._selected_season_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        else:
            self._selected_season_id = None

    def _reload_members(self) -> None:
        self.members_table.setRowCount(0)
        league_name = ""
        season_name = ""
        league_item = self.league_list.currentItem()
        season_item = self.season_list.currentItem()
        if league_item is not None:
            league_name = league_item.text()
        if season_item is not None:
            season_name = season_item.text().split(" (", 1)[0]

        if self._selected_season_id is None:
            self.roster_title.setText("Select a league and season")
            self.status_label.setText(
                "Create a league and season, then add drivers from your book or the current session."
            )
            self._update_actions_enabled()
            return

        self.roster_title.setText(f"{league_name} · {season_name}")

        conn = self._db_conn()
        try:
            members = fetch_members(conn, self._selected_season_id)
        finally:
            conn.close()

        self.members_table.setRowCount(len(members))
        for row_idx, member in enumerate(members):
            name_item = QTableWidgetItem(member.driver_name)
            id_item = QTableWidgetItem(str(member.cust_id))
            id_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            name_item.setData(Qt.ItemDataRole.UserRole, member.cust_id)
            self.members_table.setItem(row_idx, 0, name_item)
            self.members_table.setItem(row_idx, 1, id_item)

        self.status_label.setText(
            f"{len(members)} driver(s) in this season."
            if members
            else "No drivers in this season yet."
        )
        self._update_actions_enabled()

    def _refresh_candidates(self) -> None:
        self.candidates_table.setRowCount(0)
        if self._selected_season_id is None:
            return

        search = self.candidate_search.text().strip()
        conn = self._db_conn()
        try:
            candidates = fetch_driver_candidates(
                conn,
                self._selected_season_id,
                search=search,
                limit=200,
            )
        finally:
            conn.close()

        self.candidates_table.setRowCount(len(candidates))
        for row_idx, candidate in enumerate(candidates):
            self._set_candidate_row(row_idx, candidate, checked=False)

    def _set_candidate_row(
        self,
        row_idx: int,
        candidate: DriverCandidate,
        *,
        checked: bool,
    ) -> None:
        check_item = QTableWidgetItem()
        check_item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsSelectable
        )
        check_item.setCheckState(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        check_item.setData(Qt.ItemDataRole.UserRole, candidate.cust_id)
        name_item = QTableWidgetItem(candidate.driver_name)
        id_item = QTableWidgetItem(str(candidate.cust_id))
        id_item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.candidates_table.setItem(row_idx, 0, check_item)
        self.candidates_table.setItem(row_idx, 1, name_item)
        self.candidates_table.setItem(row_idx, 2, id_item)

    def _update_session_button_label(self) -> None:
        count = 0
        if self._session_drivers_provider is not None:
            count = len(self._session_drivers_provider())
        self.btn_add_session.setText(
            f"Add current session ({count})" if count else "Add current session"
        )

    def _update_actions_enabled(self) -> None:
        has_league = self._selected_league_id is not None
        has_season = self._selected_season_id is not None
        self.btn_rename_league.setEnabled(has_league)
        self.btn_delete_league.setEnabled(has_league)
        self.btn_new_season.setEnabled(has_league)
        self.btn_delete_season.setEnabled(has_season)
        session_count = (
            len(self._session_drivers_provider())
            if self._session_drivers_provider is not None
            else 0
        )
        self.btn_add_session.setEnabled(has_season and session_count > 0)
        self.btn_remove_members.setEnabled(has_season)
        self.btn_add_candidates.setEnabled(has_season)
        self.btn_select_all_candidates.setEnabled(has_season)
        self.candidate_search.setEnabled(has_season)

    def _on_league_selected(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        self._selected_league_id = (
            current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        )
        self._selected_season_id = None
        self._reload_seasons()
        self._reload_members()
        self._refresh_candidates()

    def _on_season_selected(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        self._selected_season_id = (
            current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        )
        self._reload_members()
        self._refresh_candidates()
        self._update_actions_enabled()

    def _create_league(self) -> None:
        name, ok = QInputDialog.getText(self, "New league", "League name:")
        if not ok:
            return
        conn = self._db_conn()
        try:
            league_id = create_league(conn, name)
            conn.commit()
        except Exception as exc:
            QMessageBox.warning(self, "Could not create league", str(exc))
            return
        finally:
            conn.close()
        self._selected_league_id = league_id
        self._selected_season_id = None
        self.refresh()

    def _rename_league(self) -> None:
        if self._selected_league_id is None:
            return
        current = self.league_list.currentItem()
        current_name = current.text() if current else ""
        name, ok = QInputDialog.getText(
            self,
            "Rename league",
            "League name:",
            text=current_name,
        )
        if not ok:
            return
        conn = self._db_conn()
        try:
            rename_league(conn, self._selected_league_id, name)
            conn.commit()
        except Exception as exc:
            QMessageBox.warning(self, "Could not rename league", str(exc))
            return
        finally:
            conn.close()
        self.refresh()

    def _delete_league(self) -> None:
        if self._selected_league_id is None:
            return
        league_name = self.league_list.currentItem().text()
        confirm = QMessageBox.question(
            self,
            "Delete league?",
            f"Delete “{league_name}” and all of its seasons and memberships?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        conn = self._db_conn()
        try:
            delete_league(conn, self._selected_league_id)
            conn.commit()
        finally:
            conn.close()
        self._selected_league_id = None
        self._selected_season_id = None
        self.refresh()

    def _create_season(self) -> None:
        if self._selected_league_id is None:
            return
        name, ok = QInputDialog.getText(self, "New season", "Season name:")
        if not ok:
            return
        conn = self._db_conn()
        try:
            season_id = create_season(conn, self._selected_league_id, name)
            conn.commit()
        except Exception as exc:
            QMessageBox.warning(self, "Could not create season", str(exc))
            return
        finally:
            conn.close()
        self._selected_season_id = season_id
        self.refresh()

    def _delete_season(self) -> None:
        if self._selected_season_id is None:
            return
        season_item = self.season_list.currentItem()
        season_name = season_item.text().split(" (", 1)[0] if season_item else ""
        confirm = QMessageBox.question(
            self,
            "Delete season?",
            f"Delete season “{season_name}” and remove its driver memberships?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        conn = self._db_conn()
        try:
            delete_season(conn, self._selected_season_id)
            conn.commit()
        finally:
            conn.close()
        self._selected_season_id = None
        self.refresh()

    def _add_current_session(self) -> None:
        if self._selected_season_id is None or self._session_drivers_provider is None:
            return
        drivers = self._session_drivers_provider()
        if not drivers:
            return
        conn = self._db_conn()
        try:
            added = add_members_to_season(conn, self._selected_season_id, drivers)
            conn.commit()
        finally:
            conn.close()
        skipped = len(drivers) - added
        if added:
            msg = f"Added {added} driver(s) from the current session."
            if skipped:
                msg += f" {skipped} were already in this season."
            self.status_label.setText(msg)
        else:
            self.status_label.setText("All current session drivers are already in this season.")
        self.refresh()

    def _selected_member_ids(self) -> list[int]:
        cust_ids: list[int] = []
        for item in self.members_table.selectedItems():
            if item.column() != 0:
                continue
            cust_id = item.data(Qt.ItemDataRole.UserRole)
            if cust_id is not None:
                cust_ids.append(int(cust_id))
        return sorted(set(cust_ids))

    def _remove_selected_members(self) -> None:
        if self._selected_season_id is None:
            return
        cust_ids = self._selected_member_ids()
        if not cust_ids:
            QMessageBox.information(
                self,
                "Remove drivers",
                "Select one or more drivers in the roster table first.",
            )
            return
        conn = self._db_conn()
        try:
            removed = remove_members_from_season(
                conn, self._selected_season_id, cust_ids
            )
            conn.commit()
        finally:
            conn.close()
        self.status_label.setText(f"Removed {removed} driver(s) from this season.")
        self.refresh()

    def _select_all_candidates(self) -> None:
        for row in range(self.candidates_table.rowCount()):
            item = self.candidates_table.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked)

    def _checked_candidate_ids(self) -> list[tuple[int, str]]:
        drivers: list[tuple[int, str]] = []
        for row in range(self.candidates_table.rowCount()):
            check_item = self.candidates_table.item(row, 0)
            name_item = self.candidates_table.item(row, 1)
            if check_item is None or name_item is None:
                continue
            if check_item.checkState() != Qt.CheckState.Checked:
                continue
            cust_id = int(check_item.data(Qt.ItemDataRole.UserRole))
            drivers.append((cust_id, name_item.text()))
        return drivers

    def _add_selected_candidates(self) -> None:
        if self._selected_season_id is None:
            return
        drivers = self._checked_candidate_ids()
        if not drivers:
            QMessageBox.information(
                self,
                "Add drivers",
                "Check one or more drivers in the list below first.",
            )
            return
        conn = self._db_conn()
        try:
            added = add_members_to_season(conn, self._selected_season_id, drivers)
            conn.commit()
        finally:
            conn.close()
        self.status_label.setText(f"Added {added} driver(s) to this season.")
        self.refresh()
