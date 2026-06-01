"""Background thread for the install wizard."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .logic import InstallRunner, find_project_root


class InstallWorker(QThread):
    step_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(
        self,
        *,
        root: Path | None = None,
        build_standalone: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._root = root or find_project_root()
        self._build_standalone = build_standalone
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        runner = InstallRunner(
            self._root,
            build_standalone=self._build_standalone,
            on_log=self.log_line.emit,
            on_step=self.step_changed.emit,
            on_progress=self.progress_changed.emit,
            should_cancel=lambda: self._cancel_requested,
        )
        ok, message = runner.run()
        self.finished.emit(ok, message)
