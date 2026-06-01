"""Modal progress UI while GridNotes applies an update."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


class UpdateProgressDialog(QDialog):
    """Shows step label and percent while an update runs in a background thread."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("updateProgressDialog")
        self.setWindowTitle("Updating GridNotes")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self._title_label = QLabel("Installing update…")
        self._title_label.setObjectName("updateProgressTitle")
        layout.addWidget(self._title_label)

        self._version_label = QLabel("")
        self._version_label.setObjectName("sectionHint")
        self._version_label.setWordWrap(True)
        layout.addWidget(self._version_label)

        self._status_label = QLabel("Starting…")
        self._status_label.setObjectName("updateProgressStatus")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setObjectName("updateProgressBar")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        layout.addWidget(self._progress)

        self._hint_label = QLabel(
            "Please keep this window open. Your notes and settings will not be removed."
        )
        self._hint_label.setObjectName("sectionHint")
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

    def begin(self, *, target_version: str | None = None) -> None:
        if target_version:
            self._version_label.setText(f"Updating to v{target_version.lstrip('v')}")
            self._version_label.setVisible(True)
        else:
            self._version_label.setVisible(False)
        self.set_progress("Starting…", 0)

    def set_progress(self, message: str, percent: int) -> None:
        self._status_label.setText(message)
        self._progress.setValue(max(0, min(100, percent)))

    def mark_complete(self, message: str) -> None:
        self.set_progress(message, 100)
