"""Accessibility helpers for Qt widgets (names, descriptions, row labels)."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


def set_accessible(
    widget: QWidget,
    name: str,
    description: str | None = None,
) -> None:
    """Set the accessible name (and optional description) for assistive technologies."""
    widget.setAccessibleName(name)
    if description:
        widget.setAccessibleDescription(description)


def driver_mark_label(pref: int | None, risky: bool) -> str | None:
    """Non-color text for liked / disliked / risky row state (Mark column)."""
    parts: list[str] = []
    if pref == 1:
        parts.append("Liked")
    elif pref == -1:
        parts.append("Disliked")
    if risky:
        parts.append("Risk")
    return ", ".join(parts) if parts else None
