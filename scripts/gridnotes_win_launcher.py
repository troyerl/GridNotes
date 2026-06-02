"""
Windows GridNotes.exe entry point (built with PyInstaller).

Keeps the GridNotes icon on shortcuts and taskbar pins. The real app still runs
via pythonw + gridnotes_start.py in the install folder (.venv).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _install_root() -> Path:
    # Invoked path is D:\\GridNotes\\GridNotes.exe (onefile or plain copy).
    return Path(sys.argv[0]).resolve().parent


def main() -> int:
    if sys.platform != "win32":
        return 1

    root = _install_root()
    os.chdir(root)

    pyw = root / ".venv" / "Scripts" / "pythonw.exe"
    starter = root / "gridnotes_start.py"
    missing: list[str] = []
    if not pyw.is_file():
        missing.append(str(pyw))
    if not starter.is_file():
        missing.append(str(starter))
    if missing:
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                "GridNotes is not installed correctly.\n\nMissing:\n"
                + "\n".join(missing)
                + "\n\nRe-run Install GridNotes.bat.",
                "GridNotes",
                0x10,
            )
        except OSError:
            pass
        return 1

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
        subprocess, "DETACHED_PROCESS", 0
    )
    try:
        subprocess.Popen(
            [str(pyw), str(starter)],
            cwd=str(root),
            creationflags=flags,
            close_fds=True,
        )
    except OSError:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
