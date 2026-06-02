"""Plain-language copy for install and update flows."""

from __future__ import annotations

import sys
from pathlib import Path

# Technical step labels from logic.InstallRunner → friendly progress text
INSTALL_STEP_LABELS: dict[str, str] = {
    "Checking Python": "Getting ready…",
    "Copying files to install location": "Copying GridNotes…",
    "Creating virtual environment": "Setting up GridNotes…",
    "Upgrading pip": "Preparing components…",
    "Installing dependencies": "Downloading what GridNotes needs…",
    "Installing build tools": "Almost ready…",
    "Generating application icon": "Setting up icons…",
    "Building standalone app (PyInstaller)": "Building GridNotes…",
    "Finishing Windows setup": "Setting up Windows shortcuts…",
    "Creating shortcuts": "Creating your Desktop icon…",
    "Finished": "All set!",
}


def friendly_install_step(technical_label: str) -> str:
    return INSTALL_STEP_LABELS.get(technical_label, technical_label)


def friendly_python_status(ok: bool, technical_message: str) -> str:
    if ok:
        return (
            "Everything looks good — click Install GridNotes when you're ready."
        )
    lowered = technical_message.lower()
    if "3.14" in technical_message or "3.14" in lowered:
        return (
            "GridNotes needs Python 3.12 or 3.13.\n\n"
            "1. Download Python from python.org (link opens when you install).\n"
            "2. On the first screen, turn on “Add python.exe to PATH”.\n"
            "3. Run Install GridNotes again.\n\n"
            "The installer can also try to install Python for you automatically."
        )
    if "could not determine" in lowered:
        return (
            "Python was not found on this PC.\n\n"
            "Install Python 3.12 or 3.13 from python.org, turn on "
            "“Add python.exe to PATH”, then run Install GridNotes again."
        )
    if "required" in lowered and "found" in lowered:
        return (
            "This Python version is too old or too new for GridNotes.\n\n"
            "Install Python 3.12 or 3.13 from python.org, then run "
            "Install GridNotes again."
        )
    return (
        "Python needs to be set up before GridNotes can install.\n\n"
        "Install Python 3.12 or 3.13 from python.org (check “Add to PATH”), "
        "then run Install GridNotes again."
    )


def permission_denied_message(
    install_root: Path,
    *,
    suggested_folder: Path | None = None,
) -> str:
    _ = install_root
    if sys.platform == "win32":
        hint = ""
        if suggested_folder is not None:
            hint = f"\n• Or use the default folder: {suggested_folder}"
        return (
            "Windows would not let GridNotes use that folder.\n\n"
            "Try one of these:\n"
            "• Click “Use default (no admin)” under Advanced options\n"
            "• Choose a folder on your D: drive"
            f"{hint}\n"
            "• Close this window, right-click Install GridNotes.bat, "
            "choose Run as administrator, then try Program Files again"
        )
    return (
        "GridNotes could not write to that folder.\n\n"
        "Choose a different folder or ask someone with administrator access to help."
    )


def install_success_message(
    install_root: Path,
    *,
    create_desktop_shortcut: bool,
    build_standalone: bool,
    dist_exe: Path | None = None,
) -> str:
    if build_standalone and dist_exe is not None and dist_exe.is_file():
        return (
            "Installation finished.\n\n"
            "You can open GridNotes from your Desktop icon, or share the "
            "standalone app from your build folder."
        )
    if create_desktop_shortcut:
        return (
            "You're all set!\n\n"
            "Open GridNotes from the “GridNotes” icon on your Desktop.\n\n"
            "Your notes and settings are stored separately and will not be lost."
        )
    return (
        "You're all set!\n\n"
        f"Open “Launch GridNotes” in:\n{install_root}\n\n"
        "Your notes and settings are stored separately and will not be lost."
    )


