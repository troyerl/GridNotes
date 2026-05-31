"""Settings tab UI."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .data_retention import DEFAULT_RETENTION, RETENTION_OPTIONS, SETTING_KEY, retention_label
from .db import connect_db, get_data_dir_path, get_db_file_size, get_db_path, get_setting, set_setting
from .driver_cleanup import count_zero_race_drivers
from .utils import format_file_size


class SettingsTab(QWidget):
    """Application settings panel."""

    settings_saved = pyqtSignal()
    zero_race_cleanup_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("appTitle")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)

        retention_group = QGroupBox("Race history retention")
        retention_layout = QVBoxLayout(retention_group)
        retention_layout.setSpacing(10)

        hint = QLabel(
            "Automatically remove imported race results older than the selected period. "
            "Driver notes and preferences are kept. Results without a known date are not removed."
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        retention_layout.addWidget(hint)

        row = QVBoxLayout()
        row.setSpacing(6)
        row_label = QLabel("Keep race data for")
        row_label.setObjectName("statInlineLabel")
        row.addWidget(row_label)

        self.retention_combo = QComboBox()
        self.retention_combo.setObjectName("settingsCombo")
        for value, label in RETENTION_OPTIONS:
            self.retention_combo.addItem(label, value)
        current = get_setting(SETTING_KEY, DEFAULT_RETENTION) or DEFAULT_RETENTION
        idx = self.retention_combo.findData(current)
        self.retention_combo.setCurrentIndex(idx if idx >= 0 else 0)
        row.addWidget(self.retention_combo)
        retention_layout.addLayout(row)

        self.retention_status = QLabel("")
        self.retention_status.setObjectName("sectionHint")
        self.retention_status.setWordWrap(True)
        retention_layout.addWidget(self.retention_status)
        self._update_retention_status_label()

        self.btn_save_settings = QPushButton("Save settings")
        self.btn_save_settings.setObjectName("primaryBtn")
        self.btn_save_settings.clicked.connect(self._save_settings)
        retention_layout.addWidget(self.btn_save_settings)

        layout.addWidget(retention_group)

        cleanup_group = QGroupBox("Driver cleanup")
        cleanup_layout = QVBoxLayout(cleanup_group)
        cleanup_layout.setSpacing(10)

        cleanup_hint = QLabel(
            "Remove drivers who have no imported race results. "
            "This clears live-session placeholders and scouting notes for those drivers."
        )
        cleanup_hint.setObjectName("sectionHint")
        cleanup_hint.setWordWrap(True)
        cleanup_layout.addWidget(cleanup_hint)

        self.zero_race_status = QLabel("")
        self.zero_race_status.setObjectName("sectionHint")
        self.zero_race_status.setWordWrap(True)
        cleanup_layout.addWidget(self.zero_race_status)
        self._update_zero_race_status_label()

        self.btn_remove_zero_race = QPushButton("Remove drivers with 0 races")
        self.btn_remove_zero_race.clicked.connect(self._request_zero_race_cleanup)
        cleanup_layout.addWidget(self.btn_remove_zero_race)

        layout.addWidget(cleanup_group)

        data_group = QGroupBox("Data storage")
        data_layout = QVBoxLayout(data_group)
        data_hint = QLabel("Local database and settings are stored at:")
        data_hint.setObjectName("sectionHint")
        data_layout.addWidget(data_hint)
        self.data_dir_label = QLabel(str(get_data_dir_path()))
        self.data_dir_label.setObjectName("sectionHint")
        self.data_dir_label.setWordWrap(True)
        self.data_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        data_layout.addWidget(self.data_dir_label)

        db_hint = QLabel("Database file:")
        db_hint.setObjectName("statInlineLabel")
        data_layout.addWidget(db_hint)
        self.db_path_label = QLabel("")
        self.db_path_label.setObjectName("statValue")
        self.db_path_label.setWordWrap(True)
        self.db_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        data_layout.addWidget(self.db_path_label)
        self.refresh_storage_info()
        layout.addWidget(data_group)

        layout.addStretch()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh_storage_info()
        self._update_zero_race_status_label()

    def refresh_storage_info(self) -> None:
        db_path = get_db_path()
        size_bytes = get_db_file_size()
        if size_bytes is None:
            self.db_path_label.setText(f"{db_path}  ·  —")
        else:
            self.db_path_label.setText(f"{db_path}  ·  {format_file_size(size_bytes)}")

    def current_retention_value(self) -> str:
        value = self.retention_combo.currentData()
        return value if value else DEFAULT_RETENTION

    def _update_retention_status_label(self) -> None:
        self.retention_status.setText(
            f"Current policy: {retention_label(self.current_retention_value())}"
        )

    def _update_zero_race_status_label(self, pending: int | None = None) -> None:
        if pending is None:
            conn = connect_db()
            try:
                pending = count_zero_race_drivers(conn)
            finally:
                conn.close()
        if pending:
            self.zero_race_status.setText(
                f"{pending} driver(s) with 0 races can be removed."
            )
        else:
            self.zero_race_status.setText("No zero-race drivers to remove.")

    def _request_zero_race_cleanup(self) -> None:
        self.zero_race_cleanup_requested.emit()

    def _save_settings(self) -> None:
        set_setting(SETTING_KEY, self.current_retention_value())
        self._update_retention_status_label()
        self.settings_saved.emit()

    def show_zero_race_cleanup_result(self, deleted: int) -> None:
        self.refresh_storage_info()
        if deleted:
            self.zero_race_status.setText(
                f"Removed {deleted} driver(s) with no race history."
            )
        else:
            self._update_zero_race_status_label(0)

    def show_purge_result(self, deleted: int) -> None:
        self.refresh_storage_info()
        policy = retention_label(self.current_retention_value())
        if deleted:
            self.retention_status.setText(
                f"Current policy: {policy} — removed {deleted} expired race result(s)."
            )
        else:
            self._update_retention_status_label()
