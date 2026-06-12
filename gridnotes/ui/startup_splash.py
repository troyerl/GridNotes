"""Startup splash screen shown while the main window initializes."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QEventLoop, Qt, QTimer
from PyQt6.QtGui import QIcon, QPainterPath, QRegion, QShowEvent
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

_CORNER_RADIUS = 14
_PUMP_INTERVAL_MS = 16


class StartupSplash(QWidget):
    """Frameless splash with app branding and a loading spinner."""

    def __init__(self, icon: QIcon | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint,
        )
        self.setFixedSize(380, 228)
        # Translucent outer shells flicker on Windows; use an opaque masked window there.
        self._use_translucent_shell = sys.platform != "win32"

        tokens = theme_tokens(get_theme_id())
        panel_style = (
            f"background-color: {tokens['bg_elevated']};"
            f" border: 1px solid {tokens['border_strong']};"
            f" border-radius: {_CORNER_RADIUS}px;"
        )
        label_styles = f"""
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

        if self._use_translucent_shell:
            self.setObjectName("startupSplashWindow")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)
            self.setStyleSheet("QWidget#startupSplashWindow { background: transparent; }")

            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)

            panel = QFrame()
            panel.setObjectName("startupSplash")
            panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            panel.setStyleSheet(
                f"QFrame#startupSplash {{ {panel_style} }} {label_styles}"
            )
            outer.addWidget(panel)
            content_root: QWidget = panel
        else:
            self.setObjectName("startupSplash")
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setAutoFillBackground(True)
            self.setStyleSheet(
                f"QWidget#startupSplash {{ {panel_style} }} {label_styles}"
            )
            content_root = self

        layout = QVBoxLayout(content_root)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(14)
        if icon is not None and not icon.isNull():
            icon_label = QLabel(content_root)
            icon_label.setPixmap(icon.pixmap(48, 48))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            icon_label.setStyleSheet("background: transparent;")
            header.addWidget(icon_label)
        title = QLabel("GridNotes", content_root)
        title.setObjectName("startupSplashTitle")
        header.addWidget(title, stretch=1)
        layout.addLayout(header)

        self._message_label = QLabel("Starting…", content_root)
        self._message_label.setObjectName("startupSplashMessage")
        layout.addWidget(self._message_label)

        spinner_row = QHBoxLayout()
        spinner_row.addStretch()
        self._spinner = BusySpinner(content_root, diameter=56)
        spinner_row.addWidget(self._spinner)
        spinner_row.addStretch()
        layout.addLayout(spinner_row)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(_PUMP_INTERVAL_MS)
        self._pulse_timer.timeout.connect(self._pump_events)

        self._center_on_screen()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_rounded_mask()
        self._spinner.start()
        self._pulse_timer.start()

    def _apply_rounded_mask(self) -> None:
        if self._use_translucent_shell:
            return
        from PyQt6.QtCore import QRectF

        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0, 0, self.width(), self.height()),
            _CORNER_RADIUS,
            _CORNER_RADIUS,
        )
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

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

    @staticmethod
    def _pump_events() -> None:
        app = QApplication.instance()
        if app is not None:
            app.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def finish(self, main_window: QWidget | None = None) -> None:
        self._pulse_timer.stop()
        self._spinner.stop()
        if main_window is not None:
            main_window.raise_()
            main_window.activateWindow()
        self.close()
