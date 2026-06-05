"""Tests for gridnotes.ui.update_confirm_dialog."""

import pytest

pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)

from gridnotes.ui.update_confirm_dialog import format_release_notes_plain


def test_format_release_notes_empty():
    assert "improvements" in format_release_notes_plain(None).lower()


def test_format_release_notes_bullets():
    notes = "## v1.0.44\n\n- Fixed bug\n- Added feature"
    plain = format_release_notes_plain(notes)
    assert "• Fixed bug" in plain
    assert "v1.0.44" in plain


def test_format_release_notes_truncates():
    lines = "\n".join(f"- Item {i}" for i in range(50))
    plain = format_release_notes_plain(lines, max_lines=5)
    assert "…" in plain
