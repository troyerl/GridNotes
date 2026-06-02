"""Create a zip of logs and version info for support."""

from __future__ import annotations

import logging
import os
import platform
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ..app.app_version import __version__, installed_version
from ..data.db import get_data_dir_path, get_launch_log_path
from ..installer.uninstall import resolve_install_root
from .log_config import get_log_path

logger = logging.getLogger(__name__)


def _candidate_log_files() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen:
            return
        seen.add(resolved)
        if resolved.is_file():
            paths.append(resolved)

    add(get_log_path())
    add(get_launch_log_path())

    install_root = resolve_install_root()
    if install_root is not None:
        add(install_root / "install-helper.log")
        add(install_root / "launch-error.log")

    if sys.platform == "win32":
        temp = Path(os.environ.get("TEMP", tempfile_gettempdir()))
        for path in sorted(temp.glob("gridnotes-update.log"), reverse=True)[:3]:
            add(path)
        for path in sorted(temp.glob("GridNotes/gridnotes-update.log"), reverse=True)[:3]:
            add(path)

    return paths


def tempfile_gettempdir() -> str:
    import tempfile

    return tempfile.gettempdir()


def build_support_readme() -> str:
    lines = [
        "GridNotes support bundle",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"App version: {installed_version()} (package {__version__})",
        f"Python: {sys.version.split()[0]}",
        f"Executable: {sys.executable}",
        f"Platform: {platform.platform()}",
        "",
    ]
    install_root = resolve_install_root()
    if install_root is not None:
        lines.append(f"Install folder: {install_root}")
    lines.append(f"User data folder: {get_data_dir_path()}")
    lines.append("")
    lines.append("Files included: this readme plus any logs that existed.")
    return "\n".join(lines)


def create_support_bundle(dest_zip: Path) -> tuple[bool, str]:
    """Write a zip support bundle to *dest_zip*."""
    dest_zip = dest_zip.expanduser().resolve()
    dest_zip.parent.mkdir(parents=True, exist_ok=True)

    logs = _candidate_log_files()
    try:
        with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("readme.txt", build_support_readme())
            for path in logs:
                try:
                    archive.write(path, arcname=f"logs/{path.name}")
                except OSError as exc:
                    logger.warning("Skipping %s in support bundle: %s", path, exc)
    except OSError as exc:
        logger.exception("Support bundle failed")
        return False, f"Could not create support file: {exc}"

    if not dest_zip.is_file():
        return False, "Support file was not created."

    included = len(logs) + 1
    return True, f"Saved support bundle ({included} files):\n{dest_zip}"


def open_logs_folder() -> tuple[bool, str]:
    """Open the user data folder in the system file manager."""
    folder = get_data_dir_path()
    folder.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(folder)  # noqa: S606
        elif sys.platform == "darwin":
            import subprocess

            subprocess.run(["open", str(folder)], check=False)
        else:
            import subprocess

            subprocess.run(["xdg-open", str(folder)], check=False)
        return True, f"Opened:\n{folder}"
    except OSError as exc:
        return False, f"Could not open folder:\n{folder}\n\n{exc}"
