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
APP_INSTALL_DIRNAME = "GridNotes"
REQUIREMENTS_FILE = "requirements.txt"
REQUIREMENTS_BUILD_FILE = "requirements-build.txt"

_COPY_NAMES = (
    "main.py",
    "install_gui.py",
    "requirements.txt",
    "requirements-build.txt",
    "racing_book.spec",
    "icon.png",
    "icon.ico",
    "icon.icns",
    "START_HERE.txt",
    "INSTALL.md",
)
_COPY_OPTIONAL_NAMES = (
    "Install GridNotes.bat",
    "Install GridNotes.command",
    "Run GridNotes.bat",
    "Run GridNotes.command",
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
    candidates: list[Path] = []
    if start is not None:
        candidates.append(start)
    else:
        cwd = Path.cwd()
        candidates.append(cwd)
        candidates.append(Path(__file__).resolve().parent.parent.parent)
    seen: set[Path] = set()
    for base in candidates:
        for candidate in (base, *base.parents):
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if (resolved / REQUIREMENTS_FILE).is_file() and (resolved / "main.py").is_file():
                return resolved
    return candidates[0].resolve() if candidates else Path.cwd()


def venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_pythonw(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "pythonw.exe"
    return venv_python(venv_dir)


def venv_pip(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def default_build_output_dir(install_root: Path) -> Path:
    return install_root / "dist"


def user_local_install_location() -> Path:
    """Per-user install folder (no administrator required)."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return Path(local_app_data) / "Programs" / "GridNotes"
        return Path.home() / "AppData" / "Local" / "Programs" / "GridNotes"
    if sys.platform == "darwin":
        return Path.home() / "Applications" / "GridNotes"
    return Path.home() / ".local" / "share" / "GridNotes"


def default_install_location() -> Path:
    """
    Recommended install folder (standard application location).

    Windows: C:\\Program Files\\GridNotes (or ProgramFiles env var)
    macOS:   ~/Applications/GridNotes
    Linux:   ~/.local/share/GridNotes
    """
    if sys.platform == "win32":
        pf = program_files_install_location()
        if pf is not None:
            return pf
        return user_local_install_location()
    return user_local_install_location()


def program_files_install_location() -> Path | None:
    """System-wide Windows location (requires administrator to write)."""
    if sys.platform != "win32":
        return None
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files").strip()
    if not program_files:
        return None
    return Path(program_files) / APP_INSTALL_DIRNAME


def normalize_chosen_install_dir(
    chosen: Path,
    *,
    source_root: Path | None = None,
) -> Path:
    """
    When the user picks a drive or parent folder, install into a GridNotes subfolder.

    Examples: D:\\ → D:\\GridNotes; D:\\Program Files → D:\\Program Files\\GridNotes.
    Paths that already end with GridNotes, or match the download folder, are unchanged.
    """
    chosen = chosen.expanduser()
    if source_root is not None:
        try:
            if chosen.resolve() == source_root.resolve():
                return chosen
        except OSError:
            pass
    if chosen.name.lower() == APP_INSTALL_DIRNAME.lower():
        return chosen
    return chosen / APP_INSTALL_DIRNAME


def simple_install_location_hint() -> str:
    """Short guidance for non-technical users."""
    if sys.platform == "win32":
        return (
            "Leave this as-is for a normal install (like other Windows apps). "
            "Use Choose folder… to pick another drive or folder — GridNotes will be installed "
            "in a GridNotes folder there (for example D:\\ → D:\\GridNotes). "
            "After install, open GridNotes from the Desktop icon — not from your download folder."
        )
    return (
        "Leave this folder as-is unless someone told you to change it. "
        "GridNotes will be installed there and you can open it from your Desktop."
    )


def default_install_location_hint() -> str:
    """Detailed hint shown under advanced options."""
    default = default_install_location()
    if sys.platform == "win32":
        local = user_local_install_location()
        return (
            f"Default install folder: {default}. "
            "Files are copied from your download folder into the install folder; "
            "you can delete or move the download folder after install. "
            f"To install without administrator permission, use “Install for only me” ({local})."
        )
    return (
        f"Recommended folder: {default}. "
        "Files are copied from your download folder into the install folder."
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

    for name in _COPY_OPTIONAL_NAMES:
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
    """Create double-click launchers in the install folder."""
    created: list[Path] = []
    py = venv_python(venv_dir)
    pyw = venv_pythonw(venv_dir)

    if sys.platform == "win32":
        run_bat = root / "Run GridNotes.bat"
        launcher_py = pyw if pyw.is_file() else py
        run_bat.write_text(
            "@echo off\r\n"
            f'cd /d "%~dp0"\r\n'
            f'"{launcher_py}" main.py\r\n',
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

        source_req = self.source_root / REQUIREMENTS_FILE
        if not source_req.is_file():
            return False, (
                f"Could not find {REQUIREMENTS_FILE} in your download folder:\n"
                f"{self.source_root}\n\n"
                "Use the folder that contains Install GridNotes.bat and main.py "
                "(not the AppData install folder). Run Install GridNotes.bat from "
                "that download folder."
            )

        try:
            self._step("Checking Python", 5)
            self._log(message)
            self._log(f"Download folder: {self.source_root}")
            self._check_cancelled()

            if self.root.resolve() != self.source_root.resolve():
                self._step("Copying files to install location", 10)
                self._log(f"Install folder: {self.root}")
                copy_source_to_install_root(self.source_root, self.root)
            else:
                self._log(f"Installing in place: {self.root}")
            self._check_cancelled()

            if not self.requirements.is_file():
                return False, (
                    f"Could not find {REQUIREMENTS_FILE} in {self.root} after copying.\n"
                    "Try again, or set the install location to your download folder."
                )

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
            shortcut_args: str | None = None
            if self.build_standalone and dist_exe.is_file():
                self._launch_target = dist_exe
                shortcut_working_dir = dist_exe.parent
            elif sys.platform == "win32" and venv_pythonw(self.venv_dir).is_file():
                self._launch_target = venv_pythonw(self.venv_dir)
                shortcut_working_dir = self.root
                shortcut_args = "main.py"
            elif launchers:
                self._launch_target = launchers[0]
                shortcut_working_dir = self.root
            else:
                self._launch_target = venv_python(self.venv_dir)
                shortcut_working_dir = self.root
                shortcut_args = "main.py"

            if self.create_desktop_shortcut and self._launch_target is not None:
                try:
                    shortcut = create_desktop_shortcut(
                        target=self._launch_target,
                        working_dir=shortcut_working_dir,
                        arguments=shortcut_args,
                        icon=self._shortcut_icon,
                    )
                    self._log(f"Desktop shortcut: {shortcut}")
                    self._log(f"Shortcut opens: {self.root}")
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
                shortcut_note = (
                    "Open GridNotes from the Desktop icon."
                    if self.create_desktop_shortcut
                    else f'Use “Launch GridNotes” or “{launchers[0].name if launchers else "Run GridNotes.bat"}”.'
                )
                summary = (
                    "Installation complete.\n\n"
                    f"Install folder: {self.root}\n"
                    f"{shortcut_note}\n"
                    "You can move or delete your download folder; GridNotes runs from the install folder."
                )
            return True, summary
        except RuntimeError as exc:
            if str(exc) == "Installation cancelled.":
                return False, "Installation cancelled."
            return False, str(exc)
        except (OSError, subprocess.SubprocessError) as exc:
            logger.exception("Install failed")
            return False, str(exc)
