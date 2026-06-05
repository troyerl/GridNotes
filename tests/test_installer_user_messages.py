"""Tests for gridnotes.installer.user_messages."""

from gridnotes.installer.user_messages import (
    friendly_install_step,
    friendly_python_status,
    friendly_update_progress,
)


def test_friendly_install_step_known():
    assert friendly_install_step("Finished") == "All set!"


def test_friendly_install_step_unknown_passthrough():
    assert friendly_install_step("Custom step") == "Custom step"


def test_friendly_python_status_ok():
    msg = friendly_python_status(True, "ok")
    assert "ready" in msg.lower()


def test_friendly_python_status_missing():
    msg = friendly_python_status(False, "Could not determine Python version")
    assert "Python" in msg


def test_friendly_update_progress_passthrough():
    assert friendly_update_progress("Updating…") == "Updating…"
