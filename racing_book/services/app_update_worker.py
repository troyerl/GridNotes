"""Background workers for application update checks and git pull."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from .app_update import UpdateCheckResult, apply_source_update, check_for_updates

logger = logging.getLogger(__name__)


class UpdateCheckWorker(QThread):
    finished = pyqtSignal(object)  # UpdateCheckResult

    def run(self) -> None:
        logger.info("Application update check started")
        try:
            result = check_for_updates()
        except Exception as exc:
            logger.exception("Application update check failed")
            from .app_version import __version__

            result = UpdateCheckResult(
                ok=False,
                message=f"Update check failed: {exc}",
                current_version=__version__,
            )
        self.finished.emit(result)


class ApplySourceUpdateWorker(QThread):
    finished = pyqtSignal(bool, str)

    def run(self) -> None:
        logger.info("Applying source update (git pull)")
        try:
            ok, message = apply_source_update()
            self.finished.emit(ok, message)
        except Exception as exc:
            logger.exception("Source update failed")
            self.finished.emit(False, str(exc))
