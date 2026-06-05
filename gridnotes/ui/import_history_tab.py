"""Import history tab — list of previously imported iRacing subsessions."""

from __future__ import annotations

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
from ..data.import_history import IMPORT_HISTORY_LIMIT, count_imported_sessions, fetch_import_history


class ImportHistoryTab(QWidget):
    """Top-level tab listing imported subsession IDs and session names."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

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
        self.search_input.textChanged.connect(self.refresh)
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
        layout.addWidget(table_frame, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("sectionHint")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        session_id_query = self.search_input.text().strip()
        conn = connect_db(get_db_path())
        try:
            total_sessions = count_imported_sessions(conn)
            entries = fetch_import_history(
                conn,
                session_id_query=session_id_query or None,
            )
        finally:
            conn.close()

        self._populate_table(entries)
        self._update_status(total_sessions, len(entries), session_id_query)

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

    def _update_status(
        self,
        total_sessions: int,
        shown: int,
        session_id_query: str,
    ) -> None:
        if total_sessions == 0:
            self.status_label.setText(
                "No imported sessions yet. Use Import race JSON on the Drivers tab."
            )
            return

        if session_id_query:
            if shown == 0:
                self.status_label.setText(
                    f"No imported sessions match session ID “{session_id_query}”."
                )
            elif shown == 1:
                self.status_label.setText(
                    f"1 imported session matches session ID “{session_id_query}”."
                )
            else:
                self.status_label.setText(
                    f"{shown} imported sessions match session ID “{session_id_query}”."
                )
            return

        if total_sessions > shown:
            self.status_label.setText(
                f"{total_sessions} imported session(s). "
                f"Showing the most recent {IMPORT_HISTORY_LIMIT}."
            )
        else:
            self.status_label.setText(f"{total_sessions} imported session(s).")
