"""Startup splash screen shown while the main window initializes."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QShowEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .appearance import get_theme_id
from .theme_tokens import theme_tokens
from .ui_widgets import BusySpinner


class StartupSplash(QWidget):
    """Frameless splash with app branding and a loading spinner."""

    def __init__(self, icon: QIcon | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint,
        )
        self.setObjectName("startupSplashWindow")
        self.setFixedSize(380, 228)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("QWidget#startupSplashWindow { background: transparent; }")

        tokens = theme_tokens(get_theme_id())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        panel = QFrame()
        panel.setObjectName("startupSplash")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel.setStyleSheet(
            f"""
            QFrame#startupSplash {{
                background-color: {tokens["bg_elevated"]};
                border: 1px solid {tokens["border_strong"]};
                border-radius: 14px;
            }}
            QLabel#startupSplashTitle {{
                font-size: 22px;
                font-weight: 700;
                color: {tokens["text_primary"]};
                background: transparent;
            }}
            QLabel#startupSplashMessage {{
                font-size: 13px;
                color: {tokens["text_muted"]};
                background: transparent;
            }}
            """
        )
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(14)
        if icon is not None and not icon.isNull():
            icon_label = QLabel(panel)
            icon_label.setPixmap(icon.pixmap(48, 48))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            icon_label.setStyleSheet("background: transparent;")
            header.addWidget(icon_label)
        title = QLabel("GridNotes", panel)
        title.setObjectName("startupSplashTitle")
        header.addWidget(title, stretch=1)
        layout.addLayout(header)

        self._message_label = QLabel("Starting…", panel)
        self._message_label.setObjectName("startupSplashMessage")
        layout.addWidget(self._message_label)

        spinner_row = QHBoxLayout()
        spinner_row.addStretch()
        self._spinner = BusySpinner(panel, diameter=56)
        spinner_row.addWidget(self._spinner)
        spinner_row.addStretch()
        layout.addLayout(spinner_row)

        self._center_on_screen()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._spinner.start()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(
            geo.center().x() - self.width() // 2,
            geo.center().y() - self.height() // 2,
        )

    def set_message(self, message: str) -> None:
        self._message_label.setText(message or "Starting…")
        self._pump_events()

    @staticmethod
    def _pump_events() -> None:
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def finish(self, main_window: QWidget | None = None) -> None:
        self._spinner.stop()
        if main_window is not None:
            main_window.raise_()
            main_window.activateWindow()
        self.close()
