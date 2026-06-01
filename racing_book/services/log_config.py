"""Central logging setup — all errors go to gridnotes.log for support.

User-visible errors (dialogs, status bar, settings) are logged via user_feedback.py.
"""

from __future__ import annotations

import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ..data.db import get_data_dir_path

_LOG_FILE_NAME = "gridnotes.log"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB per file
_BACKUP_COUNT = 3

_log_path: Path | None = None


def get_log_path() -> Path:
    global _log_path
    if _log_path is None:
        _log_path = get_data_dir_path() / _LOG_FILE_NAME
    return _log_path


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logging.getLogger("racing_book.crash").critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_tb),
    )


def _threading_excepthook(args: threading.ExceptHookArgs) -> None:
    logging.getLogger("racing_book.crash").critical(
        "Uncaught exception in thread %s",
        getattr(args.thread, "name", args.thread),
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def _install_qt_message_handler() -> None:
    try:
        from PyQt6.QtCore import QtMsgType, qInstallMessageHandler
    except Exception:
        return

    qt_logger = logging.getLogger("racing_book.qt")

    def handler(mode, context, message) -> None:
        if not message:
            return
        text = str(message)
        if mode == QtMsgType.QtFatalMsg:
            qt_logger.critical("%s:%s %s", context.file, context.line, text)
        elif mode == QtMsgType.QtCriticalMsg:
            qt_logger.error("%s:%s %s", context.file, context.line, text)
        elif mode == QtMsgType.QtWarningMsg:
            qt_logger.warning("%s:%s %s", context.file, context.line, text)
        elif mode == QtMsgType.QtInfoMsg:
            qt_logger.info(text)
        else:
            qt_logger.debug(text)

    qInstallMessageHandler(handler)


def setup_logging() -> Path:
    """
    Configure file logging for the whole app.
    Returns the path to gridnotes.log (for showing users where to look).
    """
    log_path = get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Start each app run with a fresh log file.
    try:
        for pattern in (_LOG_FILE_NAME, "racingbook.log"):
            for p in log_path.parent.glob(f"{pattern}*"):
                if p.is_file():
                    p.unlink(missing_ok=True)
    except Exception:
        # If we can't clear logs (locked/permissions), continue and append/rotate normally.
        pass

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        mode="w",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Optional console output when launched from a terminal (dev/debug).
    if sys.stderr is not None and getattr(sys.stderr, "isatty", lambda: False)():
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        root.addHandler(console)

    sys.excepthook = _excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _threading_excepthook

    _install_qt_message_handler()

    boot = logging.getLogger("racing_book")
    boot.info("=" * 60)
    boot.info("GridNotes starting")
    boot.info("Log file: %s", log_path)
    boot.info("Platform: %s", sys.platform)
    boot.info("Python: %s", sys.version.replace("\n", " "))
    boot.info("Frozen (bundled exe): %s", getattr(sys, "frozen", False))
    if getattr(sys, "frozen", False):
        boot.info("Executable: %s", sys.executable)
    boot.info("=" * 60)

    return log_path


def shutdown_logging() -> None:
    """Close log file handlers so user data folders can be deleted (e.g. uninstall)."""
    global _log_path
    root = logging.getLogger()
    for handler in root.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        root.removeHandler(handler)
    _log_path = None
