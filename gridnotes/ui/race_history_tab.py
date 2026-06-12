"""Per-driver race history tab."""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.timestamps import display_timezone_abbrev, format_last_seen
from ..data.db import connect_db, get_db_path
from ..data.driver_models import compare_race_finish_outcome, format_vs_you_outcome
from ..data.race_history import (
    count_driver_race_history,
    fetch_driver_race_history,
    fetch_drivers_with_race_history,
)
from .table_pagination import DEFAULT_PAGE_SIZE, TablePaginationBar


class RaceHistoryTab(QWidget):
    """Browse imported races for a selected driver."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = 0
        self._page_size = DEFAULT_PAGE_SIZE
        self._selected_cust_id: int | None = None
        self._player_cust_id_provider = lambda: None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Race history")
        title.setObjectName("appTitle")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)

        hint = QLabel(
            "Pick a driver to see every imported race in your book. "
            "When your iRacing identity is known, the You vs them column shows "
            "whether you finished ahead in each shared race (You won / You lost / Tie)."
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)
        picker_label = QLabel("Driver")
        picker_label.setObjectName("statInlineLabel")
        picker_row.addWidget(picker_label)
        self.driver_combo = QComboBox()
        self.driver_combo.setEditable(True)
        self.driver_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.driver_combo.setMinimumWidth(220)
        self.driver_combo.setMaximumWidth(400)
        self.driver_combo.currentIndexChanged.connect(self._on_driver_changed)
        picker_row.addWidget(self.driver_combo)
        picker_row.addStretch()
        layout.addLayout(picker_row)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by session ID or series…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_input, stretch=1)
        layout.addLayout(search_row)

        table_frame = QFrame()
        table_frame.setObjectName("panel")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(8)

        self.history_table = QTableWidget()
        self.history_table.setObjectName("raceHistoryTable")
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(
            [
                "Date",
                "Session ID",
                "Series",
                "Start",
                "Finish",
                "Incidents",
                "You vs them",
            ]
        )
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.history_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for col in (3, 4, 5, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        table_layout.addWidget(self.history_table, stretch=1)

        self.pagination = TablePaginationBar()
        self.pagination.set_page_size(self._page_size)
        self.pagination.previous_clicked.connect(self._go_to_previous_page)
        self.pagination.next_clicked.connect(self._go_to_next_page)
        self.pagination.page_size_changed.connect(self._set_page_size)
        table_layout.addWidget(self.pagination)

        layout.addWidget(table_frame, stretch=1)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("sectionHint")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

    def set_player_cust_id_provider(self, provider) -> None:
        self._player_cust_id_provider = provider

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._reload_driver_list()
        self.refresh()

    def refresh_icons(self) -> None:
        self.pagination.refresh_icons()

    def select_driver(self, cust_id: int | None) -> None:
        """Select a driver when they have imported race history in the book."""
        if cust_id is None:
            return
        index = self.driver_combo.findData(int(cust_id))
        if index < 0:
            return
        self.driver_combo.blockSignals(True)
        self.driver_combo.setCurrentIndex(index)
        self._selected_cust_id = int(cust_id)
        self.driver_combo.blockSignals(False)

    def _apply_driver_selection(self, index: int) -> None:
        if index < 0 or index >= self.driver_combo.count():
            self._selected_cust_id = None
            self.driver_combo.setCurrentIndex(-1)
            return
        cust_id = self.driver_combo.itemData(index)
        self._selected_cust_id = int(cust_id) if cust_id is not None else None
        if self.driver_combo.currentIndex() != index:
            self.driver_combo.setCurrentIndex(index)

    def _reload_driver_list(self) -> None:
        conn = connect_db(get_db_path())
        try:
            drivers = fetch_drivers_with_race_history(conn)
        finally:
            conn.close()

        preferred_id = self._selected_cust_id
        self.driver_combo.blockSignals(True)
        self.driver_combo.clear()
        for cust_id, name in drivers:
            label = name.strip() or f"Driver {cust_id}"
            self.driver_combo.addItem(f"{label}  (#{cust_id})", int(cust_id))
        completer = QCompleter([self.driver_combo.itemText(i) for i in range(self.driver_combo.count())])
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.driver_combo.setCompleter(completer)

        selected_index = -1
        if preferred_id is not None:
            selected_index = self.driver_combo.findData(int(preferred_id))
        if selected_index < 0 and self.driver_combo.count() > 0:
            selected_index = 0
        self._apply_driver_selection(selected_index)
        self.driver_combo.blockSignals(False)

    def _on_driver_changed(self, index: int) -> None:
        if index < 0:
            return
        cust_id = self.driver_combo.itemData(index)
        if cust_id is None:
            return
        self._selected_cust_id = int(cust_id)
        self._page = 0
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
        cust_id = self._selected_cust_id
        if cust_id is None:
            self.history_table.setRowCount(0)
            if self.driver_combo.count() <= 0:
                self.summary_label.setText(
                    "No imported race history yet. Import race JSON or use the Data API "
                    "to build your book first."
                )
            else:
                self.summary_label.setText("Select a driver to view race history.")
            self.pagination.update_state(
                page=0,
                page_count=1,
                total=0,
                start=0,
                end=0,
                item_label="races",
            )
            return

        series_query = self.search_input.text().strip() or None
        player_cust_id = self._player_cust_id_provider()
        conn = connect_db(get_db_path())
        try:
            total = count_driver_race_history(conn, cust_id, series_query=series_query)
            page_count = max(1, math.ceil(total / self._page_size)) if total else 1
            if self._page >= page_count:
                self._page = max(0, page_count - 1)
            offset = self._page * self._page_size
            entries = fetch_driver_race_history(
                conn,
                cust_id,
                player_cust_id=player_cust_id,
                limit=self._page_size,
                offset=offset,
                series_query=series_query,
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
            item_label="races",
        )
        driver_name = self.driver_combo.currentText().split("  (#")[0].strip()
        tz = display_timezone_abbrev()
        if total:
            self.summary_label.setText(
                f"{total} imported race{'s' if total != 1 else ''} for {driver_name}. "
                f"Times shown in {tz}."
            )
        else:
            self.summary_label.setText(
                f"No imported races match for {driver_name}."
            )

    def _populate_table(self, entries) -> None:
        tz = display_timezone_abbrev()
        self.history_table.setRowCount(len(entries))
        for row_idx, entry in enumerate(entries):
            date_text = format_last_seen(entry.race_at)
            if date_text and date_text != "—":
                date_text = f"{date_text} {tz}"
            values = [
                date_text or "—",
                str(entry.subsession_id) if entry.subsession_id else "—",
                entry.series_name or "—",
                self._format_position(entry.starting_position),
                self._format_position(entry.finish_position),
                str(entry.incidents) if entry.incidents is not None else "—",
                self._format_vs_you(entry),
            ]
            for col_idx, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row_idx, col_idx, item)

    @staticmethod
    def _format_position(value: int | None) -> str:
        if value is None:
            return "—"
        return f"P{int(value)}"

    @staticmethod
    def _format_vs_you(entry) -> str:
        if entry.player_finish is None:
            return "—"
        outcome = compare_race_finish_outcome(
            entry.player_finish,
            entry.player_reason_out_id,
            entry.finish_position,
            entry.reason_out_id,
        )
        return format_vs_you_outcome(outcome)
