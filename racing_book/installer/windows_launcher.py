"""Build GridNotes.exe on Windows (pythonw copy + custom icon for the taskbar)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

RCEDIT_VERSION = "2.0.0"
RCEDIT_URL = (
    f"https://github.com/electron/rcedit/releases/download/v{RCEDIT_VERSION}/rcedit-x64.exe"
)


def rcedit_tool_path(install_root: Path) -> Path:
    return install_root.resolve() / "scripts" / "rcedit-x64.exe"


def ensure_rcedit(install_root: Path) -> Path | None:
    """Download rcedit into the install folder if needed (Windows icon embedding)."""
    path = rcedit_tool_path(install_root)
    if path.is_file():
        return path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(RCEDIT_URL, path)
    except OSError as exc:
        logger.warning("Could not download rcedit: %s", exc)
        return None
    return path if path.is_file() else None


def embed_icon_in_exe(exe_path: Path, ico_path: Path, *, rcedit: Path) -> bool:
    """Replace the main icon on *exe_path* (used after copying pythonw.exe)."""
    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "timeout": 120,
    }
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if flags:
            kwargs["creationflags"] = flags
    try:
        result = subprocess.run(
            [
                str(rcedit),
                str(exe_path.resolve()),
                "--set-icon",
                str(ico_path.resolve()),
                "--set-version-string",
                "ProductName",
                "GridNotes",
                "--set-version-string",
                "FileDescription",
                "GridNotes",
                "--set-version-string",
                "InternalName",
                "GridNotes",
                "--set-version-string",
                "OriginalFilename",
                "GridNotes.exe",
                "--set-version-string",
                "CompanyName",
                "GridNotes",
            ],
            **kwargs,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("rcedit failed for %s: %s", exe_path, exc)
        return False
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        logger.warning("rcedit exit %s: %s", result.returncode, detail)
        return False
    return True
