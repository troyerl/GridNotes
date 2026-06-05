"""Silent GridNotes-Setup.exe updates for Windows installer installs."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import requests

from ..services.app_update import REQUEST_TIMEOUT_SEC, _GITHUB_HEADERS, _normalize_tag
from .logic import (
    needs_elevated_windows_update,
    windows_update_pointer_batch_lines,
    windows_update_relaunch_batch_lines,
)
from .frozen_update import download_release_file
from .portable_update import (
    ProgressCallback,
    _append_update_log,
    _launch_windows_updater,
    _safe_rmtree,
    _write_windows_apply_launcher,
)
from .update_paths import prune_old_update_workspaces, update_log_path, update_workspace_dir

logger = logging.getLogger(__name__)

# Inno Setup silent flags (see Inno Setup /VERYSILENT documentation).
# /NORESTART — we relaunch GridNotes from the batch after a successful install.
_INNO_SILENT_FLAGS = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS"


def apply_installer_update(
    install_root: Path,
    version: str,
    *,
    setup_url: str,
    wait_pid: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[bool, str, bool]:
    """
    Download GridNotes-Setup.exe and run it silently after the app exits.

    Returns (ok, message, restart_in_process).
    """
    if sys.platform != "win32":
        return (
            False,
            "Automatic installer updates are only supported on Windows.",
            True,
        )

    install_root = install_root.resolve()
    version = _normalize_tag(version)
    if not version or not setup_url.strip():
        return False, "No installer download is available for this version.", True

    pid = wait_pid if wait_pid is not None else os.getpid()
    prune_old_update_workspaces()
    temp_parent = update_workspace_dir(version=version, pid=pid, kind="installer")
    setup_path = temp_parent / "GridNotes-Setup.exe"
    log_path = update_log_path()
    _append_update_log(
        f"Installer update to v{version} for {install_root} (pid {pid})"
    )

    def report(message: str, percent: int) -> None:
        if on_progress is not None:
            on_progress(message, percent)

    try:
        report("Preparing update…", 5)
        temp_parent.mkdir(parents=True, exist_ok=True)
        download_release_file(setup_url, setup_path, on_progress=on_progress)
    except (requests.RequestException, OSError) as exc:
        logger.exception("Failed to download installer")
        _safe_rmtree(temp_parent)
        from .user_messages import portable_update_failed_message

        return False, portable_update_failed_message(), True

    if not setup_path.is_file():
        _safe_rmtree(temp_parent)
        from .user_messages import portable_update_failed_message

        return False, portable_update_failed_message(), True

    report("Installing update (GridNotes will close)…", 88)
    bat_path = temp_parent / "apply-installer-update.bat"
    vbs_path = temp_parent / "apply-installer-update.vbs"
    _write_installer_apply_batch(
        bat_path,
        setup_exe=setup_path,
        install_root=install_root,
        workspace_root=temp_parent,
        wait_pid=pid,
        log_path=log_path,
        release_version=version,
    )
    _write_windows_apply_launcher(vbs_path, bat_path)
    _append_update_log(f"Scheduled installer update batch: {bat_path}")
    time.sleep(0.5)
    _launch_windows_updater(bat_path, vbs_path)
    report("Closing GridNotes to finish installing…", 100)
    from .user_messages import portable_update_scheduled_message

    _append_update_log(f"Update log: {log_path}")
    return (
        True,
        portable_update_scheduled_message(
            requires_windows_permission=needs_elevated_windows_update(install_root)
        ),
        False,
    )


def _write_installer_apply_batch(
    bat_path: Path,
    *,
    setup_exe: Path,
    install_root: Path,
    workspace_root: Path,
    wait_pid: int,
    log_path: Path,
    release_version: str,
) -> None:
    setup = str(setup_exe.resolve())
    dest = str(install_root.resolve())
    workspace = str(workspace_root.resolve())
    log_file = str(log_path.resolve())
    pointer_lines = "".join(windows_update_pointer_batch_lines(install_root))
    relaunch_block = "\r\n".join(windows_update_relaunch_batch_lines(install_root))
    bat_path.write_text(
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        f'set "SETUP={setup}"\r\n'
        f'set "DEST={dest}"\r\n'
        f'set "WORKSPACE={workspace}"\r\n'
        f'set "LOG={log_file}"\r\n'
        f"set \"WAITPID={wait_pid}\"\r\n"
        f'echo [%date% %time%] GridNotes installer update started>>"%LOG%"\r\n'
        ":wait_pid\r\n"
        'tasklist /FI "PID eq %WAITPID%" 2>nul | find "%WAITPID%" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  ping -n 2 127.0.0.1 >nul\r\n"
        "  goto wait_pid\r\n"
        ")\r\n"
        "ping -n 3 127.0.0.1 >nul\r\n"
        f'echo [%date% %time%] Running silent installer for v{release_version}>>"%LOG%"\r\n'
        f'"%SETUP%" {_INNO_SILENT_FLAGS} /DIR="%DEST%" /LOG="{log_file}.inno.txt"\r\n'
        "set \"SETUP_CODE=%ERRORLEVEL%\"\r\n"
        'echo [%date% %time%] Installer exit code %SETUP_CODE%>>"%LOG%"\r\n'
        "if not %SETUP_CODE%==0 goto cleanup\r\n"
        f'echo {release_version}>"%DEST%\\.gridnotes-version"\r\n'
        f"{pointer_lines}"
        'echo [%date% %time%] Installer update finished>>"%LOG%"\r\n'
        f"{relaunch_block}\r\n"
        ":cleanup\r\n"
        "cd /d %TEMP%\r\n"
        'rd /s /q "%WORKSPACE%" 2>nul\r\n'
        "exit /b\r\n",
        encoding="utf-8",
    )
