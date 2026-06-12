"""Reusable Qt widgets."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QElapsedTimer, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QTextDocument
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .icons import BUTTON_ICON_TEXT_GAP, current_icon_fg, fa_icon, settings_section_icon
from .theme import configure_scroll_area


class BusySpinner(QWidget):
    """Indeterminate arc spinner for modal waiting states."""

    _REPAINT_MS = 16
    _ARC_SPAN_DEG = 270
    _ROTATION_MS = 1100

    def __init__(self, parent: QWidget | None = None, *, diameter: int = 28) -> None:
        super().__init__(parent)
        self.setObjectName("busySpinner")
        self._diameter = diameter
        self._elapsed = QElapsedTimer()
        self.setFixedSize(diameter, diameter)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(self._REPAINT_MS)
        self._timer.timeout.connect(self.update)

    def start(self) -> None:
        self._elapsed.start()
        self._timer.start()
        self.setVisible(True)
        self.update()

    def stop(self) -> None:
        self._timer.stop()
        self.setVisible(False)

    def _current_angle(self) -> float:
        if not self._elapsed.isValid():
            return 0.0
        elapsed_ms = self._elapsed.elapsed()
        return (elapsed_ms * 360.0 / self._ROTATION_MS) % 360.0

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pad = max(2, self._diameter // 10)
        rect = self.rect().adjusted(pad, pad, -pad, -pad)
        highlight = self.palette().color(self.palette().ColorRole.Highlight)
        pen_width = max(2, self._diameter // 9)

        track_color = highlight
        track_color.setAlpha(max(30, highlight.alpha() // 4))
        track = QPen(track_color)
        track.setWidth(pen_width)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track)
        painter.drawArc(rect, 0, 360 * 16)

        pen = QPen(highlight)
        pen.setWidth(pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        angle = self._current_angle()
        painter.drawArc(rect, int(-angle * 16), -self._ARC_SPAN_DEG * 16)
        painter.end()


class WrappingLabel(QLabel):
    """Label that wraps long text and reports correct height in scroll areas."""

    def __init__(self, text: str = "—", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        if width <= 0:
            return super().sizeHint().height()
        bounds = self.fontMetrics().boundingRect(
            0,
            0,
            width,
            10_000,
            int(Qt.TextFlag.TextWordWrap),
            self.text(),
        )
        return bounds.height() + 6


class HtmlHintLabel(QLabel):
    """Word-wrapped label that supports simple HTML and external links."""

    _HEIGHT_PAD = 8

    def __init__(self, html: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sectionHint")
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setOpenExternalLinks(True)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._layout_width = -1
        if html:
            self.setText(html)

    def setText(self, text: str) -> None:
        super().setText(text)
        self._layout_width = -1
        self._apply_wrapped_height()

    def hasHeightForWidth(self) -> bool:
        return True

    def _content_width(self) -> int:
        width = self.width()
        if width > 0:
            return width
        parent = self.parentWidget()
        if parent is not None and parent.width() > 0:
            margins = 24
            return max(1, parent.width() - margins)
        return 0

    def _document_height(self, width: int) -> int:
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        doc.setDocumentMargin(2)
        doc.setHtml(self.text())
        doc.setTextWidth(float(max(1, width)))
        return int(doc.size().height())

    def heightForWidth(self, width: int) -> int:
        if width <= 0:
            return super().sizeHint().height()
        return self._document_height(width) + self._HEIGHT_PAD

    def sizeHint(self) -> QSize:
        width = self._content_width() or 320
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _apply_wrapped_height(self) -> None:
        width = self._content_width()
        if width <= 0:
            return
        need = self.heightForWidth(width)
        if self.minimumHeight() != need:
            self.setMinimumHeight(need)
        self.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width = event.size().width()
        if width > 0 and width != self._layout_width:
            self._layout_width = width
            self._apply_wrapped_height()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_wrapped_height()


class AccordionSection(QFrame):
    """Single collapsible section (header button + body)."""

    toggled = pyqtSignal(bool)

    def __init__(
        self,
        title: str,
        body_html: str,
        *,
        expanded: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("accordionSection")
        self._title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = QPushButton()
        self._header.setObjectName("accordionHeader")
        self._header.setCheckable(True)
        self._header.setChecked(expanded)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self._on_header_clicked)
        layout.addWidget(self._header)

        self._body = QFrame()
        self._body.setObjectName("accordionBody")
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(12, 6, 12, 10)
        body_layout.setSpacing(0)
        self._label = HtmlHintLabel(body_html)
        body_layout.addWidget(self._label)
        layout.addWidget(self._body)

        self._body.setVisible(expanded)
        self._sync_header_text()

    def is_expanded(self) -> bool:
        return self._header.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        self._header.setChecked(expanded)
        self._body.setVisible(expanded)
        self._sync_header_text()

    def _sync_header_text(self) -> None:
        icon = "chevron-down" if self._header.isChecked() else "chevron-right"
        self._header.setIcon(
            fa_icon(
                icon,
                size=12,
                color_key=current_icon_fg(),
                text_gap=BUTTON_ICON_TEXT_GAP,
            )
        )
        self._header.setText(self._title)

    def _on_header_clicked(self) -> None:
        expanded = self._header.isChecked()
        self._body.setVisible(expanded)
        self._sync_header_text()
        if expanded:
            self._label._apply_wrapped_height()
            self._body.updateGeometry()
            self.updateGeometry()
        self.toggled.emit(expanded)


class Accordion(QWidget):
    """Vertically stacked collapsible sections (one open at a time by default)."""

    def __init__(
        self,
        *,
        exclusive: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("accordion")
        self._exclusive = exclusive
        self._sections: list[AccordionSection] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

    def add_section(
        self,
        title: str,
        body_html: str,
        *,
        expanded: bool = False,
    ) -> AccordionSection:
        section = AccordionSection(title, body_html, expanded=expanded, parent=self)
        section.toggled.connect(
            lambda open_, s=section: self._on_section_toggled(s, open_)
        )
        self._sections.append(section)
        self._layout.addWidget(section)
        if expanded and self._exclusive:
            self._collapse_others(section)
        return section

    def _on_section_toggled(self, section: AccordionSection, open_: bool) -> None:
        if open_ and self._exclusive:
            self._collapse_others(section)

    def _collapse_others(self, keep: AccordionSection) -> None:
        for section in self._sections:
            if section is not keep and section.is_expanded():
                section.set_expanded(False)


class SettingsSectionNavigator:
    """Sidebar list + stacked pages. Parent lays out sidebar | scroll(content)."""

    _SIDEBAR_WIDTH = 176

    def __init__(self) -> None:
        self.sidebar = QFrame()
        self.sidebar.setObjectName("settingsNavSidebar")
        self.sidebar.setFixedWidth(self._SIDEBAR_WIDTH)
        self.sidebar.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        nav_title = QLabel("Sections")
        nav_title.setObjectName("settingsNavTitle")
        sidebar_layout.addWidget(nav_title)

        self._nav_scroll = QScrollArea()
        self._nav_scroll.setObjectName("settingsNavScroll")
        self._nav_scroll.setWidgetResizable(True)
        self._nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._nav_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        configure_scroll_area(self._nav_scroll, page_step=72)

        nav_body = QWidget()
        nav_body.setObjectName("settingsNavList")
        self._nav_layout = QVBoxLayout(nav_body)
        self._nav_layout.setContentsMargins(8, 6, 8, 8)
        self._nav_layout.setSpacing(4)
        self._nav_layout.addStretch(1)

        self._nav_scroll.setWidget(nav_body)
        sidebar_layout.addWidget(self._nav_scroll, stretch=1)

        self._button_group = QButtonGroup(self.sidebar)
        self._button_group.setExclusive(True)
        self._button_group.idClicked.connect(self._on_section_selected)

        self.stack = QStackedWidget()
        self.stack.setObjectName("settingsSectionStack")
        self.stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def add_section(self, title: str, page: QWidget) -> int:
        index = self.stack.addWidget(page)

        button = QPushButton(title)
        button.setObjectName("settingsNavItem")
        icon_name = settings_section_icon(title)
        if icon_name:
            button.setIcon(
                fa_icon(
                    icon_name,
                    size=14,
                    color_key=current_icon_fg(),
                    text_gap=BUTTON_ICON_TEXT_GAP,
                )
            )
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button_group.addButton(button, index)
        insert_at = self._nav_layout.count() - 1
        self._nav_layout.insertWidget(insert_at, button)

        if index == 0:
            button.setChecked(True)
            self.stack.setCurrentIndex(0)

        return index

    def _on_section_selected(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def set_current_index(self, index: int) -> None:
        if index < 0 or index >= self.stack.count():
            return
        self.stack.setCurrentIndex(index)
        button = self._button_group.button(index)
        if button is not None:
            button.setChecked(True)

    def index_of_page(self, page: QWidget) -> int:
        return self.stack.indexOf(page)

    def refresh_icons(self) -> None:
        icon_color = current_icon_fg()
        for button in self._button_group.buttons():
            icon_name = settings_section_icon(button.text())
            if icon_name:
                button.setIcon(
                    fa_icon(
                        icon_name,
                        size=14,
                        color_key=icon_color,
                        text_gap=BUTTON_ICON_TEXT_GAP,
                    )
                )
