"""Resolve application icon paths and set Windows taskbar identity."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon

logger = logging.getLogger(__name__)

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


def _has_icon_assets(folder: Path) -> bool:
    return (folder / "icon.ico").is_file() or (folder / "icon.png").is_file()


def _frozen_icon_search_paths() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path | None) -> None:
        if path is None:
            return
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen:
            return
        seen.add(resolved)
        paths.append(resolved)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        add(Path(meipass))

    if getattr(sys, "frozen", False) and sys.executable:
        exe_dir = Path(sys.executable).resolve().parent
        add(exe_dir)
        add(exe_dir / "_internal")

    return paths


def _runtime_install_root() -> Path | None:
    if not sys.argv:
        return None

    arg0 = Path(sys.argv[0]).resolve()
    if arg0.name in ("gridnotes_start.py", "main.py") and _has_icon_assets(arg0.parent):
        return arg0.parent

    if arg0.suffix.lower() == ".exe" and _has_icon_assets(arg0.parent):
        return arg0.parent

    if arg0.name.lower() in ("python.exe", "pythonw.exe") and arg0.parent.name == "Scripts":
        install_root = arg0.parent.parent.parent
        if (install_root / "main.py").is_file() and _has_icon_assets(install_root):
            return install_root

    return None


def _resource_base() -> Path:
    if getattr(sys, "frozen", False):
        for folder in _frozen_icon_search_paths():
            if _has_icon_assets(folder):
                return folder
        if _frozen_icon_search_paths():
            return _frozen_icon_search_paths()[0]
        return Path(sys.executable).resolve().parent

    runtime_root = _runtime_install_root()
    if runtime_root is not None:
        return runtime_root

    try:
        from ..installer.logic import find_project_root

        root = find_project_root()
        if _has_icon_assets(root):
            return root
    except Exception:
        pass

    # Repo / install root: racing_book/app/app_icon.py -> parent x3
    repo_root = Path(__file__).resolve().parent.parent.parent
    if _has_icon_assets(repo_root):
        return repo_root

    return Path(__file__).resolve().parent.parent


def _resolve_icon_file(base: Path) -> Path | None:
    ico = base / "icon.ico"
    if ico.is_file():
        return ico

    png = base / "icon.png"
    if not png.is_file():
        return None

    if sys.platform == "win32" and not getattr(sys, "frozen", False):
        try:
            from ..installer.logic import ensure_icon_ico

            python = Path(sys.executable)
            if python.is_file():
                ensured = ensure_icon_ico(base, python)
                if ensured is not None and ensured.is_file():
                    return ensured
        except Exception as exc:
            logger.debug("Could not generate icon.ico: %s", exc)

    return png


def icon_path() -> Path | None:
    return _resolve_icon_file(_resource_base())


def load_app_icon() -> QIcon | None:
    path = icon_path()
    if path is not None:
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon

    if getattr(sys, "frozen", False) and sys.platform == "win32" and sys.executable:
        exe_icon = QIcon(sys.executable)
        if not exe_icon.isNull():
            return exe_icon

    logger.warning("Application icon not found (searched near %s)", _resource_base())
    return None
