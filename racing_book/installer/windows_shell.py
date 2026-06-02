"""Windows shell properties for taskbar icons and pinning."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _subprocess_hide_window_kwargs() -> dict:
    """Avoid flashing console windows when spawning PowerShell on Windows."""
    if sys.platform != "win32":
        return {}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return {"creationflags": flags} if flags else {}


def resolve_relaunch_command(existing: str | None = None) -> str | None:
    """Command line for taskbar pin/relaunch metadata (required with display name)."""
    if existing and existing.strip():
        return existing.strip()
    try:
        from ..installer.uninstall import resolve_install_root

        install_root = resolve_install_root()
        if install_root is not None:
            built = build_relaunch_command(install_root)
            if built:
                return built
    except Exception:
        pass
    if sys.executable:
        exe = Path(sys.executable).resolve()
        if exe.is_file():
            if len(sys.argv) <= 1:
                return f'"{exe}"'
            parts = [f'"{exe}"'] + [
                f'"{arg}"' if " " in arg else arg for arg in sys.argv[1:]
            ]
            return " ".join(parts)
    return None


def build_relaunch_command(install_root: Path) -> str | None:
    """Command line Windows uses when pinning the running app to the taskbar."""
    from .logic import (
        VENV_DIR_NAME,
        gridnotes_start_script_path,
        venv_pythonw,
        windows_launcher_arguments,
        windows_launcher_exe_path,
    )

    install_root = install_root.resolve()
    launcher = windows_launcher_exe_path(install_root)
    args = windows_launcher_arguments(install_root)
    if launcher.is_file() and args:
        return f'"{launcher.resolve()}" {args}'

    venv_dir = install_root / VENV_DIR_NAME
    pyw = venv_pythonw(venv_dir)
    starter = gridnotes_start_script_path(install_root)
    if not pyw.is_file() or not starter.is_file():
        return None
    return f'"{pyw.resolve()}" "{starter.resolve()}"'


def _run_shell_property_script(
    *,
    app_id: str,
    icon: Path | None,
    shortcut_path: Path | None = None,
    hwnd: int | None = None,
    relaunch_command: str | None = None,
    display_name: str = "GridNotes",
) -> bool:
    if sys.platform != "win32":
        return False

    from .windows_shell_native import apply_shell_properties

    return apply_shell_properties(
        app_id=app_id,
        icon=icon,
        shortcut_path=shortcut_path,
        hwnd=hwnd,
        relaunch_command=relaunch_command,
        display_name=display_name,
    )


def apply_shortcut_taskbar_identity(
    shortcut_path: Path,
    icon: Path | None,
    *,
    relaunch_command: str | None = None,
    display_name: str = "GridNotes",
) -> bool:
    """Set AppUserModelID (and icon) on a .lnk so taskbar pins keep the GridNotes icon."""
    from ..app.app_icon import APP_USER_MODEL_ID

    relaunch = resolve_relaunch_command(relaunch_command)
    return _run_shell_property_script(
        app_id=APP_USER_MODEL_ID,
        icon=icon,
        shortcut_path=shortcut_path,
        relaunch_command=relaunch,
        display_name=display_name,
    )


def apply_window_taskbar_identity(
    widget,
    icon: Path | None,
    *,
    relaunch_command: str | None = None,
    display_name: str = "GridNotes",
) -> bool:
    """Associate the main window with the same AppUserModelID as our shortcuts."""
    from ..app.app_icon import APP_USER_MODEL_ID, set_windows_app_user_model_id

    set_windows_app_user_model_id()
    if sys.platform != "win32":
        return False
    from .windows_shell_native import native_window_hwnd

    hwnd = native_window_hwnd(widget)
    if hwnd <= 0:
        logger.warning("Taskbar branding skipped: invalid window handle")
        return False
    relaunch = resolve_relaunch_command(relaunch_command)
    if not relaunch:
        logger.warning(
            "No relaunch command for taskbar branding; menu may show as Python"
        )
        return False
    return _run_shell_property_script(
        app_id=APP_USER_MODEL_ID,
        icon=icon,
        hwnd=hwnd,
        relaunch_command=relaunch,
        display_name=display_name,
    )
