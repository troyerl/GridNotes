"""Modal progress UI while streamer mode refreshes the driver list."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


class StreamerModeProgressDialog(QDialog):
    """Indeterminate progress while names are hidden or restored on screen."""

    def __init__(self, parent=None, *, enabling: bool) -> None:
        super().__init__(parent)
        self.setObjectName("streamerModeProgressDialog")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        if enabling:
            self.setWindowTitle("De-identifying drivers")
            title = "De-identifying drivers on screen"
            detail = (
                "Replacing driver names with aliases for streaming and screenshots. "
                "Your local database, notes, and marks are not changed."
            )
        else:
            self.setWindowTitle("Restoring driver names")
            title = "Restoring driver names"
            detail = (
                "Showing real names again in the table, detail panel, and Live Mode. "
                "Your scouting data is unchanged."
            )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(title)
        title_label.setObjectName("streamerModeProgressTitle")
        layout.addWidget(title_label)

        detail_label = QLabel(detail)
        detail_label.setObjectName("sectionHint")
        detail_label.setWordWrap(True)
        layout.addWidget(detail_label)

        self._progress = QProgressBar()
        self._progress.setObjectName("streamerModeProgressBar")
        self._progress.setRange(0, 0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(22)
        layout.addWidget(self._progress)

        status_label = QLabel("Please wait…")
        status_label.setObjectName("streamerModeProgressStatus")
        layout.addWidget(status_label)
