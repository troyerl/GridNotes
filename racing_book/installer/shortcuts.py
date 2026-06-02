"""Desktop shortcuts for GridNotes."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_SHORTCUT_NAME = "GridNotes"


def desktop_directories() -> list[Path]:
    """All Desktop folders that might hold a GridNotes shortcut (Windows checks several)."""
    seen: set[Path] = set()
    directories: list[Path] = []

    def add(path: Path) -> None:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            resolved = path
        if resolved in seen or not resolved.is_dir():
            return
        seen.add(resolved)
        directories.append(resolved)

    home = Path.home()
    if sys.platform == "win32":
        userprofile = Path(os.environ.get("USERPROFILE", str(home)))
        for candidate in (
            userprofile / "Desktop",
            userprofile / "OneDrive" / "Desktop",
            userprofile / "OneDrive - Personal" / "Desktop",
        ):
            add(candidate)
        public = os.environ.get("PUBLIC", "").strip()
        if public:
            add(Path(public) / "Desktop")
    else:
        add(home / "Desktop")

    return directories


def desktop_directory() -> Path:
    """Primary Desktop folder (first match)."""
    directories = desktop_directories()
    if directories:
        return directories[0]
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    return Path.home() / "Desktop"


def _escape_ps(path: Path) -> str:
    return str(path).replace("'", "''")


def windows_icon_location(icon: Path) -> str:
    """Format a path for WScript Shell Shortcut.IconLocation (path,index)."""
    resolved = str(icon.resolve())
    if icon.suffix.lower() in (".ico", ".exe", ".dll"):
        return f"{resolved},0"
    return resolved


def _create_windows_lnk(
    *,
    shortcut_path: Path,
    target: Path,
    working_dir: Path,
    description: str,
    icon: Path | None = None,
    arguments: str | None = None,
) -> None:
    icon_stmt = ""
    if icon is not None and icon.is_file():
        icon_loc = windows_icon_location(icon).replace("'", "''")
        icon_stmt = f"$s.IconLocation = '{icon_loc}'; "

    args_stmt = ""
    if arguments:
        args_stmt = f"$s.Arguments = '{arguments.replace(chr(39), chr(39) + chr(39))}'; "

    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{_escape_ps(shortcut_path)}'); "
        f"$s.TargetPath = '{_escape_ps(target)}'; "
        f"$s.WorkingDirectory = '{_escape_ps(working_dir)}'; "
        f"{args_stmt}"
        f"$s.Description = '{description.replace(chr(39), chr(39) + chr(39))}'; "
        f"{icon_stmt}"
        "$s.Save()"
    )
    kwargs: dict = {
        "check": True,
        "capture_output": True,
        "text": True,
    }
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if flags:
            kwargs["creationflags"] = flags
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        **kwargs,
    )
    try:
        from .windows_shell import apply_shortcut_taskbar_identity

        apply_shortcut_taskbar_identity(shortcut_path, icon)
    except Exception as exc:
        logger.warning("Could not set shortcut taskbar identity: %s", exc)


def create_desktop_shortcut(
    *,
    target: Path,
    working_dir: Path,
    name: str = APP_SHORTCUT_NAME,
    icon: Path | None = None,
    arguments: str | None = None,
) -> Path:
    """
    Create a desktop shortcut to *target*.

    Windows: .lnk file. macOS/Linux: copy launcher script to Desktop.
    """
    desktop = desktop_directory()
    desktop.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        shortcut_path = desktop / f"{name}.lnk"
        _create_windows_lnk(
            shortcut_path=shortcut_path,
            target=target,
            working_dir=working_dir,
            description="GridNotes — iRacing driver scouting",
            icon=icon,
            arguments=arguments,
        )
        logger.info("Created desktop shortcut: %s", shortcut_path)
        return shortcut_path

    if target.suffix.lower() in (".command", ".sh", ".bat"):
        dest = desktop / target.name
        if dest.exists():
            dest.unlink()
        shutil.copy2(target, dest)
        dest.chmod(0o755)
        logger.info("Created desktop launcher: %s", dest)
        return dest

    raise OSError(f"Cannot create a desktop shortcut for {target} on this platform.")


def _read_windows_shortcut(shortcut_path: Path) -> tuple[str, str, str]:
    """Return (TargetPath, Arguments, IconLocation) for a .lnk file."""
    escaped = _escape_ps(shortcut_path.resolve())
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('" + escaped + "'); "
        "Write-Output $s.TargetPath; "
        "if ($s.Arguments) { Write-Output $s.Arguments } else { Write-Output '' }; "
        "if ($s.IconLocation) { Write-Output $s.IconLocation } else { Write-Output '' }"
    )
    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "check": True,
    }
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if flags:
            kwargs["creationflags"] = flags
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        **kwargs,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    target = lines[0] if lines else ""
    arguments = lines[1] if len(lines) > 1 else ""
    icon_location = lines[2] if len(lines) > 2 else ""
    return target, arguments, icon_location


def _read_windows_shortcut_target(shortcut_path: Path) -> tuple[str, str]:
    target, arguments, _icon = _read_windows_shortcut(shortcut_path)
    return target, arguments


def _shortcut_uses_script_host(shortcut_path: Path) -> bool:
    """True when a shortcut still launches via wscript/cscript or a .vbs file."""
    try:
        target, _arguments = _read_windows_shortcut_target(shortcut_path)
    except (subprocess.SubprocessError, OSError) as exc:
        logger.debug("Could not read shortcut %s: %s", shortcut_path, exc)
        return False
    lowered = target.lower()
    return lowered.endswith("wscript.exe") or lowered.endswith("cscript.exe") or lowered.endswith(".vbs")


def _shortcut_should_refresh_for_launcher(
    shortcut_path: Path,
    launcher_exe: Path,
    install_root: Path,
) -> bool:
    """True when the shortcut should be rebuilt for the branded Scripts launcher."""
    if not launcher_exe.is_file():
        return _shortcut_uses_script_host(shortcut_path)
    try:
        target, arguments, icon_location = _read_windows_shortcut(shortcut_path)
    except (subprocess.SubprocessError, OSError) as exc:
        logger.debug("Could not read shortcut %s: %s", shortcut_path, exc)
        return True
    if _shortcut_uses_script_host(shortcut_path):
        return True
    lowered = target.lower()
    if lowered.endswith("pythonw.exe") or lowered.endswith("python.exe"):
        return True
    try:
        resolved_target = Path(target).resolve()
        resolved_launcher = launcher_exe.resolve()
        if resolved_target != resolved_launcher:
            legacy_root_exe = install_root.resolve() / "GridNotes.exe"
            if resolved_target == legacy_root_exe:
                return True
            return True
        starter = install_root.resolve() / "gridnotes_start.py"
        if starter.is_file() and str(starter.resolve()).lower() not in (
            arguments or ""
        ).lower():
            return True
        from .logic import windows_pin_icon_path

        pin_icon = windows_pin_icon_path(install_root)
        if pin_icon is not None:
            expected_icon = windows_icon_location(pin_icon).lower()
        elif install_root.resolve().joinpath("icon.ico").is_file():
            expected_icon = windows_icon_location(
                install_root.resolve() / "icon.ico"
            ).lower()
        else:
            expected_icon = windows_icon_location(resolved_launcher).lower()
        if icon_location.lower() != expected_icon:
            return True
    except OSError:
        return True
    return False


def _known_windows_shortcut_paths(install_root: Path) -> list[Path]:
    paths = list(find_desktop_shortcuts())
    start_menu = start_menu_shortcut_path()
    if start_menu.is_file():
        paths.append(start_menu)
    install_lnk = install_root.resolve() / f"{APP_SHORTCUT_NAME}.lnk"
    if install_lnk.is_file():
        paths.append(install_lnk)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def provision_windows_install_shortcuts(
    install_root: Path,
    *,
    target: Path,
    working_dir: Path,
    arguments: str | None,
    icon: Path | None,
    force_refresh: bool = False,
) -> None:
    """Create missing shortcuts and refresh branding (Desktop, Start Menu, install folder)."""
    if sys.platform != "win32":
        return

    shortcut_kwargs = {
        "target": target,
        "working_dir": working_dir,
        "arguments": arguments,
        "icon": icon,
    }
    if not find_desktop_shortcuts():
        create_desktop_shortcut(**shortcut_kwargs)
    start_path = start_menu_shortcut_path()
    if not start_path.is_file():
        create_start_menu_shortcut(**shortcut_kwargs)
    install_lnk = install_root.resolve() / f"{APP_SHORTCUT_NAME}.lnk"
    if not install_lnk.is_file():
        create_install_folder_shortcut(install_root, **shortcut_kwargs)

    ensure_windows_shortcuts_for_taskbar(
        install_root,
        force_refresh=force_refresh,
        **shortcut_kwargs,
    )


def ensure_windows_shortcuts_for_taskbar(
    install_root: Path,
    *,
    target: Path,
    working_dir: Path,
    arguments: str | None,
    icon: Path | None,
    force_refresh: bool = False,
) -> None:
    """
    Upgrade legacy wscript/.vbs shortcuts and refresh AppUserModelID branding.

    Pin **GridNotes.lnk** or the Desktop shortcut — not a generic Python taskbar button.
    """
    if sys.platform != "win32":
        return

    from .logic import windows_launcher_exe_path

    from .logic import windows_pin_icon_path
    from .windows_shell import apply_shortcut_taskbar_identity, build_relaunch_command

    launcher_exe = windows_launcher_exe_path(install_root)
    pin_icon = icon or windows_pin_icon_path(install_root)
    relaunch = build_relaunch_command(install_root)
    description = "GridNotes — iRacing driver scouting"
    for shortcut_path in _known_windows_shortcut_paths(install_root):
        try:
            if force_refresh or _shortcut_should_refresh_for_launcher(
                shortcut_path, launcher_exe, install_root
            ):
                logger.info("Refreshing shortcut for taskbar pin: %s", shortcut_path)
                _create_windows_lnk(
                    shortcut_path=shortcut_path,
                    target=target,
                    working_dir=working_dir,
                    description=description,
                    icon=pin_icon,
                    arguments=arguments,
                )
            apply_shortcut_taskbar_identity(
                shortcut_path,
                pin_icon,
                relaunch_command=relaunch,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Could not update shortcut %s: %s", shortcut_path, exc)


def find_desktop_shortcuts(name: str = APP_SHORTCUT_NAME) -> list[Path]:
    """Return every GridNotes shortcut file on the Desktop(s)."""
    found: list[Path] = []
    seen: set[Path] = set()
    if sys.platform == "win32":
        filenames = (f"{name}.lnk", "GridNotes.lnk")
    else:
        filenames = ("Run GridNotes.command", f"{name}.command", "GridNotes.command")

    for desktop in desktop_directories():
        for filename in filenames:
            path = desktop / filename
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path
            if resolved in seen or not resolved.is_file():
                continue
            seen.add(resolved)
            found.append(resolved)
    return found


def remove_all_desktop_shortcuts(name: str = APP_SHORTCUT_NAME) -> list[Path]:
    """Remove GridNotes shortcuts from every known Desktop folder."""
    removed: list[Path] = []
    for path in find_desktop_shortcuts(name):
        try:
            path.unlink()
            logger.info("Removed desktop shortcut: %s", path)
            removed.append(path)
        except OSError as exc:
            logger.warning("Could not remove shortcut %s: %s", path, exc)
    return removed


def remove_desktop_shortcut(name: str = APP_SHORTCUT_NAME) -> bool:
    """Remove the GridNotes desktop shortcut if it exists."""
    return bool(remove_all_desktop_shortcuts(name))


def start_menu_shortcut_path(name: str = APP_SHORTCUT_NAME) -> Path:
    """Start Menu location for a GridNotes launcher shortcut."""
    programs = Path(os.environ.get("APPDATA", "")).expanduser()
    return programs / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{name}.lnk"


def create_start_menu_shortcut(
    *,
    target: Path,
    working_dir: Path,
    name: str = APP_SHORTCUT_NAME,
    icon: Path | None = None,
    arguments: str | None = None,
) -> Path:
    """Create a Start Menu shortcut with proper taskbar/pin identity."""
    shortcut_path = start_menu_shortcut_path(name)
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    _create_windows_lnk(
        shortcut_path=shortcut_path,
        target=target,
        working_dir=working_dir,
        description="GridNotes — iRacing driver scouting",
        icon=icon,
        arguments=arguments,
    )
    logger.info("Created Start Menu shortcut: %s", shortcut_path)
    return shortcut_path


def create_install_folder_shortcut(
    install_root: Path,
    *,
    target: Path,
    working_dir: Path,
    name: str = APP_SHORTCUT_NAME,
    icon: Path | None = None,
    arguments: str | None = None,
) -> Path:
    """Create GridNotes.lnk in the install folder (useful for pinning to the taskbar)."""
    shortcut_path = install_root.resolve() / f"{name}.lnk"
    _create_windows_lnk(
        shortcut_path=shortcut_path,
        target=target,
        working_dir=working_dir,
        description="GridNotes — iRacing driver scouting",
        icon=icon,
        arguments=arguments,
    )
    logger.info("Created install-folder shortcut: %s", shortcut_path)
    return shortcut_path
