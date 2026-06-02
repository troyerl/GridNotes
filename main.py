import sys

# Must run before Qt loads (including via racing_book.app.app_icon).
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "GridNotes.GridNotes.1"
        )
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication

from racing_book.app.app_icon import load_app_icon, set_windows_app_user_model_id
from racing_book.app.racebook_app import RaceBookApp
from racing_book.data.db import init_db
from racing_book.services.log_config import setup_logging
from racing_book.ui.theme import apply_app_theme


def main() -> int:
    set_windows_app_user_model_id()
    setup_logging()
    init_db()

    app = QApplication(sys.argv)
    apply_app_theme(app)

    icon = load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    window = RaceBookApp()
    if icon is not None:
        window.setWindowIcon(icon)

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
