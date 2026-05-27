import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from racing_book.racebook_app import RaceBookApp


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
    app = QApplication(sys.argv)

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