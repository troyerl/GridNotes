"""Launch GridNotes; write startup errors to launch-error.log."""
from __future__ import annotations

import os
import runpy
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _launch_log_candidates() -> list[Path]:
    paths: list[Path] = []
    if sys.platform == "win32":
        for env_name in ("LOCALAPPDATA", "APPDATA"):
            value = os.environ.get(env_name, "").strip()
            if value:
                paths.append(Path(value) / "GridNotes" / "launch-error.log")
        paths.append(Path.home() / "GridNotes" / "launch-error.log")
        paths.append(Path(tempfile.gettempdir()) / "GridNotes" / "launch-error.log")
    try:
        root_str = str(ROOT)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        from racing_book.data.db import get_launch_log_path

        paths.insert(0, get_launch_log_path())
    except Exception:
        pass
    paths.append(ROOT / "launch-error.log")
    return paths


def _open_launch_log() -> Path | None:
    for path in _launch_log_candidates():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
            return path
        except OSError:
            continue
    return None


def _log(line: str, log_path: Path | None) -> None:
    text = line.rstrip() + "\n"
    if log_path is not None:
        try:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(text)
            return
        except OSError:
            pass
    print(text, end="", file=sys.stderr)


def main() -> int:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "GridNotes.GridNotes.1"
            )
        except Exception:
            pass

    log_path = _open_launch_log()
    if log_path is None:
        sys.stderr.write(
            "Warning: could not write launch-error.log (AppData may be locked). "
            "Continuing anyway — errors will print here.\n"
        )
    else:
        _log(f"Launch log: {log_path}", log_path)

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
    except Exception as exc:
        _log(f"Could not resolve user data folder: {exc}", log_path)

    try:
        _log("Importing PyQt6…", log_path)
        import PyQt6  # noqa: F401

        _log("PyQt6 OK", log_path)
    except Exception:
        _log("PyQt6 import failed:", log_path)
        if log_path is not None:
            with log_path.open("a", encoding="utf-8") as handle:
                traceback.print_exc(file=handle)
        else:
            traceback.print_exc()
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
        if log_path is not None:
            with log_path.open("a", encoding="utf-8") as handle:
                traceback.print_exc(file=handle)
        else:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
