"""Modal progress UI while GridNotes applies an update."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QProgressBar, QVBoxLayout

from ..installer.user_messages import friendly_update_progress, update_windows_permission_notice
from ..ui.theme import configure_modal_dialog


class UpdateProgressDialog(QDialog):
    """Shows step label and percent while an update runs in a background thread."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("updateProgressDialog")
        self.setWindowTitle("Updating GridNotes")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self._title_label = QLabel("Installing the update")
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

        self._hint_label = QLabel("")
        self._hint_label.setObjectName("sectionHint")
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        self._requires_windows_permission = False
        configure_modal_dialog(self)

    def begin(
        self,
        *,
        target_version: str | None = None,
        requires_windows_permission: bool = False,
    ) -> None:
        self._requires_windows_permission = requires_windows_permission
        if target_version:
            self._version_label.setText(
                f"Updating to version {target_version.lstrip('v')}"
            )
            self._version_label.setVisible(True)
        else:
            self._version_label.setVisible(False)
        self._apply_waiting_hint(requires_windows_permission)
        self.set_progress("Starting…", 0)

    def _apply_waiting_hint(self, requires_windows_permission: bool) -> None:
        lines = [
            "Please keep this window open until GridNotes reopens.",
            "Your notes, ratings, and settings will stay exactly as they are.",
        ]
        if requires_windows_permission:
            lines.append("")
            lines.append(update_windows_permission_notice())
        self._hint_label.setText("\n".join(lines))

    def set_progress(self, message: str, percent: int) -> None:
        self._status_label.setText(friendly_update_progress(message))
        self._progress.setRange(0, 100)
        self._progress.setValue(max(0, min(100, percent)))

    def mark_complete(self, message: str) -> None:
        self.set_progress(message, 100)

    def begin_closing_for_update(self, *, requires_windows_permission: bool) -> None:
        """Show a waiting state before GridNotes exits to finish installing."""
        self._requires_windows_permission = requires_windows_permission
        self.setWindowTitle("Finishing the update")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._title_label.setText("Almost done")
        self._progress.setRange(0, 0)
        if requires_windows_permission:
            self._status_label.setText(
                "GridNotes will close for a moment. When Windows asks for permission, "
                "click Yes so the update can finish."
            )
        else:
            self._status_label.setText(
                "GridNotes will close for a moment and reopen automatically."
            )
        self._hint_label.setText(
            "Please wait on this screen. GridNotes should reopen on its own shortly."
        )
        self.raise_()
        self.activateWindow()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
