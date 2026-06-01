"""Remove an installed copy of GridNotes (install folder, shortcut, optional user data)."""

from __future__ import annotations

import logging
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .logic import find_project_root, install_location_pointer_file
from .shortcuts import remove_all_desktop_shortcuts
from .windows_apps import unregister_windows_uninstall

from ..data.db import get_data_dir_path
from ..data.user_paths import data_dir_candidates

logger = logging.getLogger(__name__)

_CLEANUP_LOG_NAME = "gridnotes-uninstall.log"


@dataclass
class UninstallResult:
    ok: bool
    messages: list[str] = field(default_factory=list)
    install_removed: bool = False
    install_removal_deferred: bool = False
    user_data_removed: bool = False
    shortcut_removed: bool = False

    def summary(self) -> str:
        return "\n\n".join(self.messages)


def _looks_like_install_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    if not (path / "main.py").is_file():
        return False
    return any(
        (path / marker).exists()
        for marker in (".venv", "gridnotes_start.py", "Launch GridNotes.vbs", "Run GridNotes.bat")
    )


def _detect_install_root_from_runtime() -> Path | None:
    if getattr(sys, "frozen", False):
        candidate = Path(sys.executable).resolve().parent
        if _looks_like_install_root(candidate):
            return candidate

    if sys.argv:
        arg0 = Path(sys.argv[0]).resolve()
        if arg0.name in ("gridnotes_start.py", "main.py") and _looks_like_install_root(arg0.parent):
            return arg0.parent
        if arg0.name.lower() in ("python.exe", "pythonw.exe") and arg0.parent.name == "Scripts":
            install_root = arg0.parent.parent.parent
            if _looks_like_install_root(install_root):
                return install_root

    try:
        root = find_project_root()
        if _looks_like_install_root(root):
            return root.resolve()
    except Exception:
        pass
    return None


def _known_install_candidates() -> list[Path]:
    candidates: list[Path] = []
    if sys.platform != "win32":
        return candidates

    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        candidates.append(Path(f"{letter}:\\GridNotes"))

    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        candidates.append(Path(local) / "Programs" / "GridNotes")

    for key in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        value = os.environ.get(key, "").strip()
        if value:
            candidates.append(Path(value) / "GridNotes")

    return candidates


def resolve_install_root() -> Path | None:
    """Find the installed GridNotes folder (pointer file, running app, or common paths)."""
    pointer = install_location_pointer_file()
    if pointer.is_file():
        text = pointer.read_text(encoding="utf-8").strip()
        if text:
            registered = Path(text)
            if _looks_like_install_root(registered):
                return registered.resolve()

    runtime = _detect_install_root_from_runtime()
    if runtime is not None:
        return runtime

    for candidate in _known_install_candidates():
        if _looks_like_install_root(candidate):
            return candidate.resolve()

    return None


def read_registered_install_root() -> Path | None:
    """Backward-compatible alias for :func:`resolve_install_root`."""
    return resolve_install_root()


def _runtime_paths() -> list[Path]:
    paths: list[Path] = []
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve())
    try:
        paths.append(Path(sys.executable).resolve())
    except OSError:
        pass
    if sys.argv:
        paths.append(Path(sys.argv[0]).resolve())
    try:
        paths.append(Path.cwd().resolve())
    except OSError:
        pass
    return paths


def _running_from_directory(directory: Path) -> bool:
    directory = directory.resolve()
    for path in _runtime_paths():
        try:
            if path.is_relative_to(directory):
                return True
        except (ValueError, OSError):
            continue
    return False


def _cleanup_log_path() -> Path:
    return Path(tempfile.gettempdir()) / _CLEANUP_LOG_NAME


def _append_cleanup_log(log_path: Path, message: str) -> None:
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message)
            if not message.endswith("\n"):
                handle.write("\n")
    except OSError:
        pass


def _bat_quote(path: Path) -> str:
    return str(path.resolve())


