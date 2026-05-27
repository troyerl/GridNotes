import sys

from PyQt6.QtWidgets import QApplication

from racing_book.racebook_app import RaceBookApp


def main() -> int:
    app = QApplication(sys.argv)
    window = RaceBookApp()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())