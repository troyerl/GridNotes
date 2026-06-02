"""Resolve application icon paths and set Windows taskbar identity."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_USER_MODEL_ID = "GridNotes.GridNotes.1"


def set_windows_app_user_model_id() -> None:
    """Required on Windows so the taskbar uses our icon instead of a generic Python icon."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
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

    if arg0.name.lower() == "gridnotes.exe" and arg0.parent.name == "Scripts":
        install_root = arg0.parent.parent.parent
        if (install_root / "main.py").is_file() and _has_icon_assets(install_root):
            return install_root

    if sys.executable:
        exe = Path(sys.executable).resolve()
        if exe.name.lower() == "gridnotes.exe" and exe.parent.name == "Scripts":
            install_root = exe.parent.parent.parent
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


def shell_icon_path() -> Path | None:
    """
    Icon file for Windows shell branding (taskbar pin, AppUserModelID).

    Prefer icon.ico — PyQt and some shell paths handle it more reliably than pythonw.exe.
    """
    ico = icon_path()
    if ico is not None and ico.suffix.lower() == ".ico":
        return ico
    if sys.platform == "win32":
        try:
            from ..installer.logic import windows_launcher_exe_path
            from ..installer.uninstall import resolve_install_root

            root = resolve_install_root()
            if root is not None:
                install_ico = root / "icon.ico"
                if install_ico.is_file():
                    return install_ico
                launcher = windows_launcher_exe_path(root)
                if launcher.is_file():
                    return launcher
        except Exception:
            pass
    return ico


def taskbar_icon_path() -> Path | None:
    """Backward-compatible alias for :func:`shell_icon_path`."""
    return shell_icon_path()


def load_app_icon():  # -> QIcon | None
    from PyQt6.QtGui import QIcon

    candidates: list[Path] = []
    base = _resource_base()
    candidates.extend([base / "icon.ico", base / "icon.png"])

    try:
        from ..installer.uninstall import resolve_install_root

        root = resolve_install_root()
        if root is not None:
            candidates.extend([root / "icon.ico", root / "icon.png"])
    except Exception:
        pass

    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        icon = QIcon(str(resolved))
        if not icon.isNull():
            return icon

    resolved_ico = icon_path()
    if resolved_ico is not None and resolved_ico not in seen:
        icon = QIcon(str(resolved_ico))
        if not icon.isNull():
            return icon

    if getattr(sys, "frozen", False) and sys.platform == "win32" and sys.executable:
        exe_icon = QIcon(sys.executable)
        if not exe_icon.isNull():
            return exe_icon

    logger.warning("Application icon not found (searched near %s)", _resource_base())
    return None