def _write_folder_removal_batch(
    bat_path: Path,
    *,
    install_root: Path,
    wait_pid: int,
    log_path: Path,
) -> None:
    target = _bat_quote(install_root)
    log_file = _bat_quote(log_path)
    bat_path.write_text(
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        f'set "TARGET={target}"\r\n'
        f'set "LOG={log_file}"\r\n'
        f"set \"WAITPID={wait_pid}\"\r\n"
        f'echo [%date% %time%] Cleanup batch started>>"%LOG%"\r\n'
        f'echo TARGET=%TARGET% WAITPID=%WAITPID%>>"%LOG%"\r\n'
        ":wait_pid\r\n"
        'tasklist /FI "PID eq %WAITPID%" 2>nul | find "%WAITPID%" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  ping -n 2 127.0.0.1 >nul\r\n"
        "  goto wait_pid\r\n"
        ")\r\n"
        'echo [%date% %time%] Uninstall process ended>>"%LOG%"\r\n'
        "ping -n 3 127.0.0.1 >nul\r\n"
        ":try_remove\r\n"
        'if not exist "%TARGET%" goto removed\r\n'
        'echo [%date% %time%] Removing %TARGET%...>>"%LOG%"\r\n'
        'rd /s /q "%TARGET%" 2>>"%LOG%"\r\n'
        'if exist "%TARGET%" (\r\n'
        "  powershell -NoProfile -ExecutionPolicy Bypass -Command "
        '"Remove-Item -LiteralPath ''%TARGET%'' -Recurse -Force" >>"%LOG%" 2>&1\r\n'
        ")\r\n"
        'if exist "%TARGET%" (\r\n'
        '  echo [%date% %time%] takeown/icacls>>"%LOG%"\r\n'
        '  takeown /f "%TARGET%" /r /d y >>"%LOG%" 2>&1\r\n'
        '  icacls "%TARGET%" /grant "%USERNAME%:(F)" /t /c >>"%LOG%" 2>&1\r\n'
        '  rd /s /q "%TARGET%" 2>>"%LOG%"\r\n'
        ")\r\n"
        'if exist "%TARGET%" (\r\n'
        '  echo [%date% %time%] FAILED: %TARGET% still exists>>"%LOG%"\r\n'
        "  goto done\r\n"
        ")\r\n"
        ":removed\r\n"
        'echo [%date% %time%] OK: removed %TARGET%>>"%LOG%"\r\n'
        ":done\r\n"
        "del \"%~f0\"\r\n",
        encoding="utf-8",
    )


def _write_folder_removal_launcher_vbs(vbs_path: Path, bat_path: Path) -> None:
    bat_cmd = str(bat_path.resolve())
    vbs_path.write_text(
        'Set shell = CreateObject("WScript.Shell")\r\n'
        f'shell.Run "cmd.exe /c ""{bat_cmd}""", 0, False\r\n',
        encoding="utf-8",
    )


def _register_runonce_cleanup(bat_path: Path, log_path: Path) -> None:
    """If the background batch never runs, delete the folder at next sign-in."""
    if sys.platform != "win32":
        return
    import winreg

    command = f'"{bat_path.resolve()}"'
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "GridNotesCleanup", 0, winreg.REG_SZ, command)
        _append_cleanup_log(
            log_path,
            f"Registered RunOnce backup: {command}",
        )
    except OSError as exc:
        _append_cleanup_log(log_path, f"RunOnce registration failed: {exc}")


