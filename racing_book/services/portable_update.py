"""Download and apply GridNotes updates for installed copies (no git, not frozen)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

ProgressCallback = Callable[[str, int], None]

import requests

from ..installer.logic import (
    VENV_DIR_NAME,
    copy_source_to_install_root,
    relaunch_gridnotes,
    venv_python,
    windows_update_relaunch_batch_lines,
    write_gridnotes_start_script,
    write_windows_vbs_launcher,
)
from ..installer.uninstall import resolve_install_root
from .app_update import GITHUB_OWNER, GITHUB_REPO, REQUEST_TIMEOUT_SEC, _GITHUB_HEADERS, _normalize_tag

logger = logging.getLogger(__name__)

_UPDATE_LOG_NAME = "gridnotes-update.log"


def portable_install_root() -> Path | None:
    """Return the managed install folder if this run can be updated in place."""
    from .app_update import is_frozen_build, is_git_source_tree

    if is_frozen_build():
        return None
    root = resolve_install_root()
    if root is None:
        return None
    root = root.resolve()
    if is_git_source_tree(root):
        return None
    if not (root / "main.py").is_file():
        return None
    if not (root / VENV_DIR_NAME / ("Scripts" if sys.platform == "win32" else "bin")).is_dir():
        return None
    return root


def release_zipball_url(version: str) -> str:
    tag = (version or "").strip()
    if not tag.lower().startswith("v"):
        tag = f"v{tag}"
    return (
        f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/tags/{tag}.zip"
    )


def _update_log_path() -> Path:
    return Path(tempfile.gettempdir()) / _UPDATE_LOG_NAME


def _append_update_log(line: str) -> None:
    path = _update_log_path()
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line.rstrip() + "\n")
    except OSError:
        pass


def locate_release_source_root(extract_dir: Path) -> Path:
    """Find the extracted folder that contains main.py (GitHub zip has one top-level dir)."""
    extract_dir = extract_dir.resolve()
    if (extract_dir / "main.py").is_file():
        return extract_dir
    for child in sorted(extract_dir.iterdir()):
        if child.is_dir() and (child / "main.py").is_file():
            return child
    raise FileNotFoundError(f"No GridNotes source root under {extract_dir}")


def download_release_archive(
    version: str,
    dest_zip: Path,
    on_progress: ProgressCallback | None = None,
) -> None:
    url = release_zipball_url(version)
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading release archive: %s", url)
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
        with dest_zip.open("wb") as handle:
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
                        f"Downloading update… ({mb_done:.1f} / {mb_total:.1f} MB)",
                        percent,
                    )
                else:
                    on_progress("Downloading update…", 35)


def extract_release_archive(zip_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)
    return locate_release_source_root(extract_dir)


def _launch_windows_updater(bat_path: Path, vbs_path: Path) -> None:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    wscript = Path(system_root) / "System32" / "wscript.exe"
    if not wscript.is_file():
        wscript = Path("wscript.exe")
    try:
        subprocess.Popen(
            [str(wscript), "//B", "//Nologo", str(vbs_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            cwd=str(bat_path.parent),
        )
        return
    except OSError as exc:
        logger.warning("wscript launch failed: %s", exc)
    subprocess.Popen(
        ["cmd.exe", "/c", str(bat_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=str(bat_path.parent),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _write_windows_apply_batch(
    bat_path: Path,
    *,
    source_root: Path,
    install_root: Path,
    wait_pid: int,
    log_path: Path,
) -> None:
    src = str(source_root.resolve())
    dest = str(install_root.resolve())
    log_file = str(log_path.resolve())
    py = venv_python(install_root)
    relaunch_lines = windows_update_relaunch_batch_lines(install_root)
    relaunch_block = "\r\n".join(relaunch_lines)
    bat_path.write_text(
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        f'set "SRC={src}"\r\n'
        f'set "DEST={dest}"\r\n'
        f'set "LOG={log_file}"\r\n'
        f'set "PY={py}"\r\n'
        f"set \"WAITPID={wait_pid}\"\r\n"
        f'echo [%date% %time%] GridNotes update started>>"%LOG%"\r\n'
        ":wait_pid\r\n"
        'tasklist /FI "PID eq %WAITPID%" 2>nul | find "%WAITPID%" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  ping -n 2 127.0.0.1 >nul\r\n"
        "  goto wait_pid\r\n"
        ")\r\n"
        "ping -n 2 127.0.0.1 >nul\r\n"
        'echo [%date% %time%] Copying files...>>"%LOG%"\r\n'
        'robocopy "%SRC%" "%DEST%" /E /XD .venv dist build .git __pycache__ .cursor .pytest_cache '
        "/XF driver_history.db /NFL /NDL /NJH /NJS /NC /NS\r\n"
        "set \"ROBOCOPY_CODE=%ERRORLEVEL%\"\r\n"
        'echo [%date% %time%] robocopy exit code %ROBOCOPY_CODE%>>"%LOG%"\r\n'
        "if %ROBOCOPY_CODE% GEQ 8 (\r\n"
        '  echo [%date% %time%] robocopy failed, skipping pip and relaunch>>"%LOG%"\r\n'
        "  goto cleanup\r\n"
        ")\r\n"
        'echo [%date% %time%] Upgrading dependencies...>>"%LOG%"\r\n'
        '"%PY%" -m pip install -q -r "%DEST%\\requirements.txt" >>"%LOG%" 2>&1\r\n'
        'echo [%date% %time%] Registering Windows Apps entry...>>"%LOG%"\r\n'
        f'cd /d "{dest}"\r\n'
        '"%PY%" -c "from racing_book.installer.windows_apps import register_windows_uninstall; '
        "from racing_book.app.app_version import __version__; "
        'register_windows_uninstall(__import__(\'pathlib\').Path(r\'%DEST%\'), __version__)" '
        '>>"%LOG%" 2>&1\r\n'
        f"{relaunch_block}\r\n"
        'echo [%date% %time%] Update finished>>"%LOG%"\r\n'
        ":cleanup\r\n"
        f'rd /s /q "{src}" 2>nul\r\n'
        "del \"%~f0\"\r\n",
        encoding="utf-8",
    )


def _write_windows_apply_launcher(vbs_path: Path, bat_path: Path) -> None:
    bat_cmd = str(bat_path.resolve())
    vbs_path.write_text(
        'Set shell = CreateObject("WScript.Shell")\r\n'
        f'shell.Run "cmd.exe /c ""{bat_cmd}""", 0, False\r\n',
        encoding="utf-8",
    )


