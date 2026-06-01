"""Background workers for application update checks and applying updates."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from .app_update import UpdateCheckResult, apply_source_update, check_for_updates
from .portable_update import apply_portable_update, portable_install_root

logger = logging.getLogger(__name__)


class UpdateCheckWorker(QThread):
    finished = pyqtSignal(object)  # UpdateCheckResult

    def run(self) -> None:
        logger.info("Application update check started")
        try:
            result = check_for_updates()
        except Exception as exc:
            logger.exception("Application update check failed")
            from ..app.app_version import __version__

            result = UpdateCheckResult(
                ok=False,
                message=f"Update check failed: {exc}",
                current_version=__version__,
            )
        self.finished.emit(result)


class ApplyAppUpdateWorker(QThread):
    """Apply a git pull or a portable (ZIP) update."""

    progress = pyqtSignal(str, int)  # status message, percent 0–100
    finished = pyqtSignal(bool, str, bool)  # ok, message, restart_in_process

    def __init__(self, result: UpdateCheckResult, parent=None) -> None:
        super().__init__(parent)
        self._result = result

    def _report(self, message: str, percent: int) -> None:
        self.progress.emit(message, percent)

    def run(self) -> None:
        method = self._result.apply_method
        if method == "git":
            logger.info("Applying source update (git pull)")
            self._report("Starting update…", 5)
            try:
                ok, message = apply_source_update(on_progress=self._report)
                self.finished.emit(ok, message, True)
            except Exception as exc:
                logger.exception("Source update failed")
                self.finished.emit(False, str(exc), True)
            return

        if method == "portable":
            install_root = portable_install_root()
            version = self._result.latest_version
            if install_root is None or not version:
                self.finished.emit(
                    False,
                    "Could not locate the installed copy to update.",
                    True,
                )
                return
            logger.info("Applying portable update to v%s at %s", version, install_root)
            try:
                ok, message, restart = apply_portable_update(
                    install_root,
                    version,
                    on_progress=self._report,
                )
                self.finished.emit(ok, message, restart)
            except Exception as exc:
                logger.exception("Portable update failed")
                self.finished.emit(False, str(exc), True)
            return

        self.finished.emit(False, "No update method is available.", True)


# Backward-compatible alias
ApplySourceUpdateWorker = ApplyAppUpdateWorker
