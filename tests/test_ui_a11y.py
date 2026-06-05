"""Tests for gridnotes.ui.a11y and related UI string helpers."""

import pytest

pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)

from gridnotes.ui.a11y import driver_mark_label


def test_driver_mark_label_liked():
    assert driver_mark_label(1, False) == "Liked"


def test_driver_mark_label_disliked_risky():
    assert driver_mark_label(-1, True) == "Disliked, Risk"


def test_driver_mark_label_none():
    assert driver_mark_label(None, False) is None
