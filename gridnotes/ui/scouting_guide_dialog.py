"""Scrollable scouting reference (Safety Index, form guide, marks)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .a11y import set_accessible
from .icons import set_button_fa_icon
from .scouting_legend import scouting_guide_document_html

_DIALOG_ATTR = "_gridnotes_scouting_guide_dialog"


class ScoutingGuideDialog(QDialog):
    """Non-modal reference for Safety Index, trends, and marks."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("scoutingGuideDialog")
        self.setWindowTitle("Scouting guide")
        self.setModal(False)
        self.resize(560, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        intro = QLabel(
            "How to read Safety Index scores, form arrows (↗ ↘ →), marks, and risk callouts."
        )
        intro.setObjectName("sectionHint")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._browser = QTextBrowser()
        self._browser.setObjectName("scoutingGuideBrowser")
        self._browser.setOpenExternalLinks(True)
        self._browser.setHtml(scouting_guide_document_html())
        layout.addWidget(self._browser, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        set_button_fa_icon(close_btn, "xmark", text="Close")
        close_btn.setObjectName("primaryBtn")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        set_accessible(self._browser, "Scouting guide reference", None)


def show_scouting_guide(parent: QWidget | None = None) -> ScoutingGuideDialog:
    """Show the guide dialog; re-raise an existing instance on the same window."""
    host = parent.window() if parent is not None else None
    existing = getattr(host, _DIALOG_ATTR, None) if host is not None else None
    if isinstance(existing, ScoutingGuideDialog) and existing.isVisible():
        existing.raise_()
        existing.activateWindow()
        return existing

    dialog = ScoutingGuideDialog(parent)
    if host is not None:
        setattr(host, _DIALOG_ATTR, dialog)

    def _clear_ref() -> None:
        if host is not None and getattr(host, _DIALOG_ATTR, None) is dialog:
            setattr(host, _DIALOG_ATTR, None)

    dialog.finished.connect(_clear_ref)
    dialog.show()
    return dialog
