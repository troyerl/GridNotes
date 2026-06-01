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


def _schedule_install_folder_removal(install_root: Path) -> Path:
    """Delete install folder after this process exits (venv files may be locked)."""
    install_root = install_root.resolve()
    log_path = _cleanup_log_path()
    log_ps = str(log_path).replace("'", "''")
    target_ps = str(install_root).replace("'", "''")

    if sys.platform == "win32":
        script = (
            f"$log = '{log_ps}'\n"
            f"$target = '{target_ps}'\n"
            "Add-Content -LiteralPath $log \"Cleanup started $(Get-Date)\"\n"
            "Start-Sleep -Seconds 8\n"
            "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Name -match 'python(w)?\\.exe' -and $_.CommandLine -and "
            "($_.CommandLine -like \"*$target*\") } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }\n"
            "Start-Sleep -Seconds 2\n"
            "if (Test-Path -LiteralPath $target) {\n"
            "  Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue\n"
            "}\n"
            "if (Test-Path -LiteralPath $target) {\n"
            "  Add-Content -LiteralPath $log \"FAILED: folder still exists: $target\"\n"
            "} else {\n"
            "  Add-Content -LiteralPath $log \"OK: removed $target\"\n"
            "}\n"
        )
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-Command",
                script,
            ],
            creationflags=flags,
        )
        return log_path

    sh = Path(tempfile.gettempdir()) / "gridnotes-uninstall-cleanup.sh"
    sh.write_text(
        "#!/bin/bash\n"
        "sleep 8\n"
        f'rm -rf "{install_root}"\n'
        f'echo "OK: removed {install_root}" >> "{log_path}"\n'
        'rm -f "$0"\n',
        encoding="utf-8",
    )
    sh.chmod(0o755)
    subprocess.Popen(["/bin/bash", str(sh)])
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

    running_from_install = _running_from_directory(install_root)
    if not running_from_install:
        try:
            _force_rmtree(install_root)
            if not install_root.is_dir():
                return True, f"Removed install folder:\n{install_root}", False
        except OSError as exc:
            logger.warning("Immediate install removal failed: %s", exc)

    log_path = _schedule_install_folder_removal(install_root)
    return (
        True,
        "Install folder will be removed after GridNotes closes:\n"
        f"{install_root}\n\n"
        f"If it remains, delete that folder manually or check:\n{log_path}",
        True,
    )


def _remove_user_data() -> tuple[bool, str]:
    removed_any = False
    messages: list[str] = []
    errors: list[str] = []

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
                "Close GridNotes and delete this folder manually."
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
