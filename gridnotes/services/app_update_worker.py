"""Background workers for application update checks and applying updates."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from .app_update import UpdateCheckResult, apply_source_update, check_for_updates
from ..installer.frozen_update import apply_frozen_update, frozen_install_root
from ..installer.installer_update import apply_installer_update
from ..installer.portable_update import apply_portable_update, portable_install_root

logger = logging.getLogger(__name__)


class UpdateCheckWorker(QThread):
    finished = pyqtSignal(object)  # UpdateCheckResult

    def run(self) -> None:
        logger.info("Application update check started")
        try:
            result = check_for_updates()
        except Exception as exc:
            logger.exception("Application update check failed")
            from ..app.app_version import installed_version

            result = UpdateCheckResult(
                ok=False,
                message=(
                    "Could not check for updates right now.\n"
                    "Check your internet connection and try again."
                ),
                current_version=installed_version(),
            )
        self.finished.emit(result)


class ApplyAppUpdateWorker(QThread):
    """Apply a git pull or a portable (ZIP) update."""

    progress = pyqtSignal(str, int)  # status message, percent 0–100
    finished = pyqtSignal(bool, str, bool)  # ok, message, restart_in_process

    def __init__(
        self,
        result: UpdateCheckResult,
        *,
        wait_pid: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._result = result
        self._wait_pid = wait_pid

    def _report(self, message: str, percent: int) -> None:
        from ..installer.user_messages import friendly_update_progress

        self.progress.emit(friendly_update_progress(message), percent)

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
                from ..installer.user_messages import source_update_failed_message

                self.finished.emit(False, source_update_failed_message(str(exc)), True)
            return

        if method == "frozen":
            install_root = frozen_install_root()
            version = self._result.latest_version
            zip_url = self._result.release_zip_url
            if install_root is None or not version or not zip_url:
                self.finished.emit(
                    False,
                    "GridNotes could not find its install folder or the release ZIP.\n\n"
                    "Download GridNotes-Setup.exe from the website instead.",
                    True,
                )
                return
            logger.info("Applying frozen update to v%s at %s", version, install_root)
            try:
                ok, message, restart = apply_frozen_update(
                    install_root,
                    version,
                    zip_url=zip_url,
                    wait_pid=self._wait_pid,
                    on_progress=self._report,
                )
                self.finished.emit(ok, message, restart)
            except Exception:
                logger.exception("Frozen update failed")
                from ..installer.user_messages import portable_update_failed_message

                self.finished.emit(False, portable_update_failed_message(), True)
            return

        if method == "installer":
            install_root = frozen_install_root()
            version = self._result.latest_version
            setup_url = self._result.release_setup_url
            if install_root is None or not version or not setup_url:
                self.finished.emit(
                    False,
                    "GridNotes could not find its install folder or the release installer.\n\n"
                    "Download GridNotes-Setup.exe from the website instead.",
                    True,
                )
                return
            logger.info("Applying installer update to v%s at %s", version, install_root)
            try:
                ok, message, restart = apply_installer_update(
                    install_root,
                    version,
                    setup_url=setup_url,
                    wait_pid=self._wait_pid,
                    on_progress=self._report,
                )
                self.finished.emit(ok, message, restart)
            except Exception:
                logger.exception("Installer update failed")
                from ..installer.user_messages import portable_update_failed_message

                self.finished.emit(False, portable_update_failed_message(), True)
            return

        if method == "portable":
            install_root = portable_install_root()
            version = self._result.latest_version
            if install_root is None or not version:
                self.finished.emit(
                    False,
                    "GridNotes could not find its install folder to update.\n\n"
                    "Try running Install GridNotes again, or download the latest "
                    "version from the website.",
                    True,
                )
                return
            logger.info("Applying portable update to v%s at %s", version, install_root)
            try:
                ok, message, restart = apply_portable_update(
                    install_root,
                    version,
                    wait_pid=self._wait_pid,
                    on_progress=self._report,
                )
                self.finished.emit(ok, message, restart)
            except Exception as exc:
                logger.exception("Portable update failed")
                from ..installer.user_messages import portable_update_failed_message

                self.finished.emit(
                    False,
                    portable_update_failed_message(),
                    True,
                )
            return

        self.finished.emit(
            False,
            "This update cannot be installed automatically. Use Check for updates "
            "and open the download page.",
            True,
        )


# Backward-compatible alias
ApplySourceUpdateWorker = ApplyAppUpdateWorker
