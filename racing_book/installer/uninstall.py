"""Remove an installed copy of GridNotes (install folder, shortcut, optional user data)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .logic import install_location_pointer_file
from .shortcuts import APP_SHORTCUT_NAME, desktop_directory, remove_desktop_shortcut
from ..data.db import get_data_dir_path
from ..data.user_paths import data_dir_candidates

logger = logging.getLogger(__name__)


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


def read_registered_install_root() -> Path | None:
    """Install folder recorded by Install GridNotes.bat (if any)."""
    pointer = install_location_pointer_file()
    if not pointer.is_file():
        return None
    text = pointer.read_text(encoding="utf-8").strip()
    if not text:
        return None
    root = Path(text)
    if not root.is_dir():
        return None
    if not (root / "main.py").is_file():
        return None
    if not (root / ".venv").is_dir() and not (root / "gridnotes_start.py").is_file():
        return None
    return root.resolve()


def _running_from_directory(directory: Path) -> bool:
    directory = directory.resolve()
    try:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().is_relative_to(directory)
        return Path(__file__).resolve().is_relative_to(directory)
    except (ValueError, OSError):
        return False


def _schedule_install_folder_removal(install_root: Path) -> None:
    """Delete install folder after this process exits (venv files may be locked)."""
    install_root = install_root.resolve()
    if sys.platform == "win32":
        bat = Path(tempfile.gettempdir()) / "gridnotes-uninstall-cleanup.bat"
        bat.write_text(
            "@echo off\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            f'if exist "{install_root}" rd /s /q "{install_root}"\r\n'
            "del \"%~f0\"\r\n",
            encoding="utf-8",
        )
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            ["cmd.exe", "/c", str(bat)],
            creationflags=flags,
        )
        return

    sh = Path(tempfile.gettempdir()) / "gridnotes-uninstall-cleanup.sh"
    sh.write_text(
        "#!/bin/bash\n"
        "sleep 2\n"
        f'rm -rf "{install_root}"\n'
        'rm -f "$0"\n',
        encoding="utf-8",
    )
    sh.chmod(0o755)
    subprocess.Popen(["/bin/bash", str(sh)])


def _remove_install_pointer() -> None:
    pointer = install_location_pointer_file()
    if pointer.is_file():
        pointer.unlink(missing_ok=True)


def _remove_install_folder(install_root: Path) -> tuple[bool, str, bool]:
    install_root = install_root.resolve()
    if not install_root.is_dir():
        return True, "Install folder was already removed.", False

    must_defer = _running_from_directory(install_root)
    if not must_defer:
        try:
            shutil.rmtree(install_root)
            return True, f"Removed install folder:\n{install_root}", False
        except OSError as exc:
            logger.warning("Immediate install removal failed: %s", exc)
            must_defer = True

    _schedule_install_folder_removal(install_root)
    return (
        True,
        "Install folder will be removed after GridNotes closes:\n"
        f"{install_root}",
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
            shutil.rmtree(resolved)
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

    try:
        if remove_desktop_shortcut():
            result.shortcut_removed = True
            result.messages.append("Removed the Desktop shortcut.")
        else:
            desktop = desktop_directory()
            hint = desktop / f"{APP_SHORTCUT_NAME}.lnk"
            if sys.platform != "win32":
                hint = desktop / "Run GridNotes.command"
            result.messages.append(f"No Desktop shortcut found ({hint}).")
    except OSError as exc:
        result.ok = False
        result.messages.append(f"Could not remove Desktop shortcut:\n{exc}")

    if install_root is not None:
        _remove_install_pointer()
        ok, message, deferred = _remove_install_folder(install_root)
        result.install_removed = ok
        result.install_removal_deferred = deferred
        result.messages.append(message)
        if not ok:
            result.ok = False

    if remove_user_data:
        ok, message = _remove_user_data()
        result.user_data_removed = ok and "Removed:" in message
        result.messages.append(message)
        if not ok:
            result.ok = False
    elif install_root is None and not result.shortcut_removed:
        result.ok = False
        result.messages.append(
            "Nothing to uninstall. GridNotes may be running from source without "
            "using Install GridNotes.bat."
        )

    return result
