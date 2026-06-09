"""Pagination controls for large driver tables."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from .a11y import set_accessible
from .icons import set_button_fa_icon

DEFAULT_PAGE_SIZE = 50
PAGE_SIZE_OPTIONS = (25, 50, 100, 200)


class TablePaginationBar(QWidget):
    previous_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    page_size_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(8)

        self._summary = QLabel("")
        self._summary.setObjectName("sectionHint")
        layout.addWidget(self._summary)
        layout.addStretch()

        rows_label = QLabel("Rows per page")
        rows_label.setObjectName("statInlineLabel")
        layout.addWidget(rows_label)

        self._page_size = QComboBox()
        self._page_size.setObjectName("tablePageSize")
        for size in PAGE_SIZE_OPTIONS:
            self._page_size.addItem(str(size), size)
        self._page_size.setCurrentIndex(PAGE_SIZE_OPTIONS.index(DEFAULT_PAGE_SIZE))
        self._page_size.currentIndexChanged.connect(self._emit_page_size)
        layout.addWidget(self._page_size)

        self._page_label = QLabel("")
        self._page_label.setObjectName("sectionHint")
        layout.addWidget(self._page_label)

        self._btn_prev = QPushButton()
        set_button_fa_icon(self._btn_prev, "chevron-left", icon_only=True, icon_size=14)
        self._btn_prev.setToolTip("Previous page")
        set_accessible(self._btn_prev, "Previous page", "Go to the previous page of results.")
        self._btn_prev.clicked.connect(self.previous_clicked.emit)
        layout.addWidget(self._btn_prev)

        self._btn_next = QPushButton()
        set_button_fa_icon(self._btn_next, "chevron-right", icon_only=True, icon_size=14)
        self._btn_next.setToolTip("Next page")
        set_accessible(self._btn_next, "Next page", "Go to the next page of results.")
        self._btn_next.clicked.connect(self.next_clicked.emit)
        layout.addWidget(self._btn_next)

    def page_size(self) -> int:
        value = self._page_size.currentData()
        return int(value) if value is not None else DEFAULT_PAGE_SIZE

    def set_page_size(self, size: int) -> None:
        idx = self._page_size.findData(size)
        if idx >= 0:
            self._page_size.blockSignals(True)
            self._page_size.setCurrentIndex(idx)
            self._page_size.blockSignals(False)

    def update_state(
        self,
        *,
        page: int,
        page_count: int,
        total: int,
        start: int,
        end: int,
        item_label: str = "drivers",
    ) -> None:
        if total <= 0:
            self._summary.setText(f"No {item_label} match the current filters.")
            self._page_label.setText("")
        else:
            self._summary.setText(f"Showing {start}–{end} of {total} {item_label}")
            self._page_label.setText(f"Page {page + 1} of {page_count}")
        self._btn_prev.setEnabled(page > 0)
        self._btn_next.setEnabled(page < page_count - 1)

    def _emit_page_size(self, _index: int) -> None:
        self.page_size_changed.emit(self.page_size())
