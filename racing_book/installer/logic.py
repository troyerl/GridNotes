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


def ensure_icon_ico(root: Path, python: Path | None = None) -> Path | None:
    """Create icon.ico from icon.png in *root* when missing (Windows desktop shortcuts)."""
    ico = root / "icon.ico"
    if ico.is_file():
        return ico
    png = root / "icon.png"
    if not png.is_file():
        return None
    script = root / "scripts" / "generate_icon.py"
    if not script.is_file() or python is None or not python.is_file():
        return None
    try:
        subprocess.run(
            [str(python), "-m", "pip", "install", "Pillow>=10.0"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        subprocess.run(
            [str(python), str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("Could not generate icon.ico: %s", exc)
        return None
    return ico if ico.is_file() else None


def resolve_shortcut_icon(
    install_root: Path,
    *,
    source_root: Path | None = None,
    launch_target: Path | None = None,
    python: Path | None = None,
) -> Path | None:
    """Pick the best .ico (or .exe with embedded icon) for a desktop shortcut."""
    ensure_icon_ico(install_root, python)
    for base in (install_root, source_root):
        if base is None:
            continue
        ico = base / "icon.ico"
        if ico.is_file():
            return ico
    if (
        launch_target is not None
        and launch_target.suffix.lower() == ".exe"
        and launch_target.is_file()
    ):
        return launch_target
    return None


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


def windows_vbs_launcher_path(root: Path) -> Path:
    return root.resolve() / "Launch GridNotes.vbs"


def write_launcher_scripts(root: Path, venv_dir: Path) -> list[Path]:
    """Create double-click launchers in the install folder."""
    created: list[Path] = []
    py = venv_python(venv_dir)
    pyw = venv_pythonw(venv_dir)
    root = root.resolve()

    if sys.platform == "win32":
        run_bat = root / "Run GridNotes.bat"
        run_bat.write_text(
            "@echo off\r\n"
            'cd /d "%~dp0"\r\n'
            'if exist "%~dp0.venv\\Scripts\\pythonw.exe" (\r\n'
            '  "%~dp0.venv\\Scripts\\pythonw.exe" "%~dp0main.py"\r\n'
            ") else (\r\n"
            '  "%~dp0.venv\\Scripts\\python.exe" "%~dp0main.py"\r\n'
            ")\r\n",
            encoding="utf-8",
        )
        created.append(run_bat)

        launcher_py = pyw if pyw.is_file() else py
        pyw_abs = str(launcher_py.resolve())
        main_abs = str((root / "main.py").resolve())
        root_abs = str(root)
        vbs_path = windows_vbs_launcher_path(root)

        def _vbs_str(value: str) -> str:
            return value.replace('"', '""')

        vbs_path.write_text(
            "Set shell = CreateObject(\"WScript.Shell\")\r\n"
            f'shell.CurrentDirectory = "{_vbs_str(root_abs)}"\r\n'
            "command = Chr(34) & "
            f'"{_vbs_str(pyw_abs)}" & Chr(34) & " " & Chr(34) & '
            f'"{_vbs_str(main_abs)}" & Chr(34)\r\n'
            "shell.Run command, 0, False\r\n",
            encoding="utf-8",
        )
        created.append(vbs_path)
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


def preferred_shortcut_target(
    root: Path,
    venv_dir: Path,
    *,
    dist_exe: Path | None = None,
    build_standalone: bool = False,
) -> tuple[Path, Path, str | None]:
    """Return (target, working_dir, arguments) for a desktop shortcut."""
    root = root.resolve()
    if build_standalone and dist_exe is not None and dist_exe.is_file():
        return dist_exe.resolve(), dist_exe.parent.resolve(), None

    if sys.platform == "win32":
        vbs = windows_vbs_launcher_path(root)
        if vbs.is_file():
            return vbs, root, None
        run_bat = root / "Run GridNotes.bat"
        if run_bat.is_file():
            return run_bat, root, None

    pyw = venv_pythonw(venv_dir)
    if pyw.is_file():
        main_py = (root / "main.py").resolve()
        return pyw.resolve(), root, f'"{main_py}"'
    py = venv_python(venv_dir)
    main_py = (root / "main.py").resolve()
    return py.resolve(), root, f'"{main_py}"'


def launch_installed_app(
    install_root: Path,
    *,
    standalone_exe: Path | None = None,
) -> tuple[bool, str]:
    """Start GridNotes from an install folder."""
    install_root = install_root.resolve()
    main_py = install_root / "main.py"
    if not main_py.is_file():
        return False, f"Could not find main.py in:\n{install_root}"

    venv_dir = install_root / VENV_DIR_NAME
    dist_exe = standalone_exe
    if dist_exe is None:
        dist_exe = install_root / "dist" / "GridNotes" / "GridNotes.exe"
    if dist_exe.is_file():
        try:
            subprocess.Popen(
                [str(dist_exe)],
                cwd=str(dist_exe.parent),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True, ""
        except OSError as exc:
            return False, str(exc)

    if sys.platform == "win32":
        vbs = windows_vbs_launcher_path(install_root)
        if vbs.is_file():
            try:
                subprocess.Popen(
                    ["wscript.exe", "//B", str(vbs)],
                    cwd=str(install_root),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return True, ""
            except OSError as exc:
                return False, str(exc)

        run_bat = install_root / "Run GridNotes.bat"
        if run_bat.is_file():
            try:
                subprocess.Popen(
                    ["cmd.exe", "/c", str(run_bat)],
                    cwd=str(install_root),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return True, ""
            except OSError as exc:
                return False, str(exc)

    py = venv_pythonw(venv_dir)
    if not py.is_file():
        py = venv_python(venv_dir)
    if not py.is_file():
        return False, f"Virtual environment is missing Python under:\n{venv_dir}"
    try:
        subprocess.Popen(
            [str(py), str(main_py)],
            cwd=str(install_root),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True, ""
    except OSError as exc:
        return False, str(exc)


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
            shortcut_target, shortcut_working_dir, shortcut_args = preferred_shortcut_target(
                self.root,
                self.venv_dir,
                dist_exe=dist_exe,
                build_standalone=self.build_standalone,
            )
            self._launch_target = shortcut_target

            if self.create_desktop_shortcut:
                try:
                    shortcut_icon = resolve_shortcut_icon(
                        self.root,
                        source_root=self.source_root,
                        launch_target=shortcut_target,
                        python=venv_python(self.venv_dir),
                    )
                    shortcut = create_desktop_shortcut(
                        target=shortcut_target,
                        working_dir=shortcut_working_dir,
                        arguments=shortcut_args,
                        icon=shortcut_icon,
                    )
                    self._log(f"Desktop shortcut: {shortcut}")
                    if shortcut_icon is not None:
                        self._log(f"Shortcut icon: {shortcut_icon}")
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
