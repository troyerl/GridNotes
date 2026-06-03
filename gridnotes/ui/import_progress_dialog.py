"""Modal progress UI while race JSON files are imported."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


class ImportProgressDialog(QDialog):
    """Indeterminate progress while JSON race logs are uploaded and imported."""

    def __init__(self, parent=None, *, file_count: int = 1) -> None:
        super().__init__(parent)
        self.setObjectName("importProgressDialog")
        self.setWindowTitle("Importing race data")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        count = max(1, int(file_count))
        if count == 1:
            title = "Importing race JSON"
            detail = (
                "Reading your file and updating your local scouting database. "
                "This may take a moment for large race logs."
            )
        else:
            title = f"Importing {count} race JSON files"
            detail = (
                "Reading each file and updating your local scouting database. "
                "Please wait until this finishes."
            )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(title)
        title_label.setObjectName("importProgressTitle")
        layout.addWidget(title_label)

        detail_label = QLabel(detail)
        detail_label.setObjectName("sectionHint")
        detail_label.setWordWrap(True)
        layout.addWidget(detail_label)

        self._progress = QProgressBar()
        self._progress.setObjectName("importProgressBar")
        self._progress.setRange(0, 0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(22)
        layout.addWidget(self._progress)

        self._status_label = QLabel("Starting import…")
        self._status_label.setObjectName("importProgressStatus")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

    def set_file_progress(self, current: int, total: int, filename: str) -> None:
        name = (filename or "").strip() or "file"
        if total > 1:
            self._status_label.setText(
                f"Processing file {current} of {total}:\n{name}"
            )
        else:
            self._status_label.setText(f"Processing {name}…")

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_finalizing(self) -> None:
        """Shown while the main thread updates the driver table after import."""
        self.set_status(
            "Updating the driver list…\n"
            "Please wait — the window may look idle briefly for large imports."
        )
