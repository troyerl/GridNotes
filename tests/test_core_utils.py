"""Tests for gridnotes.core.utils."""

from gridnotes.core.utils import (
    display_val,
    format_file_size,
    normalize_1_based,
    sqlite_row_to_int,
)


def test_sqlite_row_to_int_valid():
    assert sqlite_row_to_int(42) == 42
    assert sqlite_row_to_int("7") == 7


def test_sqlite_row_to_int_invalid():
    assert sqlite_row_to_int(None) is None
    assert sqlite_row_to_int("abc") is None


def test_display_val():
    assert display_val(None) == "—"
    assert display_val("none") == "—"
    assert display_val("  Alice  ") == "Alice"
    assert display_val(42) == "42"


def test_format_file_size():
    assert format_file_size(512) == "512 B"
    assert "KB" in format_file_size(2048)
    assert "MB" in format_file_size(2 * 1024 * 1024)


def test_normalize_1_based():
    assert normalize_1_based(0) == 1
    assert normalize_1_based(5) == 6
    assert normalize_1_based(-1) is None
    assert normalize_1_based("x") is None
