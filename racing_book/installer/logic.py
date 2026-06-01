"""Install GridNotes from a downloaded source tree into a local virtual environment."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from .shortcuts import create_desktop_shortcut

logger = logging.getLogger(__name__)

MIN_PYTHON = (3, 10)
VENV_DIR_NAME = ".venv"
REQUIREMENTS_FILE = "requirements.txt"
REQUIREMENTS_BUILD_FILE = "requirements-build.txt"

_COPY_NAMES = (
    "main.py",
    "requirements.txt",
    "requirements-build.txt",
    "racing_book.spec",
    "icon.png",
    "icon.ico",
    "icon.icns",
)
_COPY_DIRS = ("racing_book", "scripts")
_IGNORE_DIR_NAMES = {
    ".venv",
    ".build-venv",
    "dist",
    "build",
    ".git",
    "__pycache__",
    ".cursor",
    ".pytest_cache",
}


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


def default_build_output_dir(install_root: Path) -> Path:
    return install_root / "dist"


def default_install_location() -> Path:
    """
    Recommended install folder (per-user, no admin required).

    Windows: %LOCALAPPDATA%\\Programs\\GridNotes (same idea as per-user Program Files)
    macOS:   ~/Applications/GridNotes
    Linux:   ~/.local/share/GridNotes
    """
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return Path(local_app_data) / "Programs" / "GridNotes"
        return Path.home() / "AppData" / "Local" / "Programs" / "GridNotes"
    if sys.platform == "darwin":
        return Path.home() / "Applications" / "GridNotes"
    return Path.home() / ".local" / "share" / "GridNotes"


def program_files_install_location() -> Path | None:
    """System-wide Windows location (requires administrator to write)."""
    if sys.platform != "win32":
        return None
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files").strip()
    if not program_files:
        return None
    return Path(program_files) / "GridNotes"


def default_install_location_hint() -> str:
    default = default_install_location()
    if sys.platform == "win32":
        pf = program_files_install_location()
        pf_note = ""
        if pf is not None:
            pf_note = (
                f" For all users under {pf}, choose that path with Browse and run "
                "this installer as administrator if Windows asks for permission."
            )
        return (
            f"Default install folder: {default} — your personal Programs area "
            "(no admin password). Files are copied from the download folder into "
            f"the location you choose.{pf_note}"
        )
    if sys.platform == "darwin":
        return (
            f"Default install folder: {default} — your Applications folder "
            "(no administrator password). Files are copied from the download folder."
        )
    return (
        f"Default install folder: {default}. Files are copied from the download "
        "folder into the location you choose."
    )


def is_valid_install_root(path: Path) -> tuple[bool, str]:
    path = path.resolve()
    if not path.parent.exists():
        return False, "Parent folder does not exist."
    return True, ""


def copy_source_to_install_root(source: Path, dest: Path) -> None:
    """Copy application source into *dest* (skips venv, builds, and local database)."""
    source = source.resolve()
    dest = dest.resolve()
    if source == dest:
        return

    dest.mkdir(parents=True, exist_ok=True)

    def ignore_directory(directory: str, names: list[str]) -> list[str]:
        base = Path(directory)
        ignored: list[str] = []
        for name in names:
            if name in _IGNORE_DIR_NAMES:
                ignored.append(name)
                continue
            if name == "driver_history.db" and base == source:
                ignored.append(name)
            if name.endswith(".pyc"):
                ignored.append(name)
        return ignored

    for name in _COPY_NAMES:
        src_file = source / name
        if src_file.is_file():
            shutil.copy2(src_file, dest / name)

    for dirname in _COPY_DIRS:
        src_dir = source / dirname
        if src_dir.is_dir():
            shutil.copytree(
                src_dir,
                dest / dirname,
                ignore=ignore_directory,
                dirs_exist_ok=True,
            )


def resolve_install_root(source: Path, chosen: Path) -> Path:
    """Return the folder where install steps should run."""
    source = source.resolve()
    chosen = chosen.resolve()
    if chosen == source:
        return source
    copy_source_to_install_root(source, chosen)
    return chosen


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
        source_root: Path,
        install_root: Path,
        *,
        build_standalone: bool = False,
        build_output_dir: Path | None = None,
        create_desktop_shortcut: bool = False,
        on_log: Callable[[str], None] | None = None,
        on_step: Callable[[str], None] | None = None,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        self.source_root = source_root.resolve()
        self.root = install_root.resolve()
        self.build_standalone = build_standalone and sys.platform == "win32"
        self.build_output_dir = (
            build_output_dir.resolve()
            if build_output_dir
            else default_build_output_dir(self.root)
        )
        self.create_desktop_shortcut = create_desktop_shortcut
        self._on_log = on_log or (lambda _line: None)
        self._on_step = on_step or (lambda _step: None)
        self._on_progress = on_progress or (lambda _pct: None)
        self._should_cancel = should_cancel or (lambda: False)
        self.venv_dir = self.root / VENV_DIR_NAME
        self.requirements = self.root / REQUIREMENTS_FILE
        self._launch_target: Path | None = None
        self._shortcut_icon: Path | None = None
        for icon_name in ("icon.ico", "icon.png"):
            icon_path = self.root / icon_name
            if icon_path.is_file():
                self._shortcut_icon = icon_path
                break

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

            if self.root != self.source_root:
                self._step("Copying files to install location", 10)
                self._log(f"Install folder: {self.root}")
                resolve_install_root(self.source_root, self.root)
            else:
                self._log(f"Installing in place: {self.root}")
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
                self.build_output_dir.mkdir(parents=True, exist_ok=True)
                self._log(f"Build output folder: {self.build_output_dir}")
                self._run(
                    [
                        str(py),
                        "-m",
                        "PyInstaller",
                        "racing_book.spec",
                        "--noconfirm",
                        "--clean",
                        "--distpath",
                        str(self.build_output_dir),
                        "--workpath",
                        str(self.root / "build"),
                    ],
                )
                self._check_cancelled()

            self._step("Creating shortcuts", 95)
            launchers = write_launcher_scripts(self.root, self.venv_dir)
            for path in launchers:
                self._log(f"Created {path.name}")

            dist_exe = self.build_output_dir / "GridNotes" / "GridNotes.exe"
            if self.build_standalone and dist_exe.is_file():
                self._launch_target = dist_exe
            elif launchers:
                self._launch_target = launchers[0]
            else:
                self._launch_target = venv_python(self.venv_dir)

            if self.create_desktop_shortcut and self._launch_target is not None:
                try:
                    shortcut = create_desktop_shortcut(
                        target=self._launch_target,
                        working_dir=(
                            self._launch_target.parent
                            if self._launch_target.suffix.lower() == ".exe"
                            else self.root
                        ),
                        icon=self._shortcut_icon,
                    )
                    self._log(f"Desktop shortcut: {shortcut}")
                except (OSError, subprocess.SubprocessError) as exc:
                    self._log(f"Could not create desktop shortcut: {exc}")

            self._step("Finished", 100)
            if self.build_standalone:
                if dist_exe.is_file():
                    summary = (
                        "Installation complete.\n\n"
                        f"Install folder: {self.root}\n"
                        f"Standalone app: {dist_exe}\n"
                        "Or run from source using the launcher in the install folder."
                    )
                else:
                    summary = (
                        "Dependencies installed, but GridNotes.exe was not found.\n"
                        f"Expected: {dist_exe}\n"
                        "Check the log for PyInstaller errors."
                    )
            else:
                launcher = launchers[0].name if launchers else "main.py"
                summary = (
                    "Installation complete.\n\n"
                    f"Install folder: {self.root}\n"
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
