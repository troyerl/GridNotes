"""Settings tab UI."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .data_retention import DEFAULT_RETENTION, RETENTION_OPTIONS, SETTING_KEY, retention_label
from .db import get_data_dir_path, get_setting, set_setting


class SettingsTab(QWidget):
    """Application settings panel."""

    settings_saved = pyqtSignal()

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

        data_group = QGroupBox("Data storage")
        data_layout = QVBoxLayout(data_group)
        data_hint = QLabel("Local database and settings are stored at:")
        data_hint.setObjectName("sectionHint")
        data_layout.addWidget(data_hint)
        path_label = QLabel(str(get_data_dir_path()))
        path_label.setObjectName("statValue")
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        data_layout.addWidget(path_label)
        layout.addWidget(data_group)

        layout.addStretch()

    def current_retention_value(self) -> str:
        value = self.retention_combo.currentData()
        return value if value else DEFAULT_RETENTION

    def _update_retention_status_label(self) -> None:
        self.retention_status.setText(
            f"Current policy: {retention_label(self.current_retention_value())}"
        )

    def _save_settings(self) -> None:
        set_setting(SETTING_KEY, self.current_retention_value())
        self._update_retention_status_label()
        self.settings_saved.emit()

    def show_purge_result(self, deleted: int) -> None:
        policy = retention_label(self.current_retention_value())
        if deleted:
            self.retention_status.setText(
                f"Current policy: {policy} — removed {deleted} expired race result(s)."
            )
        else:
            self._update_retention_status_label()
