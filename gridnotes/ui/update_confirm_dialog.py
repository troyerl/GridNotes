"""Confirm an update with readable release notes."""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def format_release_notes_plain(notes: str | None, *, max_lines: int = 24) -> str:
    if not notes or not notes.strip():
        return "This update includes bug fixes and improvements."

    lines: list[str] = []
    for raw in notes.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            line = re.sub(r"^#+\s*", "", line)
            if line:
                lines.append(line)
            continue
        if line.startswith(("- ", "* ")):
            lines.append(f"• {line[2:].strip()}")
        else:
            lines.append(line)
        if len(lines) >= max_lines:
            lines.append("…")
            break
    return "\n".join(lines) if lines else "This update includes bug fixes and improvements."


class UpdateConfirmDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        version: str,
        release_notes: str | None,
        portable: bool,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Update available")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(f"Install GridNotes {version.lstrip('v')}?")
        title.setObjectName("updateProgressTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        summary = QLabel(
            "GridNotes will download the update, close briefly, and reopen. "
            "Your notes and settings stay on this computer."
            if portable
            else "GridNotes will install the latest version and restart. "
            "Your notes and settings stay on this computer."
        )
        summary.setObjectName("sectionHint")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        whats_new = QLabel("What's new")
        whats_new.setObjectName("statInlineLabel")
        layout.addWidget(whats_new)

        notes_label = QLabel(format_release_notes_plain(release_notes))
        notes_label.setWordWrap(True)
        notes_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumHeight(220)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.addWidget(notes_label)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        buttons.button(QDialogButtonBox.StandardButton.Yes).setText("Update now")
        buttons.button(QDialogButtonBox.StandardButton.No).setText("Not now")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
