#!/usr/bin/env python3
"""Launch the GridNotes graphical installer (sets up .venv and dependencies)."""

from __future__ import annotations

import subprocess
import sys
import traceback
from pathlib import Path

# Ensure imports work when double-clicked (cwd may differ from script folder).
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _log_path() -> Path:
    return _ROOT / "install-helper.log"


def _append_log(text: str) -> None:
    try:
        with _log_path().open("a", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
    except OSError:
        pass


def _win_alert(title: str, message: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # type: ignore[attr-defined]
    except OSError:
        pass


def _ensure_pyqt6() -> None:
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        print("Installing PyQt6 for the install wizard…")
        _append_log("Installing PyQt6…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "PyQt6>=6.6"],
        )


def main() -> int:
    _append_log(f"install_gui.py starting with {sys.executable}")
    try:
        _ensure_pyqt6()

        print("Checking for Python 3.12 or 3.13 for GridNotes…")
        from racing_book.installer.ensure_python import ensure_supported_python_for_install

        ok, message, _executable = ensure_supported_python_for_install(log=print)
        print(message)
        _append_log(message)
        if not ok:
            print()
            _win_alert("GridNotes Install", message[:1000])
            input("Press Enter to close…")
            return 1
        print()

        from racing_book.installer.window import run_install_wizard

        return run_install_wizard()
    except Exception:
        detail = traceback.format_exc()
        _append_log(detail)
        print(detail, file=sys.stderr)
        print(f"\nDetails saved to {_log_path()}")
        _win_alert(
            "GridNotes Install",
            "The install wizard could not start.\n\n"
            f"See install-helper.log in:\n{_ROOT}",
        )
        input("Press Enter to close…")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
