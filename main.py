import argparse
import sys

# Must run before Qt loads (including via gridnotes.app.app_icon).
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "GridNotes.GridNotes.1"
        )
    except Exception:
        pass

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication

from gridnotes.app.app_icon import load_app_icon, set_windows_app_user_model_id
from gridnotes.app.gridnotes_app import GridNotesApp
from gridnotes.data.db import init_db
from gridnotes.services.log_config import setup_logging
from gridnotes.ui.icons import load_font
from gridnotes.ui.startup_splash import StartupSplash
from gridnotes.ui.theme import apply_app_theme

_SPLASH_PREVIEW_MESSAGES = (
    "Starting…",
    "Loading database…",
    "Building interface…",
    "Loading drivers…",
)


def preview_startup_splash() -> int:
    """Show the startup splash only (for design review). Press Esc to quit."""
    set_windows_app_user_model_id()
    app = QApplication(sys.argv)
    app.setApplicationName("GridNotes")
    load_font()
    apply_app_theme(app)

    icon = load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    splash = StartupSplash(icon=icon)
    shortcut = QShortcut(QKeySequence("Esc"), splash)
    shortcut.activated.connect(app.quit)

    message_index = 0

    def show_next_message() -> None:
        nonlocal message_index
        splash.set_message(_SPLASH_PREVIEW_MESSAGES[message_index % len(_SPLASH_PREVIEW_MESSAGES)])
        message_index += 1

    show_next_message()
    splash.show()

    timer = QTimer()
    timer.timeout.connect(show_next_message)
    timer.start(1800)

    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="GridNotes")
    parser.add_argument(
        "--preview-splash",
        action="store_true",
        help="Open the startup splash only (Esc to close).",
    )
    args, _unknown = parser.parse_known_args()
    if args.preview_splash:
        return preview_startup_splash()

    set_windows_app_user_model_id()
    setup_logging()
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("GridNotes")
    if hasattr(app, "setApplicationDisplayName"):
        app.setApplicationDisplayName("GridNotes")
    load_font()
    apply_app_theme(app)

    icon = load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    splash = StartupSplash(icon=icon)
    splash.show()
    app.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def _launch_main_window() -> None:
        window = GridNotesApp(splash=splash)
        if icon is not None:
            window.setWindowIcon(icon)
        window.show()
        app.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        splash.finish(window)
        if sys.platform == "win32":

            def _apply_windows_taskbar_branding() -> None:
                try:
                    from gridnotes.app.app_icon import shell_icon_path
                    from gridnotes.installer.uninstall import resolve_install_root
                    from gridnotes.platform.windows.windows_shell import (
                        apply_window_taskbar_identity,
                        build_relaunch_command,
                    )

                    install_root = resolve_install_root()
                    relaunch = (
                        build_relaunch_command(install_root) if install_root else None
                    )
                    apply_window_taskbar_identity(
                        window,
                        shell_icon_path(),
                        relaunch_command=relaunch,
                        display_name="GridNotes",
                    )
                except Exception:
                    pass

            QTimer.singleShot(0, _apply_windows_taskbar_branding)
            QTimer.singleShot(750, _apply_windows_taskbar_branding)

    QTimer.singleShot(0, _launch_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
