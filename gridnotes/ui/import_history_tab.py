"""Import history tab — list of previously imported iRacing subsessions."""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.timestamps import format_last_seen
from ..data.db import connect_db, get_db_path
from ..data.import_history import count_import_history, fetch_import_history
from .icons import set_button_fa_icon
from ..data.leagues import (
    clear_session_league_race,
    fetch_leagues,
    fetch_seasons,
    mark_session_league_race,
)
from .table_pagination import DEFAULT_PAGE_SIZE, TablePaginationBar


class MarkLeagueRaceDialog(QDialog):
    """Pick a league (and optional season) for an imported session."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        subsession_id: int,
        session_name: str,
        current_league_id: int | None = None,
        current_season_id: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mark as league race")
        self.setModal(True)
        self._selected_league_id: int | None = None
        self._selected_season_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        intro = QLabel(
            f"Tag subsession {subsession_id} ({session_name}) as a league race "
            "and add its drivers to the season roster."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.league_combo = QComboBox()
        self.season_combo = QComboBox()
        form.addRow("League", self.league_combo)
        form.addRow("Season", self.season_combo)
        layout.addLayout(form)

        self.league_combo.currentIndexChanged.connect(self._on_league_changed)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_leagues(current_league_id, current_season_id)

    def _load_leagues(
        self,
        current_league_id: int | None,
        current_season_id: int | None,
    ) -> None:
        conn = connect_db(get_db_path())
        try:
            leagues = fetch_leagues(conn)
        finally:
            conn.close()

        self.league_combo.blockSignals(True)
        self.league_combo.clear()
        if not leagues:
            self.league_combo.addItem("Create a league on the Leagues tab first", None)
            self.league_combo.setEnabled(False)
            self.season_combo.setEnabled(False)
            self.league_combo.blockSignals(False)
            return

        selected_index = 0
        for index, league in enumerate(leagues):
            self.league_combo.addItem(league.name, league.id)
            if league.id == current_league_id:
                selected_index = index
        self.league_combo.setCurrentIndex(selected_index)
        self.league_combo.blockSignals(False)
        self._reload_seasons(current_season_id)

    def _on_league_changed(self, _index: int) -> None:
        self._reload_seasons(None)

    def _reload_seasons(self, current_season_id: int | None) -> None:
        self.season_combo.blockSignals(True)
        self.season_combo.clear()

        league_id = self.league_combo.currentData()
        if league_id is None:
            self.season_combo.setEnabled(False)
            self.season_combo.blockSignals(False)
            return

        conn = connect_db(get_db_path())
        try:
            seasons = fetch_seasons(conn, int(league_id))
        finally:
            conn.close()

        if not seasons:
            self.season_combo.addItem("Create a season on the Leagues tab first", None)
            self.season_combo.setEnabled(False)
            self.season_combo.blockSignals(False)
            return

        self.season_combo.setEnabled(True)
        selected_index = 0
        for index, season in enumerate(seasons):
            self.season_combo.addItem(season.name, season.id)
            if season.id == current_season_id:
                selected_index = index
        self.season_combo.setCurrentIndex(selected_index)
        self.season_combo.blockSignals(False)

    def _accept(self) -> None:
        league_id = self.league_combo.currentData()
        if league_id is None:
            QMessageBox.information(
                self,
                "No league selected",
                "Create a league on the Leagues tab, then try again.",
            )
            return
        season_id = self.season_combo.currentData()
        if season_id is None:
            QMessageBox.information(
                self,
                "No season selected",
                "Create a season on the Leagues tab, then try again.",
            )
            return
        self._selected_league_id = int(league_id)
        self._selected_season_id = int(season_id)
        self.accept()

    @property
    def league_id(self) -> int | None:
        return self._selected_league_id

    @property
    def season_id(self) -> int | None:
        return self._selected_season_id


class ImportHistoryTab(QWidget):
    """Top-level tab listing imported subsession IDs and session names."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = 0
        self._page_size = DEFAULT_PAGE_SIZE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Import history")
        title.setObjectName("appTitle")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)

        hint = QLabel(
            "Sessions already imported from iRacing JSON or the Data API. "
            "Use the subsession ID to check whether a race is in your book "
            "before importing again, or mark a session as a league race."
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by session ID…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_input, stretch=1)
        layout.addLayout(search_row)

        table_frame = QFrame()
        table_frame.setObjectName("panel")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(8)

        action_row = QHBoxLayout()
        self.btn_mark_league = QPushButton("Mark as league race…")
        self.btn_mark_league.setObjectName("primaryBtn")
        self.btn_mark_league.clicked.connect(self._mark_selected_league_race)
        self.btn_mark_league.setEnabled(False)
        action_row.addWidget(self.btn_mark_league)
        self.btn_clear_league = QPushButton("Clear league tag")
        self.btn_clear_league.clicked.connect(self._clear_selected_league_race)
        self.btn_clear_league.setEnabled(False)
        action_row.addWidget(self.btn_clear_league)
        action_row.addStretch()
        table_layout.addLayout(action_row)

        self.history_table = QTableWidget()
        self.history_table.setObjectName("importHistoryTable")
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(
            ["Session ID", "Session", "League", "Imported"]
        )
        self.history_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.history_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.history_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setWordWrap(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.itemSelectionChanged.connect(self._update_action_buttons)
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table_layout.addWidget(self.history_table, stretch=1)

        self.pagination = TablePaginationBar()
        self.pagination.set_page_size(self._page_size)
        self.pagination.previous_clicked.connect(self._go_to_previous_page)
        self.pagination.next_clicked.connect(self._go_to_next_page)
        self.pagination.page_size_changed.connect(self._set_page_size)
        table_layout.addWidget(self.pagination)

        layout.addWidget(table_frame, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("sectionHint")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self._apply_icons()

    def _apply_icons(self) -> None:
        set_button_fa_icon(self.btn_mark_league, "tag", text="Mark as league race…")
        set_button_fa_icon(self.btn_clear_league, "eraser", text="Clear league tag")

    def refresh_icons(self) -> None:
        self._apply_icons()
        self.pagination.refresh_icons()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    def _on_search_changed(self) -> None:
        self._page = 0
        self.refresh()

    def _set_page_size(self, size: int) -> None:
        self._page_size = max(1, size)
        self._page = 0
        self.refresh()

    def _go_to_previous_page(self) -> None:
        if self._page <= 0:
            return
        self._page -= 1
        self.refresh()

    def _go_to_next_page(self) -> None:
        self._page += 1
        self.refresh()

    def refresh(self) -> None:
        session_id_query = self.search_input.text().strip()
        conn = connect_db(get_db_path())
        try:
            total = count_import_history(
                conn,
                session_id_query=session_id_query or None,
            )
            page_count = max(1, math.ceil(total / self._page_size)) if total else 1
            if self._page >= page_count:
                self._page = max(0, page_count - 1)
            offset = self._page * self._page_size
            entries = fetch_import_history(
                conn,
                limit=self._page_size,
                offset=offset,
                session_id_query=session_id_query or None,
            )
        finally:
            conn.close()

        self._populate_table(entries)
        if total > 0:
            start = offset + 1
            end = offset + len(entries)
        else:
            start = 0
            end = 0
        self.pagination.update_state(
            page=self._page,
            page_count=page_count,
            total=total,
            start=start,
            end=end,
            item_label="sessions",
        )
        self._update_status(total, session_id_query)
        self._update_action_buttons()

    def _populate_table(self, entries) -> None:
        self.history_table.setRowCount(len(entries))
        for row_idx, entry in enumerate(entries):
            id_item = QTableWidgetItem(str(entry.subsession_id))
            id_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            id_item.setData(Qt.ItemDataRole.UserRole, entry.subsession_id)
            id_item.setData(Qt.ItemDataRole.UserRole + 1, entry.league_id)

            name_item = QTableWidgetItem(entry.session_name)
            name_item.setData(Qt.ItemDataRole.UserRole, entry.subsession_id)

            league_text = self._format_league_label(entry.league_name, entry.season_name)
            league_item = QTableWidgetItem(league_text)
            league_item.setData(Qt.ItemDataRole.UserRole, entry.subsession_id)

            imported_text = format_last_seen(entry.race_at)
            if imported_text == "N/A":
                imported_text = "—"
            imported_item = QTableWidgetItem(imported_text)
            imported_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            tooltip = (
                f"Subsession {entry.subsession_id}\n"
                f"{entry.session_name}\n"
                f"{entry.driver_count} driver(s) in this import"
            )
            if entry.league_name:
                tooltip += f"\nLeague: {league_text}"
            id_item.setToolTip(tooltip)
            name_item.setToolTip(tooltip)
            league_item.setToolTip(tooltip)
            imported_item.setToolTip(tooltip)
            self.history_table.setItem(row_idx, 0, id_item)
            self.history_table.setItem(row_idx, 1, name_item)
            self.history_table.setItem(row_idx, 2, league_item)
            self.history_table.setItem(row_idx, 3, imported_item)

    @staticmethod
    def _format_league_label(
        league_name: str | None,
        season_name: str | None,
    ) -> str:
        if not league_name:
            return "—"
        if season_name:
            return f"{league_name} · {season_name}"
        return league_name

    def _selected_entry(self) -> tuple[int, str, int | None] | None:
        row = self.history_table.currentRow()
        if row < 0:
            return None
        id_item = self.history_table.item(row, 0)
        name_item = self.history_table.item(row, 1)
        if id_item is None or name_item is None:
            return None
        subsession_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        league_id = id_item.data(Qt.ItemDataRole.UserRole + 1)
        league_id = int(league_id) if league_id is not None else None
        return subsession_id, name_item.text(), league_id

    def _update_action_buttons(self) -> None:
        selected = self._selected_entry()
        has_selection = selected is not None
        has_league_tag = bool(selected and selected[2] is not None)
        self.btn_mark_league.setEnabled(has_selection)
        self.btn_clear_league.setEnabled(has_selection and has_league_tag)

    def _mark_selected_league_race(self) -> None:
        selected = self._selected_entry()
        if selected is None:
            return
        subsession_id, session_name, league_id = selected

        current_season_id = None
        if league_id is not None:
            conn = connect_db(get_db_path())
            try:
                row = conn.execute(
                    "SELECT season_id FROM league_race_sessions WHERE subsession_id = ?",
                    (subsession_id,),
                ).fetchone()
                if row is not None and row[0] is not None:
                    current_season_id = int(row[0])
            finally:
                conn.close()

        dialog = MarkLeagueRaceDialog(
            self,
            subsession_id=subsession_id,
            session_name=session_name,
            current_league_id=league_id,
            current_season_id=current_season_id,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.league_id is None:
            return

        conn = connect_db(get_db_path())
        try:
            result = mark_session_league_race(
                conn,
                subsession_id,
                dialog.league_id,
                season_id=dialog.season_id,
            )
            conn.commit()
        except Exception as exc:
            QMessageBox.warning(self, "Could not mark session", str(exc))
            return
        finally:
            conn.close()

        self.status_label.setText(self._format_mark_result_message(subsession_id, result))
        self.refresh()

    @staticmethod
    def _format_mark_result_message(
        subsession_id: int,
        result,
    ) -> str:
        msg = f"Subsession {subsession_id} marked as a league race."
        if result.drivers_in_session == 0:
            msg += " No drivers were found in this import."
            return msg
        if result.drivers_added:
            msg += f" Added {result.drivers_added} driver(s) to the season roster."
        already = result.drivers_in_session - result.drivers_added
        if already:
            msg += f" {already} were already in the season."
        return msg

    def _clear_selected_league_race(self) -> None:
        selected = self._selected_entry()
        if selected is None:
            return
        subsession_id = selected[0]
        conn = connect_db(get_db_path())
        try:
            cleared = clear_session_league_race(conn, subsession_id)
            conn.commit()
        finally:
            conn.close()
        if cleared:
            self.status_label.setText(
                f"League tag removed from subsession {subsession_id}."
            )
        self.refresh()

    def _update_status(self, total: int, session_id_query: str) -> None:
        if total == 0 and not session_id_query:
            self.status_label.setText(
                "No imported sessions yet. Use Import race JSON on the Drivers tab."
            )
            return

        if total == 0 and session_id_query:
            self.status_label.setText(
                f"No imported sessions match session ID “{session_id_query}”."
            )
            return

        if session_id_query:
            self.status_label.setText(
                f"Filtered by session ID “{session_id_query}”."
            )
            return

        self.status_label.setText(f"{total} imported session(s) in your book.")
