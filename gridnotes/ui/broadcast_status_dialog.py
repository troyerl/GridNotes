"""Modal shown while this device is broadcasting scouting data."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..ui.a11y import set_accessible, set_button_tooltip
from .ui_widgets import BusySpinner


class BroadcastStatusDialog(QDialog):
    stop_requested = pyqtSignal()
    audio_spotter_changed = pyqtSignal(bool)

    def __init__(
        self,
        *,
        broadcaster_name: str,
        port: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("updateProgressDialog")
        self.setWindowTitle("GridNotes Broadcast")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self._stopping = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self._title_label = QLabel("Broadcasting scouting data")
        self._title_label.setObjectName("updateProgressTitle")
        layout.addWidget(self._title_label)

        self._host_label = QLabel(f"Broadcaster: {broadcaster_name}")
        self._host_label.setObjectName("sectionHint")
        self._host_label.setWordWrap(True)
        layout.addWidget(self._host_label)

        self._port_label = QLabel(f"Port: {port}")
        self._port_label.setObjectName("sectionHint")
        layout.addWidget(self._port_label)

        self._status_label = QLabel("Waiting for a receiver…")
        self._status_label.setObjectName("updateProgressStatus")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._receivers_label = QLabel("")
        self._receivers_label.setObjectName("sectionHint")
        self._receivers_label.setWordWrap(True)
        self._receivers_label.setVisible(False)
        layout.addWidget(self._receivers_label)

        spinner_row = QHBoxLayout()
        spinner_row.addStretch()
        self._spinner = BusySpinner(self, diameter=32)
        self._spinner.setVisible(False)
        spinner_row.addWidget(self._spinner)
        spinner_row.addStretch()
        layout.addLayout(spinner_row)

        self.chk_audio_spotter = QCheckBox("Audio spotter")
        self.chk_audio_spotter.setObjectName("liveAudioSpotter")
        self.chk_audio_spotter.setChecked(False)
        set_button_tooltip(
            self.chk_audio_spotter,
            "Optional — off by default for this broadcast only. When enabled, speaks a "
            "warning if a disliked or high-risk driver is within 1.5 seconds behind you "
            "(Windows only, green-flag running). Does not change your saved app setting.",
        )
        set_accessible(
            self.chk_audio_spotter,
            "Audio spotter",
            "Enable co-driver warnings for this broadcast session only.",
        )
        self.chk_audio_spotter.stateChanged.connect(self._on_audio_spotter_changed)
        layout.addWidget(self.chk_audio_spotter)

        self._hint_label = QLabel(
            "GridNotes is closed while broadcasting. Receivers on the same network can "
            "connect using the Receiver button in the header bar on another device.\n\n"
            "Keep iRacing running on this PC so live session and grid data stay in sync."
        )
        self._hint_label.setObjectName("sectionHint")
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_stop = QPushButton("Stop broadcasting")
        self.btn_stop.setObjectName("primaryBtn")
        set_button_tooltip(
            self.btn_stop,
            "Stop sharing and return to the full GridNotes window.",
        )
        self.btn_stop.clicked.connect(self._request_stop)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        if sys.platform != "win32":
            self.set_audio_spotter_available(False)

    def set_connected_receivers(self, names: list[str]) -> None:
        if self._stopping:
            return
        if not names:
            self._status_label.setText("Waiting for a receiver…")
            self._receivers_label.setVisible(False)
            self._receivers_label.setText("")
            return
        count = len(names)
        noun = "receiver" if count == 1 else "receivers"
        self._status_label.setText(f"{count} {noun} connected")
        self._receivers_label.setText(
            "\n".join(f"• {name}" for name in names)
        )
        self._receivers_label.setVisible(True)

    def set_receiver_count(self, count: int) -> None:
        """Backward-compatible hook when only a count is available."""
        if count <= 0:
            self.set_connected_receivers([])
        else:
            self.set_connected_receivers([f"Receiver {index + 1}" for index in range(count)])

    def set_audio_spotter_enabled(self, enabled: bool) -> None:
        self.chk_audio_spotter.blockSignals(True)
        self.chk_audio_spotter.setChecked(enabled)
        self.chk_audio_spotter.blockSignals(False)

    def set_audio_spotter_available(self, available: bool) -> None:
        self.chk_audio_spotter.setEnabled(available)
        if not available:
            set_button_tooltip(
                self.chk_audio_spotter,
                "Audio spotter requires Windows with iRacing running.",
            )

    def is_stopping(self) -> bool:
        return self._stopping

    def begin_stopping(self, *, closing_app: bool = False) -> None:
        if self._stopping:
            return
        self._stopping = True
        self.btn_stop.setEnabled(False)
        self.btn_stop.setVisible(False)
        self.chk_audio_spotter.setEnabled(False)
        self._host_label.setVisible(False)
        self._port_label.setVisible(False)
        self.chk_audio_spotter.setVisible(False)
        self._hint_label.setVisible(False)
        self._receivers_label.setVisible(False)
        self._spinner.start()
        if closing_app:
            self.setWindowTitle("Closing GridNotes")
            self._title_label.setText("Closing GridNotes")
            self._status_label.setText(
                "Stopping broadcast and closing the app. Please wait…"
            )
        else:
            self.setWindowTitle("Stopping broadcast")
            self._title_label.setText("Stopping broadcast")
            self._status_label.setText(
                "Disconnecting receivers and returning to GridNotes. Please wait…"
            )
        self.raise_()
        self.activateWindow()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def _on_audio_spotter_changed(self, _state: int) -> None:
        self.audio_spotter_changed.emit(self.chk_audio_spotter.isChecked())

    def _request_stop(self) -> None:
        if self._stopping:
            return
        self.begin_stopping()
        self.stop_requested.emit()
