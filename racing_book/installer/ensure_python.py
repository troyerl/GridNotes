"""Ensure a supported Python (3.10–3.13) is available for the install helper on Windows."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .logic import resolve_install_python

logger = logging.getLogger(__name__)

# Pinned installer used when winget is unavailable (64-bit Windows).
WINDOWS_PYTHON_FULL_VERSION = "3.13.3"
WINDOWS_PYTHON_INSTALLER_URL = (
    f"https://www.python.org/ftp/python/{WINDOWS_PYTHON_FULL_VERSION}/"
    f"python-{WINDOWS_PYTHON_FULL_VERSION}-amd64.exe"
)
WINGET_PYTHON_PACKAGE_ID = "Python.Python.3.13"


def _log_line(log: Callable[[str], None] | None, message: str) -> None:
    logger.info(message)
    if log is not None:
        log(message)


def _try_winget_install(log: Callable[[str], None] | None) -> bool:
    where = subprocess.run(
        ["where", "winget"],
        capture_output=True,
        text=True,
    )
    if where.returncode != 0:
        return False

    _log_line(log, "Installing Python 3.13 with winget (may take a few minutes)…")
    result = subprocess.run(
        [
            "winget",
            "install",
            "-e",
            "--id",
            WINGET_PYTHON_PACKAGE_ID,
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
            "--silent",
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        _log_line(log, f"winget install did not succeed ({result.returncode}).")
        if detail:
            _log_line(log, detail[:500])
        return False
    return True


def _download_python_installer(dest: Path, log: Callable[[str], None] | None) -> bool:
    _log_line(log, f"Downloading Python {WINDOWS_PYTHON_FULL_VERSION} from python.org…")
    try:
        urllib.request.urlretrieve(WINDOWS_PYTHON_INSTALLER_URL, dest)
    except OSError as exc:
        _log_line(log, f"Download failed: {exc}")
        return False
    if not dest.is_file() or dest.stat().st_size < 1_000_000:
        _log_line(log, "Downloaded file looks incomplete.")
        return False
    _log_line(log, f"Saved installer to {dest}")
    return True


def _run_python_installer(installer: Path, log: Callable[[str], None] | None) -> bool:
    _log_line(log, "Running the Python installer (quiet, per-user, adds to PATH)…")
    try:
        result = subprocess.run(
            [
                str(installer),
                "/quiet",
                "InstallAllUsers=0",
                "PrependPath=1",
                "Include_test=0",
                "Include_launcher=1",
            ],
            capture_output=True,
            text=True,
            timeout=900,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        _log_line(log, f"Python installer failed: {exc}")
        return False

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        _log_line(log, f"Python installer exited with code {result.returncode}.")
        if detail:
            _log_line(log, detail[:500])
        return False
    return True


def _install_python_windows(log: Callable[[str], None] | None) -> bool:
    if _try_winget_install(log):
        ok, _, _ = resolve_install_python()
        if ok:
            return True

    with tempfile.TemporaryDirectory(prefix="gridnotes-py-") as tmp:
        installer = Path(tmp) / f"python-{WINDOWS_PYTHON_FULL_VERSION}-amd64.exe"
        if not _download_python_installer(installer, log):
            return False
        if not _run_python_installer(installer, log):
            return False

    ok, _, _ = resolve_install_python()
    return ok


def ensure_supported_python_for_install(
    log: Callable[[str], None] | None = None,
) -> tuple[bool, str, str | None]:
    """
    Return a supported Python for building the GridNotes venv.

    On Windows, downloads and installs Python 3.13 if only 3.14 (or nothing
    supported) is available. Requires *some* Python on PATH to run this script
    (the install wizard uses 3.14 for that).
    """
    ok, message, executable = resolve_install_python()
    if ok and executable is not None:
        return True, message, executable

    if sys.platform != "win32":
        return False, message, None

    _log_line(
        log,
        "Supported Python (3.10–3.13) not found. "
        f"Attempting to install Python {WINDOWS_PYTHON_FULL_VERSION}…",
    )
    if _install_python_windows(log):
        ok, message, executable = resolve_install_python()
        if ok and executable is not None:
            return (
                True,
                f"{message}\n\n(Installed automatically for GridNotes.)",
                executable,
            )

    return (
        False,
        "Could not install Python 3.13 automatically.\n\n"
        "Install Python 3.12 or 3.13 manually from https://www.python.org/downloads/\n"
        '(check "Add python.exe to PATH"), delete D:\\GridNotes\\.venv if it exists,\n'
        "then run Install GridNotes.bat again.\n\n"
        f"You can also try in cmd: winget install -e --id {WINGET_PYTHON_PACKAGE_ID}",
        None,
    )
