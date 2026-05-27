import sys

from PyQt6.QtWidgets import QApplication

from racing_book.app_icon import load_app_icon, set_windows_app_user_model_id
from racing_book.log_config import setup_logging
from racing_book.racebook_app import RaceBookApp
from racing_book.theme import APP_STYLESHEET


def main() -> int:
    set_windows_app_user_model_id()
    setup_logging()

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)

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
