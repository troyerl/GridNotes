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

    print("Checking for Python 3.12 or 3.13 for GridNotes…")
    from racing_book.installer.ensure_python import ensure_supported_python_for_install

    ok, message, _executable = ensure_supported_python_for_install(log=print)
    print(message)
    if not ok:
        print()
        input("Press Enter to close…")
        return 1
    print()

    from racing_book.installer.window import run_install_wizard

    return run_install_wizard()


if __name__ == "__main__":
    raise SystemExit(main())
