"""Reusable Qt widgets."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget


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
