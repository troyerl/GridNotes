"""Launch GridNotes; write startup errors to launch-error.log."""
from __future__ import annotations

import os
import runpy
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _log_path() -> Path:
    """Prefer per-user AppData so D:\\ or Program Files installs can always log."""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA", "").strip()
        if app_data:
            return Path(app_data) / "GridNotes" / "launch-error.log"
    try:
        root_str = str(ROOT)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        from racing_book.data.db import get_launch_log_path

        return get_launch_log_path()
    except Exception:
        return ROOT / "launch-error.log"


def _log(line: str, log_path: Path) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def main() -> int:
    log_path = _log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"Could not write {log_path}: {exc}\n")
        return 1

    _log(f"Python: {sys.version.split()[0]} ({sys.executable})", log_path)
    _log(f"Install folder: {ROOT}", log_path)

    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    try:
        from racing_book.data.db import get_data_dir_path

        data_dir = get_data_dir_path()
        _log(f"User data folder: {data_dir}", log_path)
        _log(f"App log file: {data_dir / 'gridnotes.log'}", log_path)
    except Exception:
        _log("Could not resolve user data folder (will retry when app starts)", log_path)

    try:
        _log("Importing PyQt6…", log_path)
        import PyQt6  # noqa: F401

        _log("PyQt6 OK", log_path)
    except Exception:
        _log("PyQt6 import failed:", log_path)
        with log_path.open("a", encoding="utf-8") as handle:
            traceback.print_exc(file=handle)
        return 1

    main_py = ROOT / "main.py"
    if not main_py.is_file():
        _log(f"Missing file: {main_py}", log_path)
        return 1

    try:
        _log("Starting GridNotes…", log_path)
        runpy.run_path(str(main_py), run_name="__main__")
        _log("GridNotes closed.", log_path)
        return 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        _log(f"GridNotes exited with code {code}", log_path)
        return code
    except Exception:
        _log("GridNotes crashed:", log_path)
        with log_path.open("a", encoding="utf-8") as handle:
            traceback.print_exc(file=handle)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
