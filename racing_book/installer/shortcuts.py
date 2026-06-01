"""Desktop shortcuts for GridNotes."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_SHORTCUT_NAME = "GridNotes"


def desktop_directory() -> Path:
    home = Path.home()
    if sys.platform == "win32":
        userprofile = Path(os.environ.get("USERPROFILE", home))
        for candidate in (
            userprofile / "Desktop",
            userprofile / "OneDrive" / "Desktop",
        ):
            if candidate.is_dir():
                return candidate
        return userprofile / "Desktop"
    return home / "Desktop"


def _escape_ps(path: Path) -> str:
    return str(path).replace("'", "''")


def windows_icon_location(icon: Path) -> str:
    """Format a path for WScript Shell Shortcut.IconLocation (path,index)."""
    resolved = str(icon.resolve())
    if icon.suffix.lower() in (".ico", ".exe", ".dll"):
        return f"{resolved},0"
    return resolved


def _create_windows_lnk(
    *,
    shortcut_path: Path,
    target: Path,
    working_dir: Path,
    description: str,
    icon: Path | None = None,
    arguments: str | None = None,
) -> None:
    icon_stmt = ""
    if icon is not None and icon.is_file():
        icon_loc = windows_icon_location(icon).replace("'", "''")
        icon_stmt = f"$s.IconLocation = '{icon_loc}'; "

    args_stmt = ""
    if arguments:
        args_stmt = f"$s.Arguments = '{arguments.replace(chr(39), chr(39) + chr(39))}'; "

    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{_escape_ps(shortcut_path)}'); "
        f"$s.TargetPath = '{_escape_ps(target)}'; "
        f"$s.WorkingDirectory = '{_escape_ps(working_dir)}'; "
        f"{args_stmt}"
        f"$s.Description = '{description.replace(chr(39), chr(39) + chr(39))}'; "
        f"{icon_stmt}"
        "$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
    )


def create_desktop_shortcut(
    *,
    target: Path,
    working_dir: Path,
    name: str = APP_SHORTCUT_NAME,
    icon: Path | None = None,
    arguments: str | None = None,
) -> Path:
    """
    Create a desktop shortcut to *target*.

    Windows: .lnk file. macOS/Linux: copy launcher script to Desktop.
    """
    desktop = desktop_directory()
    desktop.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        shortcut_path = desktop / f"{name}.lnk"
        _create_windows_lnk(
            shortcut_path=shortcut_path,
            target=target,
            working_dir=working_dir,
            description="GridNotes — iRacing driver scouting",
            icon=icon,
            arguments=arguments,
        )
        logger.info("Created desktop shortcut: %s", shortcut_path)
        return shortcut_path

    if target.suffix.lower() in (".command", ".sh", ".bat"):
        dest = desktop / target.name
        if dest.exists():
            dest.unlink()
        shutil.copy2(target, dest)
        dest.chmod(0o755)
        logger.info("Created desktop launcher: %s", dest)
        return dest

    raise OSError(f"Cannot create a desktop shortcut for {target} on this platform.")
