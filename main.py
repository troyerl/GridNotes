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

from PyQt6.QtWidgets import QApplication

from gridnotes.app.app_icon import load_app_icon, set_windows_app_user_model_id
from gridnotes.app.gridnotes_app import GridNotesApp
from gridnotes.data.db import init_db
from gridnotes.services.log_config import setup_logging
from gridnotes.ui.icons import load_font
from gridnotes.ui.theme import apply_app_theme


def main() -> int:
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

    window = GridNotesApp()
    if icon is not None:
        window.setWindowIcon(icon)

    window.show()
    if sys.platform == "win32":
        from PyQt6.QtCore import QTimer

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

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
