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
        source_root: Path | None = None,
        install_root: Path | None = None,
        build_standalone: bool = False,
        build_output_dir: Path | None = None,
        create_desktop_shortcut: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._source_root = source_root or find_project_root(Path.cwd())
        if not (self._source_root / "requirements.txt").is_file():
            self._source_root = find_project_root()
        self._install_root = install_root or self._source_root
        self._build_standalone = build_standalone
        self._build_output_dir = build_output_dir
        self._create_desktop_shortcut = create_desktop_shortcut
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        runner = InstallRunner(
            self._source_root,
            self._install_root,
            build_standalone=self._build_standalone,
            build_output_dir=self._build_output_dir,
            create_desktop_shortcut=self._create_desktop_shortcut,
            on_log=self.log_line.emit,
            on_step=self.step_changed.emit,
            on_progress=self.progress_changed.emit,
            should_cancel=lambda: self._cancel_requested,
        )
        ok, message = runner.run()
        self.finished.emit(ok, message)
