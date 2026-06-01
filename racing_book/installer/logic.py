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
MAX_PYTHON = (3, 13)  # 3.14+ breaks PyQt6 in the install-helper venv today
VENV_DIR_NAME = ".venv"
APP_INSTALL_DIRNAME = "GridNotes"
REQUIREMENTS_FILE = "requirements.txt"
REQUIREMENTS_BUILD_FILE = "requirements-build.txt"

_COPY_NAMES = (
    "main.py",
    "gridnotes_start.py",
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
    "Open GridNotes.bat",
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
    Recommended install folder (no administrator required on Windows).

    Windows: %LOCALAPPDATA%\\Programs\\GridNotes (use Program Files only with admin)
    macOS:   ~/Applications/GridNotes
    Linux:   ~/.local/share/GridNotes
    """
    return user_local_install_location()


def is_windows_admin() -> bool:
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def install_path_under_program_files(path: Path) -> bool:
    if sys.platform != "win32":
        return False
    resolved = path.resolve()
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        prefix = os.environ.get(env_name, "").strip()
        if not prefix:
            continue
        try:
            resolved.relative_to(Path(prefix).resolve())
            return True
        except ValueError:
            continue
    return False


def permission_denied_install_message(install_root: Path) -> str:
    local = user_local_install_location()
    return (
        f"Windows denied access to:\n{install_root}\n\n"
        "Program Files requires administrator permission.\n\n"
        "Choose one:\n"
        f"• Click “Install for only me” or use: {local}\n"
        "• Or pick D:\\ in Choose folder… (installs to D:\\GridNotes)\n"
        "• Or close this window, right-click Install GridNotes.bat → "
        "Run as administrator, then install to Program Files again"
    )


def check_install_folder_writable(install_root: Path) -> tuple[bool, str]:
    """Return whether GridNotes can create/write the install folder."""
    install_root = install_root.resolve()
    try:
        install_root.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as exc:
        if isinstance(exc, PermissionError) or getattr(exc, "winerror", None) == 5:
            return False, permission_denied_install_message(install_root)
        return False, str(exc)

    probe = install_root / ".gridnotes_install_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except (PermissionError, OSError) as exc:
        if isinstance(exc, PermissionError) or getattr(exc, "winerror", None) == 5:
            return False, permission_denied_install_message(install_root)
        return False, str(exc)

    if install_path_under_program_files(install_root) and not is_windows_admin():
        return False, permission_denied_install_message(install_root)

    return True, ""


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
            "Default folder needs no administrator permission. "
            "Use Choose folder… for another drive (for example D:\\ → D:\\GridNotes). "
            "For C:\\Program Files, use advanced options and run Install GridNotes.bat as administrator. "
            "After install, open GridNotes from the Desktop icon."
        )
    return (
        "Leave this folder as-is unless someone told you to change it. "
        "GridNotes will be installed there and you can open it from your Desktop."
    )


def default_install_location_hint() -> str:
    """Detailed hint shown under advanced options."""
    default = default_install_location()
    if sys.platform == "win32":
        pf = program_files_install_location()
        pf_note = f" {pf}" if pf is not None else ""
        return (
            f"Default install folder: {default}. "
            "Program Files"
            f"{pf_note} requires running Install GridNotes.bat as administrator. "
            "Use Choose folder… for D:\\ or another drive."
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


def _python_version_for_executable(executable: str) -> tuple[int, int] | None:
    try:
        output = subprocess.check_output(
            [executable, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            text=True,
            timeout=20,
        )
        major_s, minor_s = output.strip().split()[:2]
        return int(major_s), int(minor_s)
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def _is_supported_python_version(major: int, minor: int) -> bool:
    return (major, minor) >= MIN_PYTHON and (major, minor) <= MAX_PYTHON


def _resolve_windows_py_launcher(version: str) -> str | None:
    try:
        output = subprocess.check_output(
            ["py", f"-{version}", "-c", "import sys; print(sys.executable)"],
            text=True,
            timeout=20,
        )
        path = output.strip()
        return path if path and Path(path).is_file() else None
    except (subprocess.SubprocessError, OSError):
        return None


def resolve_install_python() -> tuple[bool, str, str | None]:
    """
    Pick a Python executable for creating the GridNotes .venv.

    On Windows, prefers the ``py`` launcher (3.13, 3.12, …) so Python 3.14 on PATH
    does not break the install.
    """
    if sys.platform == "win32":
        for version in ("3.13", "3.12", "3.11", "3.10"):
            executable = _resolve_windows_py_launcher(version)
            if executable is None:
                continue
            parsed = _python_version_for_executable(executable)
            if parsed is not None and _is_supported_python_version(*parsed):
                return (
                    True,
                    f"Using {executable} (Python {parsed[0]}.{parsed[1]})",
                    executable,
                )

    executable = sys.executable
    parsed = _python_version_for_executable(executable)
    if parsed is None:
        return False, "Could not determine your Python version.", None

    if not _is_supported_python_version(*parsed):
        if parsed >= (3, 14):
            return (
                False,
                "Python 3.14 is not supported for GridNotes install yet.\n\n"
                "Install Python 3.12 or 3.13 from https://www.python.org/downloads/\n"
                '(check "Add python.exe to PATH" on the first installer screen).\n\n'
                "Then delete the folder D:\\GridNotes\\.venv if it exists, and run\n"
                "Install GridNotes.bat again.\n\n"
                "Tip: On Windows you can keep 3.14 installed; the installer will use\n"
                "3.12 or 3.13 automatically if you install them too.",
                None,
            )
        return (
            False,
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}–{MAX_PYTHON[0]}.{MAX_PYTHON[1]} is required "
            f"(found {parsed[0]}.{parsed[1]}).",
            None,
        )

    return (
        True,
        f"Using {executable} (Python {parsed[0]}.{parsed[1]})",
        executable,
    )


def check_python() -> tuple[bool, str]:
    ok, message, _executable = resolve_install_python()
    return ok, message


def install_location_pointer_file() -> Path:
    """Where we store the path to the last successful install (for Open GridNotes.bat)."""
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        return Path(local) / "GridNotes" / "install-path.txt"
    return Path.home() / "AppData" / "Local" / "GridNotes" / "install-path.txt"


def save_install_location(install_root: Path) -> None:
    path = install_location_pointer_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(install_root.resolve()), encoding="utf-8")
    logger.info("Saved install location pointer: %s", path)


def windows_vbs_launcher_path(root: Path) -> Path:
    return root.resolve() / "Launch GridNotes.vbs"


def gridnotes_start_script_path(root: Path) -> Path:
    return root.resolve() / "gridnotes_start.py"


def _gridnotes_start_template_path() -> Path:
    """Canonical gridnotes_start.py (repo root or next to this module)."""
    root = find_project_root()
    candidate = root / "gridnotes_start.py"
    if candidate.is_file():
        return candidate
    return Path(__file__).resolve().parent / "gridnotes_start.py"


def write_gridnotes_start_script(root: Path) -> Path:
    """Copy the bootstrap script that logs UI startup failures to launch-error.log."""
    path = gridnotes_start_script_path(root)
    source = _gridnotes_start_template_path()
    if not source.is_file():
        raise FileNotFoundError(f"Missing launcher template: {source}")
    shutil.copy2(source, path)
    return path


def write_launcher_scripts(root: Path, venv_dir: Path) -> list[Path]:
    """Create double-click launchers in the install folder."""
    created: list[Path] = []
    py = venv_python(venv_dir)
    pyw = venv_pythonw(venv_dir)
    root = root.resolve()
    write_gridnotes_start_script(root)
    starter = gridnotes_start_script_path(root)

    if sys.platform == "win32":
        ps1 = root / "Launch-GridNotes.ps1"
        ps1.write_text(
            "$ErrorActionPreference = 'Continue'\r\n"
            "$root = $PSScriptRoot\r\n"
            "$bat = Join-Path $root 'Run GridNotes.bat'\r\n"
            "$log = Join-Path $root 'launch-error.log'\r\n"
            "if (-not (Test-Path $bat)) { 'Run GridNotes.bat not found' | Out-File $log; exit 1 }\r\n"
            "$p = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', $bat) "
            "-WorkingDirectory $root -Wait -PassThru\r\n"
            "exit $p.ExitCode\r\n",
            encoding="utf-8",
        )
        created.append(ps1)

        run_bat = root / "Run GridNotes.bat"
        run_bat.write_text(
            "@echo off\r\n"
            "setlocal EnableExtensions\r\n"
            'cd /d "%~dp0"\r\n'
            'set "PY=%~dp0.venv\\Scripts\\python.exe"\r\n'
            'set "STARTER=%~dp0gridnotes_start.py"\r\n'
            'set "MAIN=%~dp0main.py"\r\n'
            'set "LOG=%~dp0launch-error.log"\r\n'
            'echo === GridNotes launch %date% %time% ===>"%LOG%"\r\n'
            'echo Install folder: %CD%>>"%LOG%"\r\n'
            'if not exist "%PY%" (\r\n'
            '  echo ERROR: Missing %PY%>>"%LOG%"\r\n'
            "  goto :fail\r\n"
            ")\r\n"
            'if exist "%STARTER%" goto :run_starter\r\n'
            'echo gridnotes_start.py missing, running main.py>>"%LOG%"\r\n'
            'if not exist "%MAIN%" (\r\n'
            '  echo ERROR: Missing %MAIN%>>"%LOG%"\r\n'
            "  goto :fail\r\n"
            ")\r\n"
            'goto :run_main\r\n'
            ":run_starter\r\n"
            'echo Running gridnotes_start.py...>>"%LOG%"\r\n'
            '"%PY%" "%STARTER%" >>"%LOG%" 2>&1\r\n'
            "if errorlevel 1 goto :fail\r\n"
            "exit /b 0\r\n"
            ":run_main\r\n"
            'echo Running main.py...>>"%LOG%"\r\n'
            '"%PY%" "%MAIN%" >>"%LOG%" 2>&1\r\n'
            "if errorlevel 1 goto :fail\r\n"
            "exit /b 0\r\n"
            ":fail\r\n"
            "echo.\r\n"
            "echo GridNotes did not start.\r\n"
            "echo See: %LOG%\r\n"
            "echo App log (if the app ran): %APPDATA%\\GridNotes\\gridnotes.log\r\n"
            "echo.\r\n"
            "type \"%LOG%\"\r\n"
            "echo.\r\n"
            "pause\r\n"
            "exit /b 1\r\n",
            encoding="utf-8",
        )
        created.append(run_bat)

        diagnose_bat = root / "Diagnose GridNotes.bat"
        diagnose_bat.write_text(
            "@echo off\r\n"
            "setlocal\r\n"
            'cd /d "%~dp0"\r\n'
            'set "LOG=%~dp0launch-error.log"\r\n'
            'set "PY=%~dp0.venv\\Scripts\\python.exe"\r\n'
            'echo === GridNotes diagnose %date% %time% ===>"%LOG%"\r\n'
            'echo Folder: %CD%>>"%LOG%"\r\n'
            'dir /b >>"%LOG%" 2>&1\r\n'
            'if not exist "%PY%" (\r\n'
            '  echo ERROR: venv python missing>>"%LOG%"\r\n'
            "  goto :done\r\n"
            ")\r\n"
            '"%PY%" --version>>"%LOG%" 2>&1\r\n'
            '"%PY%" -c "import PyQt6">>"%LOG%" 2>&1\r\n'
            '"%PY%" -c "import racing_book">>"%LOG%" 2>&1\r\n'
            ":done\r\n"
            "type \"%LOG%\"\r\n"
            "echo.\r\n"
            "pause\r\n",
            encoding="utf-8",
        )
        created.append(diagnose_bat)
        created.append(starter)
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
        run_bat = root / "Run GridNotes.bat"
        if run_bat.is_file():
            return run_bat, root, None
        vbs = windows_vbs_launcher_path(root)
        if vbs.is_file():
            return vbs, root, None

    pyw = venv_pythonw(venv_dir)
    if pyw.is_file():
        main_py = (root / "main.py").resolve()
        return pyw.resolve(), root, f'"{main_py}"'
    py = venv_python(venv_dir)
    main_py = (root / "main.py").resolve()
    return py.resolve(), root, f'"{main_py}"'


def _windows_start_file(install_root: Path, launcher: Path) -> None:
    """Start a launcher and wait so startup errors surface in the console/log."""
    subprocess.Popen(
        ["cmd.exe", "/c", str(launcher)],
        cwd=str(install_root),
    )


def validate_install_for_launch(install_root: Path) -> tuple[bool, str]:
    """Verify the install folder can import GridNotes dependencies before launch."""
    install_root = install_root.resolve()
    main_py = install_root / "main.py"
    if not main_py.is_file():
        return False, f"main.py is missing in:\n{install_root}"

    if sys.platform == "win32" and not gridnotes_start_script_path(install_root).is_file():
        write_gridnotes_start_script(install_root)

    venv_dir = install_root / VENV_DIR_NAME
    py = venv_python(venv_dir)
    if not py.is_file():
        return (
            False,
            f"The virtual environment is incomplete.\n"
            f"Expected Python at:\n{py}\n\n"
            "Run Install GridNotes.bat again.",
        )

    try:
        result = subprocess.run(
            [str(py), "-c", "import PyQt6"],
            cwd=str(install_root),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"Could not verify the install:\n{exc}"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return (
            False,
            "GridNotes dependencies did not install correctly.\n\n"
            f"{detail}\n\n"
            "Run Install GridNotes.bat again. If this keeps failing, install "
            "Python 3.12 or 3.13 from python.org (3.14 can be problematic).",
        )
    return True, ""


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
        run_bat = install_root / "Run GridNotes.bat"
        if run_bat.is_file():
            try:
                _windows_start_file(install_root, run_bat)
                return True, ""
            except OSError as exc:
                return False, str(exc)

        vbs = windows_vbs_launcher_path(install_root)
        if vbs.is_file():
            try:
                _windows_start_file(install_root, vbs)
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
        self._install_python: str | None = None

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
        ok, message, install_python = resolve_install_python()
        if not ok or install_python is None:
            return False, message
        self._install_python = install_python

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
            venv_py = venv_python(self.venv_dir)
            if self.venv_dir.exists() and venv_py.is_file():
                existing = _python_version_for_executable(str(venv_py))
                if existing is not None and not _is_supported_python_version(*existing):
                    self._log(
                        f"Removing existing {self.venv_dir.name} "
                        f"(Python {existing[0]}.{existing[1]} is not supported)…"
                    )
                    shutil.rmtree(self.venv_dir)
                else:
                    self._log(f"Using existing {self.venv_dir.name}/")

            if not self.venv_dir.exists():
                self._log(f"Creating {self.venv_dir.name} with {self._install_python}")
                self._run([self._install_python, "-m", "venv", str(self.venv_dir)])
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

            save_install_location(self.root)

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
                if self.create_desktop_shortcut:
                    shortcut_note = (
                        "To open GridNotes: use the “GridNotes” icon on your Desktop.\n"
                        "Or double-click “Open GridNotes.bat” in your download folder."
                    )
                else:
                    shortcut_note = (
                        f'Open “Launch GridNotes.vbs” in:\n{self.root}\n'
                        "Or use “Open GridNotes.bat” in your download folder."
                    )
                summary = (
                    "Installation complete.\n\n"
                    f"Install folder: {self.root}\n\n"
                    f"{shortcut_note}\n\n"
                    "“Install GridNotes.bat” was only the installer — do not use it to run the app."
                )
            return True, summary
        except RuntimeError as exc:
            if str(exc) == "Installation cancelled.":
                return False, "Installation cancelled."
            return False, str(exc)
        except PermissionError:
            logger.exception("Install failed: permission denied")
            return False, permission_denied_install_message(self.root)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 5:
                logger.exception("Install failed: access denied")
                return False, permission_denied_install_message(self.root)
            logger.exception("Install failed")
            return False, str(exc)
        except subprocess.SubprocessError as exc:
            logger.exception("Install failed")
            return False, str(exc)
