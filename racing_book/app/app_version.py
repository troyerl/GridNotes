"""Application version metadata."""

from __future__ import annotations

import re
from pathlib import Path

__version__ = "1.0.13"

INSTALLED_VERSION_FILENAME = ".gridnotes-version"


def installed_version() -> str:
    """
    Version of the installed copy under D:\\GridNotes (or similar).

    Prefer .gridnotes-version (written on install/update); fall back to
    app_version.py in the install tree.
    """
    try:
        from ..installer.uninstall import resolve_install_root

        root = resolve_install_root()
        if root is not None:
            marker = root / INSTALLED_VERSION_FILENAME
            if marker.is_file():
                text = marker.read_text(encoding="utf-8").strip().lstrip("vV")
                if text:
                    return text
            app_version_py = root / "racing_book" / "app" / "app_version.py"
            if app_version_py.is_file():
                for line in app_version_py.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("__version__"):
                        _, _, rhs = line.partition("=")
                        value = rhs.strip().strip('"').strip("'")
                        if value:
                            return value
    except OSError:
        pass
    return __version__


def write_installed_version(install_root: Path, version: str) -> None:
    """Record the release version in the install folder (Settings → Apps uses this)."""
    text = (version or "").strip().lstrip("vV")
    if not text:
        return
    try:
        path = install_root.resolve() / INSTALLED_VERSION_FILENAME
        path.write_text(f"{text}\n", encoding="utf-8")
    except OSError:
        pass


def parse_version(value: str) -> tuple[int, ...]:
    """Parse a semver-like string into a comparable integer tuple."""
    parts: list[int] = []
    for segment in re.split(r"[.\-+]", (value or "").strip()):
        if segment.isdigit():
            parts.append(int(segment))
        elif parts:
            break
    return tuple(parts) if parts else (0,)


def is_newer_version(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)
