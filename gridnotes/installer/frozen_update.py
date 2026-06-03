"""Download and apply GitHub release ZIP updates for PyInstaller (frozen) installs."""

from __future__ import annotations

import logging
import os
import sys
import time
import zipfile
from pathlib import Path

import requests

from ..services.app_update import REQUEST_TIMEOUT_SEC, _GITHUB_HEADERS, _normalize_tag
from .logic import (
    needs_elevated_windows_update,
    windows_update_pointer_batch_lines,
    windows_update_relaunch_batch_lines,
)
from .portable_update import (
    ProgressCallback,
    _append_update_log,
    _launch_windows_updater,
    _safe_rmtree,
    _write_windows_apply_launcher,
)
from .update_paths import prune_old_update_workspaces, update_log_path, update_workspace_dir

logger = logging.getLogger(__name__)


def frozen_install_root() -> Path | None:
    """Folder containing the running GridNotes.exe (frozen / installer build)."""
    from ..services.app_update import is_frozen_build

    if not is_frozen_build():
        return None
    root = Path(sys.executable).resolve().parent
    if root.is_dir() and (root / "GridNotes.exe").is_file():
        return root
    from ..platform.windows.windows_apps import registry_install_root

    return registry_install_root()


def locate_frozen_release_root(extract_dir: Path) -> Path:
    """Find GridNotes.exe inside an extracted release ZIP."""
    extract_dir = extract_dir.resolve()
    if (extract_dir / "GridNotes.exe").is_file():
        return extract_dir
    for child in sorted(extract_dir.iterdir()):
        if child.is_dir() and (child / "GridNotes.exe").is_file():
            return child
    raise FileNotFoundError(f"No GridNotes.exe in extracted release under {extract_dir}")


