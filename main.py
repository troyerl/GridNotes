import sys
from pathlib import Path

import logging

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from racing_book.db import get_data_dir_path
from racing_book.racebook_app import RaceBookApp
from racing_book.theme import APP_STYLESHEET


def _app_icon_path() -> Path | None:
    if getattr(sys, "frozen", False):
        path = Path(sys._MEIPASS) / "icon.png"
    else:
        path = Path(__file__).resolve().parent / "icon.png"
    return path if path.is_file() else None


def _load_app_icon() -> QIcon | None:
    path = _app_icon_path()
    if path is None:
        return None
    icon = QIcon(str(path))
    return icon if not icon.isNull() else None


def main() -> int:
    # Log to a file so Windows users can debug even without a console.
    try:
        log_path = get_data_dir_path() / "racingbook.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            handlers=[logging.FileHandler(log_path, encoding="utf-8")],
        )
        logging.getLogger(__name__).info("App starting. Log file: %s", log_path)
    except Exception:
        # If logging setup fails, continue without it.
        pass

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)

    icon = _load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    window = RaceBookApp()
    if icon is not None:
        window.setWindowIcon(icon)

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())