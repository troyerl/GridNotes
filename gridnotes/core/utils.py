"""Shared helpers with no UI or database dependencies."""

from __future__ import annotations


def sqlite_row_to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def display_val(value) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text and text.lower() != "none" else "—"


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def normalize_1_based(pos) -> int | None:
    """iRacing event_result uses 0-based positions (0 == P1)."""
    if isinstance(pos, int) and pos >= 0:
        return pos + 1
    return None
