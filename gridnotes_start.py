"""Launch GridNotes; write startup errors to launch-error.log."""
from __future__ import annotations

import runpy
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "launch-error.log"


def _log(line: str) -> None:
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def main() -> int:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text("", encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"Could not write {LOG}: {exc}\n")
        return 1

    _log(f"Python: {sys.version.split()[0]} ({sys.executable})")
    _log(f"Install folder: {ROOT}")

    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    try:
        from racing_book.data.db import get_data_dir_path

        data_dir = get_data_dir_path()
        _log(f"User data folder: {data_dir}")
        _log(f"App log file: {data_dir / 'gridnotes.log'}")
    except Exception:
        _log("Could not resolve user data folder (will retry when app starts)")

    try:
        _log("Importing PyQt6…")
        import PyQt6  # noqa: F401

        _log("PyQt6 OK")
    except Exception:
        _log("PyQt6 import failed:")
        with LOG.open("a", encoding="utf-8") as handle:
            traceback.print_exc(file=handle)
        return 1

    main_py = ROOT / "main.py"
    if not main_py.is_file():
        _log(f"Missing file: {main_py}")
        return 1

    try:
        _log("Starting GridNotes…")
        runpy.run_path(str(main_py), run_name="__main__")
        _log("GridNotes closed.")
        return 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        _log(f"GridNotes exited with code {code}")
        return code
    except Exception:
        _log("GridNotes crashed:")
        with LOG.open("a", encoding="utf-8") as handle:
            traceback.print_exc(file=handle)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
