"""Reusable Qt widgets."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
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

from .theme import configure_scroll_area


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
        if html:
            self.setText(html)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        if width <= 0:
            return super().sizeHint().height()
        doc = self.fontMetrics()
        bounds = doc.boundingRect(
            0,
            0,
            width,
            10_000,
            int(Qt.TextFlag.TextWordWrap),
            self.text(),
        )
        return bounds.height() + 8


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
        arrow = "▼" if self._header.isChecked() else "▸"
        self._header.setText(f"{arrow}  {self._title}")

    def _on_header_clicked(self) -> None:
        expanded = self._header.isChecked()
        self._body.setVisible(expanded)
        self._sync_header_text()
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
