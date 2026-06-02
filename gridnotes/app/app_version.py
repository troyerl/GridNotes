"""Application version metadata."""

from __future__ import annotations

import re
from pathlib import Path

__version__ = "1.0.21"

INSTALLED_VERSION_FILENAME = ".gridnotes-version"


def _read_marker_version(install_root: Path) -> str | None:
    marker = install_root / INSTALLED_VERSION_FILENAME
    if not marker.is_file():
        return None
    text = marker.read_text(encoding="utf-8").strip().lstrip("vV")
    return text or None


def _read_py_version(install_root: Path) -> str | None:
    for pkg in ("gridnotes", "racing_book"):
        app_version_py = install_root / pkg / "app" / "app_version.py"
        if not app_version_py.is_file():
            continue
        for line in app_version_py.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("__version__"):
                _, _, rhs = line.partition("=")
                value = rhs.strip().strip('"').strip("'")
                if value:
                    return value
    return None


def reconcile_installed_version(install_root: Path) -> str:
    """
    Pick the newest version recorded in the install folder and sync the marker file.

    After an update, .gridnotes-version can lag behind app_version.py if post-update
    refresh failed; using the max keeps Settings and update checks accurate.
    """
    install_root = install_root.resolve()
    marker = _read_marker_version(install_root)
    py_ver = _read_py_version(install_root)
    candidates = [v for v in (marker, py_ver) if v]
    if not candidates:
        return __version__
    best = max(candidates, key=parse_version)
    if marker != best:
        write_installed_version(install_root, best)
    return best


def installed_version() -> str:
    """Version of the installed copy under D:\\GridNotes (or similar)."""
    try:
        from ..installer.uninstall import resolve_install_root

        root = resolve_install_root()
        if root is not None:
            return reconcile_installed_version(root)
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
