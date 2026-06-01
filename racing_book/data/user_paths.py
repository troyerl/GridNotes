"""Pick a per-user folder the current Windows/macOS/Linux user can actually write."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP_NAME = "GridNotes"
LEGACY_APP_NAME = "RacingBook"


def _probe_writable(directory: Path) -> bool:
    """Return True if we can create the folder and write a small file there."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".gridnotes_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def data_dir_candidates(*, include_legacy: bool = True) -> list[Path]:
    """Ordered list of possible GridNotes user-data folders (most preferred first)."""
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            resolved = path
        if resolved in seen:
            return
        seen.add(resolved)
        candidates.append(resolved)

    if sys.platform == "win32":
        # LOCALAPPDATA first — Roaming\\GridNotes is often admin-locked after elevated install.
        for env_name in ("LOCALAPPDATA", "APPDATA"):
            value = os.environ.get(env_name, "").strip()
            if value:
                add(Path(value) / APP_NAME)
        add(Path.home() / "GridNotes")
        documents = Path.home() / "Documents" / "GridNotes"
        add(documents)
        add(Path(tempfile.gettempdir()) / APP_NAME)
    elif sys.platform == "darwin":
        add(Path.home() / "Library" / "Application Support" / APP_NAME)
        add(Path.home() / "GridNotes")
    else:
        add(Path.home() / ".local" / "share" / APP_NAME)
        add(Path.home() / "GridNotes")

    if include_legacy:
        if sys.platform == "win32":
            for env_name in ("LOCALAPPDATA", "APPDATA"):
                value = os.environ.get(env_name, "").strip()
                if value:
                    add(Path(value) / LEGACY_APP_NAME)
        elif sys.platform == "darwin":
            add(Path.home() / "Library" / "Application Support" / LEGACY_APP_NAME)
        else:
            add(Path.home() / ".local" / "share" / LEGACY_APP_NAME)

    return candidates


def resolve_writable_data_dir() -> Path:
    """
    Return the first data folder we can write to.

    Prefers an existing folder that already has driver_history.db, if writable.
    """
    candidates = data_dir_candidates()
    with_database = [
        path
        for path in candidates
        if path.is_dir() and (path / "driver_history.db").is_file() and _probe_writable(path)
    ]
    if with_database:
        return with_database[0]

    for path in candidates:
        if _probe_writable(path):
            return path

    tried = "\n".join(f"  • {p}" for p in candidates)
    raise PermissionError(
        "GridNotes could not find a folder your user account can write to.\n\n"
        f"Tried:\n{tried}\n\n"
        "If %APPDATA%\\GridNotes was created by an administrator, delete that folder "
        "or fix its permissions, then try again."
    )


def resolve_launch_log_path() -> Path:
    return resolve_writable_data_dir() / "launch-error.log"