def _apply_on_unix(source_root: Path, install_root: Path) -> tuple[bool, str]:
    try:
        copy_source_to_install_root(source_root, install_root)
        py = venv_python(install_root / VENV_DIR_NAME)
        result = subprocess.run(
            [str(py), "-m", "pip", "install", "-r", str(install_root / "requirements.txt")],
            cwd=str(install_root),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            output = (result.stdout or result.stderr or "").strip()
            return False, output or "pip install failed."
        return True, "Update installed."
    except (OSError, subprocess.SubprocessError, shutil.Error) as exc:
        logger.exception("Unix portable update failed")
        return False, str(exc)
    finally:
        shutil.rmtree(source_root.parent, ignore_errors=True)


def apply_portable_update(
    install_root: Path,
    version: str,
    *,
    wait_pid: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[bool, str, bool]:
    """
    Download tag *version*, apply to *install_root*.

    Returns (ok, message, restart_in_process). On Windows the app should exit
    and a background script finishes the update and relaunches GridNotes.
    """
    install_root = install_root.resolve()
    version = _normalize_tag(version)
    if not version:
        return False, "No release version to install.", True

    pid = wait_pid if wait_pid is not None else os.getpid()
    temp_parent = Path(tempfile.gettempdir()) / f"gridnotes-update-{version}-{pid}"
    zip_path = temp_parent / "release.zip"
    extract_dir = temp_parent / "extract"
    staging_dir = temp_parent / "source"

    log_path = _update_log_path()
    _append_update_log(f"Portable update to v{version} for {install_root} (pid {pid})")

    def report(message: str, percent: int) -> None:
        if on_progress is not None:
            on_progress(message, percent)

    try:
        report("Preparing update…", 5)
        if temp_parent.exists():
            shutil.rmtree(temp_parent, ignore_errors=True)
        temp_parent.mkdir(parents=True, exist_ok=True)
        download_release_archive(version, zip_path, on_progress=on_progress)
        report("Extracting release…", 65)
        source_root = extract_release_archive(zip_path, extract_dir)
        report("Preparing files…", 75)
        # Stage a clean tree for robocopy (extract dir may contain extra nesting).
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        copy_source_to_install_root(source_root, staging_dir)
        shutil.rmtree(extract_dir, ignore_errors=True)
        zip_path.unlink(missing_ok=True)
    except (requests.RequestException, OSError, zipfile.BadZipFile, FileNotFoundError) as exc:
        logger.exception("Failed to download or extract release")
        shutil.rmtree(temp_parent, ignore_errors=True)
        return False, f"Could not download the update: {exc}", True

    if sys.platform == "win32":
        report("Installing update (GridNotes will close)…", 88)
        venv_dir = install_root / VENV_DIR_NAME
        write_gridnotes_start_script(install_root)
        if venv_dir.is_dir():
            write_windows_vbs_launcher(install_root, venv_dir)
        bat_path = temp_parent / "apply-update.bat"
        vbs_path = temp_parent / "apply-update.vbs"
        _write_windows_apply_batch(
            bat_path,
            source_root=staging_dir,
            install_root=install_root,
            wait_pid=pid,
            log_path=log_path,
        )
        _write_windows_apply_launcher(vbs_path, bat_path)
        _append_update_log(f"Scheduled update batch: {bat_path}")
        _launch_windows_updater(bat_path, vbs_path)
        report("Closing GridNotes to finish installing…", 100)
        return (
            True,
            "GridNotes will close and reopen when the update is ready. "
            f"Details: {log_path}",
            False,
        )

    report("Installing files…", 85)
    ok, message = _apply_on_unix(staging_dir, install_root)
    if ok:
        report("Reopening GridNotes…", 95)
        if not relaunch_gridnotes(install_root):
            message = f"{message}\n\nCould not reopen GridNotes automatically."
        report("Finishing…", 100)
    return ok, message, False
