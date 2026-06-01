"""Install GridNotes from a downloaded source tree into a local virtual environment."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_PYTHON = (3, 10)
VENV_DIR_NAME = ".venv"
REQUIREMENTS_FILE = "requirements.txt"
REQUIREMENTS_BUILD_FILE = "requirements-build.txt"


def find_project_root(start: Path | None = None) -> Path:
    """Locate the repository root (folder containing requirements.txt)."""
    if start is None:
        start = Path(__file__).resolve().parent.parent.parent
    for candidate in (start, *start.parents):
        if (candidate / REQUIREMENTS_FILE).is_file() and (candidate / "main.py").is_file():
            return candidate
    return start


def venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_pip(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def check_python() -> tuple[bool, str]:
    version = sys.version_info[:3]
    if version[:2] < MIN_PYTHON:
        return (
            False,
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required (found {version[0]}.{version[1]}).",
        )
    return True, f"Using {sys.executable} (Python {version[0]}.{version[1]}.{version[2]})"


def write_launcher_scripts(root: Path, venv_dir: Path) -> list[Path]:
    """Create double-click launchers in the project root."""
    created: list[Path] = []
    py = venv_python(venv_dir)

    if sys.platform == "win32":
        run_bat = root / "Run GridNotes.bat"
        run_bat.write_text(
            "@echo off\r\n"
            f'cd /d "%~dp0"\r\n'
            f'"{py}" main.py\r\n',
            encoding="utf-8",
        )
        created.append(run_bat)
    else:
        run_sh = root / "Run GridNotes.command"
        run_sh.write_text(
            "#!/bin/bash\n"
            'cd "$(dirname "$0")"\n'
            f'"{py}" main.py\n',
            encoding="utf-8",
        )
        os.chmod(run_sh, 0o755)
        created.append(run_sh)

    return created


class InstallRunner:
    """Run install steps synchronously; callbacks receive log lines and progress."""

    def __init__(
        self,
        root: Path,
        *,
        build_standalone: bool = False,
        on_log: Callable[[str], None] | None = None,
        on_step: Callable[[str], None] | None = None,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        self.root = root
        self.build_standalone = build_standalone and sys.platform == "win32"
        self._on_log = on_log or (lambda _line: None)
        self._on_step = on_step or (lambda _step: None)
        self._on_progress = on_progress or (lambda _pct: None)
        self._should_cancel = should_cancel or (lambda: False)
        self.venv_dir = root / VENV_DIR_NAME
        self.requirements = root / REQUIREMENTS_FILE

    def _log(self, line: str) -> None:
        if line:
            logger.info(line)
            self._on_log(line)

    def _step(self, label: str, percent: int) -> None:
        self._on_step(label)
        self._on_progress(percent)

    def _check_cancelled(self) -> None:
        if self._should_cancel():
            raise RuntimeError("Installation cancelled.")

    def _run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        label: str | None = None,
    ) -> None:
        if label:
            self._log(f"$ {' '.join(args)}")
        proc = subprocess.Popen(
            args,
            cwd=str(cwd or self.root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            self._check_cancelled()
            self._log(line.rstrip("\n"))
        code = proc.wait()
        if code != 0:
            raise RuntimeError(f"Command failed ({code}): {' '.join(args)}")

    def run(self) -> tuple[bool, str]:
        ok, message = check_python()
        if not ok:
            return False, message

        if not self.requirements.is_file():
            return False, f"Could not find {REQUIREMENTS_FILE} in {self.root}"

        try:
            self._step("Checking Python", 5)
            self._log(message)
            self._check_cancelled()

            self._step("Creating virtual environment", 15)
            if self.venv_dir.exists():
                self._log(f"Using existing {self.venv_dir.name}/")
            else:
                self._run([sys.executable, "-m", "venv", str(self.venv_dir)])
            self._check_cancelled()

            py = venv_python(self.venv_dir)
            if not py.is_file():
                return False, f"Virtual environment is missing Python at {py}"

            self._step("Upgrading pip", 30)
            self._run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
            self._check_cancelled()

            self._step("Installing dependencies", 55)
            self._run(
                [str(py), "-m", "pip", "install", "-r", str(self.requirements)],
            )
            self._check_cancelled()

            if self.build_standalone:
                build_req = self.root / REQUIREMENTS_BUILD_FILE
                if not build_req.is_file():
                    return False, f"Missing {REQUIREMENTS_BUILD_FILE} for standalone build."
                self._step("Installing build tools", 65)
                self._run([str(py), "-m", "pip", "install", "-r", str(build_req)])
                self._check_cancelled()

                icon_script = self.root / "scripts" / "generate_icon.py"
                if icon_script.is_file():
                    self._step("Generating application icon", 72)
                    self._run([str(py), str(icon_script)])
                    self._check_cancelled()

                self._step("Building standalone app (PyInstaller)", 85)
                self._run(
                    [str(py), "-m", "PyInstaller", "racing_book.spec", "--noconfirm", "--clean"],
                )
                self._check_cancelled()

            self._step("Creating shortcuts", 95)
            launchers = write_launcher_scripts(self.root, self.venv_dir)
            for path in launchers:
                self._log(f"Created {path.name}")

            self._step("Finished", 100)
            if self.build_standalone:
                dist_exe = self.root / "dist" / "GridNotes" / "GridNotes.exe"
                if dist_exe.is_file():
                    summary = (
                        "Installation complete.\n\n"
                        f"Standalone app: {dist_exe}\n"
                        "Or run from source using the launcher script in this folder."
                    )
                else:
                    summary = (
                        "Dependencies installed, but GridNotes.exe was not found in dist/.\n"
                        "Check the log for PyInstaller errors."
                    )
            else:
                launcher = launchers[0].name if launchers else "main.py"
                summary = (
                    "Installation complete.\n\n"
                    f"Use “Launch GridNotes” or double-click “{launcher}” to start the app."
                )
            return True, summary
        except RuntimeError as exc:
            if str(exc) == "Installation cancelled.":
                return False, "Installation cancelled."
            return False, str(exc)
        except (OSError, subprocess.SubprocessError) as exc:
            logger.exception("Install failed")
            return False, str(exc)