def _launch_folder_removal_worker(bat_path: Path, vbs_path: Path, log_path: Path) -> None:
    """Start cleanup via wscript (reliable) with a direct cmd.exe fallback."""
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    wscript = Path(system_root) / "System32" / "wscript.exe"
    if not wscript.is_file():
        wscript = Path("wscript.exe")

    launched = False
    try:
        subprocess.Popen(
            [str(wscript), "//B", "//Nologo", str(vbs_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            cwd=str(bat_path.parent),
        )
        launched = True
        _append_cleanup_log(log_path, f"Started cleanup launcher: {vbs_path}")
    except OSError as exc:
        _append_cleanup_log(log_path, f"wscript launch failed: {exc}")

    if not launched:
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", str(bat_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                cwd=str(bat_path.parent),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            _append_cleanup_log(log_path, f"Started cleanup batch directly: {bat_path}")
        except OSError as exc:
            _append_cleanup_log(log_path, f"cmd launch failed: {exc}")


def _schedule_install_folder_removal(install_root: Path, *, wait_pid: int) -> Path:
    """
    Delete *install_root* after process *wait_pid* exits.

    Uninstall runs from .venv inside the install folder, so the folder cannot be
    deleted until this Python process has fully exited.
    """
    install_root = install_root.resolve()
    log_path = _cleanup_log_path()
    _append_cleanup_log(
        log_path,
        f"Scheduled removal of {install_root} after PID {wait_pid} exits.",
    )

    if sys.platform == "win32":
        temp_dir = Path(tempfile.gettempdir())
        bat_path = temp_dir / f"gridnotes-remove-{wait_pid}.bat"
        vbs_path = temp_dir / f"gridnotes-remove-{wait_pid}.vbs"
        _write_folder_removal_batch(
            bat_path,
            install_root=install_root,
            wait_pid=wait_pid,
            log_path=log_path,
        )
        _write_folder_removal_launcher_vbs(vbs_path, bat_path)
        _append_cleanup_log(log_path, f"Cleanup batch: {bat_path}")
        _append_cleanup_log(log_path, f"Cleanup launcher: {vbs_path}")
        _launch_folder_removal_worker(bat_path, vbs_path, log_path)
        _register_runonce_cleanup(bat_path, log_path)
        return log_path

    sh = Path(tempfile.gettempdir()) / f"gridnotes-remove-{wait_pid}.sh"
    sh.write_text(
        "#!/bin/bash\n"
        f"TARGET='{install_root}'\n"
        f"LOG='{log_path}'\n"
        f"WAITPID={wait_pid}\n"
        "while kill -0 \"$WAITPID\" 2>/dev/null; do sleep 1; done\n"
        "sleep 2\n"
        "rm -rf \"$TARGET\" && echo \"OK: removed $TARGET\" >> \"$LOG\" "
        "|| echo \"FAILED: $TARGET\" >> \"$LOG\"\n"
        "rm -f \"$0\"\n",
        encoding="utf-8",
    )
    sh.chmod(0o755)
    subprocess.Popen(["/bin/bash", str(sh)], close_fds=True)
    return log_path


def _chmod_and_retry(func, path: str, exc_info) -> None:
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR | stat.S_IREAD)
        func(path)
    else:
        raise exc_info[1]


def _force_rmtree(path: Path) -> None:
    shutil.rmtree(path, onerror=_chmod_and_retry)


def _remove_install_pointer() -> None:
    pointer = install_location_pointer_file()
    if pointer.is_file():
        pointer.unlink(missing_ok=True)


def _remove_install_folder(install_root: Path) -> tuple[bool, str, bool]:
    install_root = install_root.resolve()
    if not install_root.is_dir():
        return True, "Install folder was already removed.", False

    executable_under_install = False
    try:
        executable_under_install = Path(sys.executable).resolve().is_relative_to(install_root)
    except (ValueError, OSError):
        pass

    # Uninstall almost always runs from inside the install tree (.venv); wait for exit.
    if _running_from_directory(install_root) or executable_under_install:
        log_path = _schedule_install_folder_removal(install_root, wait_pid=os.getpid())
        return (
            True,
            "The install folder will be deleted when you close this window:\n"
            f"{install_root}\n\n"
            f"(If {install_root} remains, delete it manually or see {log_path})",
            True,
        )

    try:
        _force_rmtree(install_root)
        if not install_root.is_dir():
            return True, f"Removed install folder:\n{install_root}", False
    except OSError as exc:
        logger.warning("Immediate install removal failed: %s", exc)

    log_path = _schedule_install_folder_removal(install_root, wait_pid=os.getpid())
    return (
        True,
        "Install folder will be removed shortly:\n"
        f"{install_root}\n\n"
        f"If it remains, delete it manually or check:\n{log_path}",
        True,
    )


def _remove_user_data() -> tuple[bool, str]:
    removed_any = False
    messages: list[str] = []
    errors: list[str] = []

    try:
        from ..services.log_config import shutdown_logging

        shutdown_logging()
    except Exception as exc:
        logger.warning("Could not release log file before uninstall: %s", exc)

    try:
        primary = get_data_dir_path()
        targets = [primary, *data_dir_candidates(include_legacy=True)]
    except OSError as exc:
        return False, f"Could not locate your data folder:\n{exc}"

    seen: set[Path] = set()
    for folder in targets:
        try:
            resolved = folder.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        try:
            _force_rmtree(resolved)
            removed_any = True
            messages.append(f"Removed:\n{resolved}")
        except OSError as exc:
            errors.append(f"{resolved}\n  {exc}")

    if errors:
        detail = "\n\n".join(errors)
        if removed_any:
            return False, "\n\n".join(messages) + f"\n\nSome folders could not be removed:\n{detail}"
        return False, f"Could not remove your data:\n{detail}"

    if not removed_any:
        return True, "No user data folders were found to remove."

    return True, "\n\n".join(messages)


def perform_uninstall(
    *,
    install_root: Path | None,
    remove_user_data: bool,
) -> UninstallResult:
    """Uninstall GridNotes. Call after closing the database connection."""
    result = UninstallResult(ok=True)

    removed_shortcuts = remove_all_desktop_shortcuts()
    if removed_shortcuts:
        result.shortcut_removed = True
        lines = "\n".join(f"  • {path}" for path in removed_shortcuts)
        result.messages.append(f"Removed Desktop shortcut(s):\n{lines}")
    else:
        result.messages.append(
            "No Desktop shortcut was found (checked Desktop and OneDrive Desktop)."
        )

    if install_root is not None:
        _remove_install_pointer()
        ok, message, deferred = _remove_install_folder(install_root)
        result.install_removed = ok and not deferred and not install_root.is_dir()
        result.install_removal_deferred = deferred
        result.messages.append(message)
        if not ok:
            result.ok = False
        elif not deferred and install_root.is_dir():
            result.ok = False
            result.messages.append(
                f"Install folder could not be removed:\n{install_root}\n"
                "Delete this folder manually in File Explorer."
            )
    else:
        result.messages.append(
            "Could not find the install folder automatically. "
            "Delete your GridNotes install folder manually (for example D:\\GridNotes)."
        )
        if not result.shortcut_removed and not remove_user_data:
            result.ok = False

    if remove_user_data:
        ok, message = _remove_user_data()
        result.user_data_removed = ok and "Removed:" in message
        result.messages.append(message)
        if not ok:
            result.ok = False

    unregister_windows_uninstall(install_root)
    result.messages.append("Removed GridNotes from Windows Settings → Apps.")

    return result
