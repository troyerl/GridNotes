"""Apply Windows taskbar identity without fragile PowerShell argument quoting."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_TASKBAR_SCRIPT_NAME = "windows_taskbar_identity.ps1"


def _taskbar_script_path() -> Path | None:
    candidates: list[Path] = []
    try:
        from ..installer.uninstall import resolve_install_root

        root = resolve_install_root()
        if root is not None:
            candidates.append(root / "scripts" / _TASKBAR_SCRIPT_NAME)
    except Exception:
        pass
    repo_script = Path(__file__).resolve().parent.parent.parent / "scripts" / _TASKBAR_SCRIPT_NAME
    candidates.append(repo_script)
    for path in candidates:
        if path.is_file():
            return path
    return None


def _icon_resource(icon: Path | None) -> str:
    if icon is not None and icon.is_file():
        return f"{icon.resolve()},0"
    return ""


def _run_taskbar_script(*, mode: str, hwnd: int | None, shortcut_path: Path | None) -> bool:
    script = _taskbar_script_path()
    if script is None:
        logger.warning("Missing %s", _TASKBAR_SCRIPT_NAME)
        return False

    env = os.environ.copy()
    env["GN_APP_ID"] = env.get("GN_APP_ID", "GridNotes.GridNotes.1")
    if hwnd is not None and hwnd > 0:
        env["GN_HWND"] = str(hwnd)
    if shortcut_path is not None:
        env["GN_SHORTCUT_PATH"] = str(shortcut_path.resolve())

    args = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Mode",
        mode,
    ]
    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "timeout": 60,
        "env": env,
    }
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if flags:
            kwargs["creationflags"] = flags
    try:
        result = subprocess.run(args, **kwargs)
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("Taskbar identity script failed to run: %s", exc)
        return False

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        logger.warning(
            "Taskbar identity script exit %s: %s",
            result.returncode,
            detail,
        )
        return False
    return True


def apply_shell_properties(
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
    if not relaunch_command or not relaunch_command.strip():
        logger.warning("Taskbar branding skipped: empty relaunch command")
        return False

    env_backup: dict[str, str | None] = {}
    for key in (
        "GN_APP_ID",
        "GN_DISPLAY_NAME",
        "GN_RELAUNCH_CMD",
        "GN_ICON_PATH",
        "GN_HWND",
        "GN_SHORTCUT_PATH",
    ):
        env_backup[key] = os.environ.get(key)

    try:
        os.environ["GN_APP_ID"] = app_id
        os.environ["GN_DISPLAY_NAME"] = display_name
        os.environ["GN_RELAUNCH_CMD"] = relaunch_command.strip()
        icon_res = _icon_resource(icon)
        if icon_res:
            os.environ["GN_ICON_PATH"] = icon_res.split(",")[0]
        elif "GN_ICON_PATH" in os.environ:
            del os.environ["GN_ICON_PATH"]

        if shortcut_path is not None:
            ok = _run_taskbar_script(mode="Shortcut", hwnd=None, shortcut_path=shortcut_path)
        elif hwnd is not None and hwnd > 0:
            ok = _run_taskbar_script(mode="Window", hwnd=hwnd, shortcut_path=None)
        else:
            ok = False
    finally:
        for key, previous in env_backup.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous

    if ok:
        logger.info(
            "Applied Windows taskbar identity (%s)",
            "shortcut" if shortcut_path else f"hwnd={hwnd}",
        )
    return ok


def native_window_hwnd(widget) -> int:
    """Best HWND for a QWidget (Qt 6)."""
    try:
        wh = widget.windowHandle()
        if wh is not None:
            wid = int(wh.winId())
            if wid > 0:
                return wid
    except (AttributeError, TypeError, ValueError):
        pass
    try:
        return int(widget.winId())
    except (AttributeError, TypeError, ValueError):
        return 0