def download_release_file(
    url: str,
    dest: Path,
    on_progress: ProgressCallback | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading release asset: %s", url)
    if on_progress is not None:
        on_progress("Connecting to GitHub…", 8)
    with requests.get(
        url,
        headers=_GITHUB_HEADERS,
        stream=True,
        timeout=REQUEST_TIMEOUT_SEC,
    ) as response:
        response.raise_for_status()
        total_bytes = int(response.headers.get("content-length", 0) or 0)
        downloaded = 0
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                if on_progress is None:
                    continue
                if total_bytes > 0:
                    fraction = downloaded / total_bytes
                    percent = 10 + int(50 * fraction)
                    mb_done = downloaded / (1024 * 1024)
                    mb_total = total_bytes / (1024 * 1024)
                    on_progress(
                        f"Updating… ({mb_done:.1f} / {mb_total:.1f} MB)",
                        percent,
                    )
                else:
                    on_progress("Updating…", 35)


def extract_frozen_release(zip_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)
    return locate_frozen_release_root(extract_dir)


def _write_frozen_apply_batch(
    bat_path: Path,
    *,
    source_root: Path,
    install_root: Path,
    wait_pid: int,
    log_path: Path,
    release_version: str,
) -> None:
    src = str(source_root.resolve())
    dest = str(install_root.resolve())
    log_file = str(log_path.resolve())
    exe = str((install_root / "GridNotes.exe").resolve())
    pointer_lines = "".join(windows_update_pointer_batch_lines(install_root))
    relaunch_block = "\r\n".join(windows_update_relaunch_batch_lines(install_root))
    bat_path.write_text(
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        f'set "SRC={src}"\r\n'
        f'set "DEST={dest}"\r\n'
        f'set "LOG={log_file}"\r\n'
        f"set \"WAITPID={wait_pid}\"\r\n"
        f'echo [%date% %time%] GridNotes frozen update started>>"%LOG%"\r\n'
        ":wait_pid\r\n"
        'tasklist /FI "PID eq %WAITPID%" 2>nul | find "%WAITPID%" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  ping -n 2 127.0.0.1 >nul\r\n"
        "  goto wait_pid\r\n"
        ")\r\n"
        "ping -n 8 127.0.0.1 >nul\r\n"
        'echo [%date% %time%] Preparing destination folder...>>"%LOG%"\r\n'
        'if exist "%DEST%\\GridNotes.exe" (\r\n'
        '  del /f /q "%DEST%\\GridNotes.exe.old" 2>nul\r\n'
        '  move /y "%DEST%\\GridNotes.exe" "%DEST%\\GridNotes.exe.old" 2>nul\r\n'
        ")\r\n"
        'echo [%date% %time%] Copying application files...>>"%LOG%"\r\n'
        'robocopy "%SRC%" "%DEST%" /E /NFL /NDL /NJH /NJS /NC /NS /R:2 /W:2\r\n'
        "set \"ROBOCOPY_CODE=%ERRORLEVEL%\"\r\n"
        'echo [%date% %time%] robocopy exit code %ROBOCOPY_CODE%>>"%LOG%"\r\n'
        "if %ROBOCOPY_CODE% GEQ 8 (\r\n"
        '  echo [%date% %time%] robocopy failed>>"%LOG%"\r\n'
        "  goto cleanup\r\n"
        ")\r\n"
        'del /f /q "%DEST%\\GridNotes.exe.old" 2>nul\r\n'
        f'echo {release_version}>"%DEST%\\.gridnotes-version"\r\n'
        f"{pointer_lines}"
        'echo [%date% %time%] Update finished>>"%LOG%"\r\n'
        f"{relaunch_block}\r\n"
        ":cleanup\r\n"
        f'rd /s /q "{src}" 2>nul\r\n'
        "del \"%~f0\"\r\n",
        encoding="utf-8",
    )


def apply_frozen_update(
    install_root: Path,
    version: str,
    *,
    zip_url: str,
    wait_pid: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[bool, str, bool]:
    """
    Download the release ZIP and replace the install folder in place.

    Returns (ok, message, restart_in_process). On Windows the app exits and a
    background script finishes the update and relaunches GridNotes.exe.
    """
    if sys.platform != "win32":
        return (
            False,
            "Automatic updates for the installed app are only supported on Windows.",
            True,
        )

    install_root = install_root.resolve()
    version = _normalize_tag(version)
    if not version or not zip_url.strip():
        return False, "No release download is available for this version.", True

    pid = wait_pid if wait_pid is not None else os.getpid()
    prune_old_update_workspaces()
    temp_parent = update_workspace_dir(version=version, pid=pid, kind="frozen")
    zip_path = temp_parent / "release.zip"
    extract_dir = temp_parent / "extract"
    log_path = update_log_path()
    _append_update_log(f"Frozen update to v{version} for {install_root} (pid {pid})")

    def report(message: str, percent: int) -> None:
        if on_progress is not None:
            on_progress(message, percent)

    try:
        report("Preparing update…", 5)
        temp_parent.mkdir(parents=True, exist_ok=True)
        download_release_file(zip_url, zip_path, on_progress=on_progress)
        report("Extracting release…", 65)
        source_root = extract_frozen_release(zip_path, extract_dir)
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
    except (requests.RequestException, OSError, zipfile.BadZipFile, FileNotFoundError) as exc:
        logger.exception("Failed to download or extract frozen release")
        _safe_rmtree(temp_parent)
        from .user_messages import portable_update_failed_message

        return False, portable_update_failed_message(), True

    report("Installing update (GridNotes will close)…", 88)
    bat_path = temp_parent / "apply-frozen-update.bat"
    vbs_path = temp_parent / "apply-frozen-update.vbs"
    _write_frozen_apply_batch(
        bat_path,
        source_root=source_root,
        install_root=install_root,
        wait_pid=pid,
        log_path=log_path,
        release_version=version,
    )
    _write_windows_apply_launcher(
        vbs_path,
        bat_path,
        elevate=needs_elevated_windows_update(install_root),
    )
    _append_update_log(f"Scheduled frozen update batch: {bat_path}")
    time.sleep(0.5)
    _launch_windows_updater(bat_path, vbs_path)
    report("Closing GridNotes to finish installing…", 100)
    from .user_messages import portable_update_scheduled_message

    message = portable_update_scheduled_message()
    if needs_elevated_windows_update(install_root):
        message += (
            "\n\nWindows may ask once for permission to finish installing in the background."
        )
    _append_update_log(f"Update log: {log_path}")
    return True, message, False
