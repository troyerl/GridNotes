"""Log messages shown to the user (dialogs, status bar, settings hints)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

_logger = logging.getLogger("racing_book.user")


def log_user_error(message: str, *, context: str | None = None) -> None:
    """Record a user-visible error or warning in gridnotes.log."""
    if context:
        _logger.warning("%s: %s", context, message)
    else:
        _logger.warning("%s", message)


def log_user_error_dialog(title: str, message: str) -> None:
    log_user_error(message, context=title)


def show_warning(parent: QWidget | None, title: str, text: str) -> int:
    from PyQt6.QtWidgets import QMessageBox

    log_user_error_dialog(title, text)
    return QMessageBox.warning(parent, title, text)


def show_critical(parent: QWidget | None, title: str, text: str) -> int:
    from PyQt6.QtWidgets import QMessageBox

    _logger.error("%s: %s", title, text)
    return QMessageBox.critical(parent, title, text)