def install_failure_message(technical: str) -> str:
    """Turn technical errors into a short user message; details stay in the log."""
    lowered = technical.lower()
    if "cancelled" in lowered:
        return "Installation was cancelled."
    if "pyinstaller" in lowered or "gridnotes.exe was not found" in lowered:
        return (
            "GridNotes could not finish building the app.\n\n"
            "Turn on “Show installation details” and try again, or install "
            "without the standalone build option."
        )
    if len(technical) > 280:
        return (
            "Installation did not finish.\n\n"
            "Turn on “Show installation details” below for more information, "
            "or see install-helper.log in your download folder."
        )
    return technical


# --- Updates ---

UPDATE_PROGRESS_LABELS: dict[str, str] = {
    "Connecting to GitHub…": "Connecting…",
    "Pulling latest code from GitHub…": "Updating…",
    "Refreshing Windows launchers and shortcuts…": "Updating shortcuts and icon…",
    "Extracting release…": "Unpacking the update…",
    "Preparing files…": "Preparing the update…",
    "Installing update (GridNotes will close)…": "Almost done — GridNotes will close briefly…",
    "Installing files…": "Installing the update…",
    "Closing GridNotes to finish installing…": "Closing GridNotes to finish…",
    "Restarting GridNotes…": "Reopening GridNotes…",
    "Reopening GridNotes…": "Reopening GridNotes…",
    "Finishing…": "Finishing up…",
    "Starting update…": "Starting…",
    "Preparing update…": "Getting ready…",
    "Updating…": "Updating…",
}


def friendly_update_progress(message: str) -> str:
    if message in UPDATE_PROGRESS_LABELS:
        return UPDATE_PROGRESS_LABELS[message]
    if message.startswith("Updating… ("):
        return "Updating…"
    if message.startswith("Downloading update… ("):
        return "Updating…"
    return message


def update_check_user_message(
    *,
    update_available: bool,
    current: str,
    latest: str | None,
    release_ok: bool,
    release_message: str,
    can_apply: bool,
    apply_method: str | None,
    is_frozen: bool,
) -> str:
    if not release_ok and not update_available:
        lowered = release_message.lower()
        if "could not reach" in lowered or "github" in lowered:
            return (
                "Could not check for updates right now.\n"
                "Check your internet connection and try again."
            )
        return "Could not check for updates right now. Try again in a few minutes."

    if update_available and latest:
        headline = f"A new version is available: v{latest}."
        if current:
            headline = f"A new version is available: v{latest} (you have v{current})."
        if can_apply and apply_method in ("portable", "frozen", "installer"):
            return (
                f"{headline}\n\n"
                "Click Update now. GridNotes will update in place, close for a moment, "
                "and reopen automatically. Your notes and settings stay safe."
            )
        if can_apply and apply_method == "git":
            return (
                f"{headline}\n\n"
                "Click Update now to install the latest version and restart GridNotes."
            )
        if is_frozen:
            return (
                f"{headline}\n\n"
                "This build cannot update automatically. Click Get latest version to open "
                "the GitHub releases page."
            )
        return f"{headline}\n\nClick Update now for download instructions."

    if latest and current:
        return f"You're up to date (version {current})."
    return "You're up to date."


def portable_update_scheduled_message() -> str:
    return (
        "GridNotes will close for a moment and reopen when the update is finished.\n\n"
        "Your notes and settings are safe."
    )


def portable_update_failed_message() -> str:
    return (
        "The update could not be completed.\n\n"
        "Check your internet connection and try again from Settings → Check for updates."
    )


def source_update_success_message() -> str:
    return "Update installed. Restarting GridNotes…"


def source_update_failed_message(technical: str) -> str:
    lowered = technical.lower()
    if "not a git" in lowered:
        return "This copy of GridNotes cannot be updated from here. Use Update now after checking for updates."
    if len(technical) > 200:
        return (
            "The update did not finish.\n\n"
            "Try Check for updates again, or download the latest version from the website."
        )
    return technical
