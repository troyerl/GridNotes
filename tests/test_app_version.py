"""Tests for gridnotes.app.app_version."""

from pathlib import Path

from gridnotes.app import app_version


def test_parse_version():
    assert app_version.parse_version("1.0.44") == (1, 0, 44)
    assert app_version.parse_version("v2.10.3-beta") == (10, 3)
    assert app_version.parse_version("") == (0,)


def test_is_newer_version():
    assert app_version.is_newer_version("1.0.44", "1.0.43")
    assert not app_version.is_newer_version("1.0.43", "1.0.44")
    assert not app_version.is_newer_version("1.0.43", "1.0.43")


def test_reconcile_installed_version_uses_newest(tmp_path):
    install = tmp_path / "GridNotes"
    install.mkdir()
    (install / app_version.INSTALLED_VERSION_FILENAME).write_text("1.0.40\n")
    best = app_version.reconcile_installed_version(install)
    assert best == app_version.__version__
    marker = (install / app_version.INSTALLED_VERSION_FILENAME).read_text().strip()
    assert marker == app_version.__version__


def test_write_installed_version(tmp_path):
    install = tmp_path / "app"
    install.mkdir()
    app_version.write_installed_version(install, "v1.2.3")
    assert (install / app_version.INSTALLED_VERSION_FILENAME).read_text().strip() == "1.2.3"
