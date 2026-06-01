#!/usr/bin/env python3
"""Launch the GridNotes graphical installer (sets up .venv and dependencies)."""

from __future__ import annotations

import subprocess
import sys


def _ensure_pyqt6() -> None:
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        print("Installing PyQt6 for the install wizard…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "PyQt6>=6.6"],
        )


def main() -> int:
    _ensure_pyqt6()
    from racing_book.installer.window import run_install_wizard

    return run_install_wizard()


if __name__ == "__main__":
    raise SystemExit(main())
