"""Import history tab — list of previously imported iRacing subsessions."""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
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

from ..core.timestamps import format_last_seen
from ..data.db import connect_db, get_db_path
from ..data.import_history import count_import_history, fetch_import_history
from .table_pagination import DEFAULT_PAGE_SIZE, TablePaginationBar


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
            "before importing again."
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

        self.history_table = QTableWidget()
        self.history_table.setObjectName("importHistoryTable")
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(
            ["Session ID", "Session", "Imported"]
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
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
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

    def _populate_table(self, entries) -> None:
        self.history_table.setRowCount(len(entries))
        for row_idx, entry in enumerate(entries):
            id_item = QTableWidgetItem(str(entry.subsession_id))
            id_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            name_item = QTableWidgetItem(entry.session_name)
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
            id_item.setToolTip(tooltip)
            name_item.setToolTip(tooltip)
            imported_item.setToolTip(tooltip)
            self.history_table.setItem(row_idx, 0, id_item)
            self.history_table.setItem(row_idx, 1, name_item)
            self.history_table.setItem(row_idx, 2, imported_item)

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
