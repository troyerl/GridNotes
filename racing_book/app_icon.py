"""Resolve application icon paths and set Windows taskbar identity."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon

_APP_ID = "GridNotes.GridNotes.1"


def set_windows_app_user_model_id() -> None:
    """Required on Windows so the taskbar uses our icon instead of a generic Python icon."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_ID)
    except Exception:
        pass


def _resource_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def icon_path() -> Path | None:
    base = _resource_base()
    if sys.platform == "win32":
        ico = base / "icon.ico"
        if ico.is_file():
            return ico
    png = base / "icon.png"
    return png if png.is_file() else None


def load_app_icon() -> QIcon | None:
    path = icon_path()
    if path is None:
        return None
    icon = QIcon(str(path))
    return icon if not icon.isNull() else None
