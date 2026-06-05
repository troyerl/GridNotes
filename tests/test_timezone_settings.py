"""Tests for display timezone helpers."""

from __future__ import annotations

import os
import sys

import pytest

from gridnotes.core import timezone_settings


@pytest.fixture(autouse=True)
def reset_tzpath_flag():
    timezone_settings._tzpath_configured = False
    previous = os.environ.get("TZPATH")
    yield
    timezone_settings._tzpath_configured = False
    if previous is None:
        os.environ.pop("TZPATH", None)
    else:
        os.environ["TZPATH"] = previous


def test_configure_tzpath_for_frozen_is_idempotent(tmp_path, monkeypatch):
    tz_root = tmp_path / "zoneinfo"
    tz_root.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv("TZPATH", raising=False)

    timezone_settings.configure_tzpath_for_frozen()
    first = os.environ.get("TZPATH", "")

    timezone_settings.configure_tzpath_for_frozen()
    second = os.environ.get("TZPATH", "")

    assert first
    assert first == second
    assert first.count(str(tz_root)) == 1


def test_configure_tzpath_skips_when_not_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.delenv("TZPATH", raising=False)

    timezone_settings.configure_tzpath_for_frozen()

    assert "TZPATH" not in os.environ
