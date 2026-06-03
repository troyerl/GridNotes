"""Register GridNotes in Windows Settings → Apps (Add/Remove Programs)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_APP_NAME = "GridNotes"
UNINSTALL_SUBKEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{REGISTRY_APP_NAME}"


def _registry_hive(install_root: Path) -> int:
    import winreg

    if sys.platform != "win32":
        return winreg.HKEY_CURRENT_USER

    from gridnotes.installer.logic import install_path_under_program_files, is_windows_admin

    if install_path_under_program_files(install_root) and is_windows_admin():
        return winreg.HKEY_LOCAL_MACHINE
    return winreg.HKEY_CURRENT_USER


def uninstall_launcher_path(install_root: Path) -> Path:
    install_root = install_root.resolve()
    inno_uninstaller = install_root / "unins000.exe"
    if inno_uninstaller.is_file():
        return inno_uninstaller
    vbs = install_root / "Uninstall GridNotes.vbs"
    if vbs.is_file():
        return vbs
    return (install_root / "Uninstall GridNotes.bat").resolve()


def registry_install_root() -> Path | None:
    """Install folder from Settings → Apps (InstallLocation), if GridNotes.exe exists."""
    if sys.platform != "win32":
        return None

    import winreg

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, UNINSTALL_SUBKEY) as key:
                location, _ = winreg.QueryValueEx(key, "InstallLocation")
        except OSError:
            continue
        if not location:
            continue
        root = Path(str(location)).resolve()
        if (root / "GridNotes.exe").is_file():
            return root
    return None


def uninstall_command_line(install_root: Path) -> str:
    launcher = uninstall_launcher_path(install_root)
    if launcher.name.lower() == "unins000.exe":
        return f'"{launcher}"'
    if launcher.suffix.lower() == ".vbs":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        wscript = Path(system_root) / "System32" / "wscript.exe"
        return f'"{wscript}" "{launcher}"'
    return f'"{launcher}"'


def register_windows_uninstall(install_root: Path, version: str | None = None) -> None:
    """Add GridNotes to Settings → Apps → Installed apps (install-helper installs)."""
    if sys.platform != "win32":
        return

    import winreg

    from gridnotes.app.app_version import WINDOWS_PUBLISHER, installed_version, write_installed_version

    install_root = install_root.resolve()
    launcher = uninstall_launcher_path(install_root)
    if not launcher.is_file():
        logger.warning("Skipping Apps list registration; missing %s", launcher)
        return

    version = (version or installed_version()).strip()
    write_installed_version(install_root, version)
    uninstall_string = uninstall_command_line(install_root)
    if launcher.name.lower() == "unins000.exe":
        quiet_uninstall = f'{uninstall_string} /VERYSILENT'
    else:
        quiet_uninstall = f"{uninstall_string} /quiet"

    icon = install_root / "icon.ico"
    display_icon = str(icon.resolve()) if icon.is_file() else uninstall_string

    estimated_size_kb = 0
    try:
        total_bytes = sum(
            f.stat().st_size for f in install_root.rglob("*") if f.is_file()
        )
        estimated_size_kb = max(1, total_bytes // 1024)
    except OSError:
        pass

    registered: list[str] = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.CreateKey(hive, UNINSTALL_SUBKEY) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "GridNotes")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, WINDOWS_PUBLISHER)
                winreg.SetValueEx(
                    key, "InstallLocation", 0, winreg.REG_SZ, str(install_root)
                )
                winreg.SetValueEx(
                    key, "UninstallString", 0, winreg.REG_SZ, uninstall_string
                )
                winreg.SetValueEx(
                    key, "QuietUninstallString", 0, winreg.REG_SZ, quiet_uninstall
                )
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, display_icon)
                winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
                if estimated_size_kb:
                    winreg.SetValueEx(
                        key, "EstimatedSize", 0, winreg.REG_DWORD, estimated_size_kb
                    )
            registered.append(
                "HKLM" if hive == winreg.HKEY_LOCAL_MACHINE else "HKCU"
            )
        except OSError as exc:
            logger.debug(
                "Could not register GridNotes in Windows Apps list (hive=%s): %s",
                hive,
                exc,
            )

    if registered:
        logger.info(
            "Registered GridNotes v%s in Windows Apps list (%s, path=%s)",
            version,
            ", ".join(registered),
            install_root,
        )
    else:
        logger.warning("Could not register GridNotes in Windows Apps list")


def unregister_windows_uninstall(install_root: Path | None = None) -> None:
    """Remove GridNotes from Settings → Apps."""
    if sys.platform != "win32":
        return

    import winreg

    hives = {winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE}
    if install_root is not None:
        hives.add(_registry_hive(install_root))

    for hive in hives:
        try:
            winreg.DeleteKey(hive, UNINSTALL_SUBKEY)
            logger.info("Removed GridNotes from Windows Apps list (hive=%s)", hive)
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning("Could not remove Apps list entry: %s", exc)
