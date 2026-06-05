"""Tests for update staging folder helpers."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from gridnotes.installer import update_paths


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "gridnotes.installer.update_paths.get_data_dir_path",
        lambda: tmp_path,
    )
    return tmp_path


def test_update_workspace_dir_creates_under_updates(data_dir):
    path = update_paths.update_workspace_dir(
        version="1.0.51",
        pid=1234,
        kind="frozen",
    )
    assert path.is_dir()
    assert path.parent == data_dir / "updates"
    assert path.name.startswith("frozen-1.0.51-1234-")


def test_prune_removes_old_workspaces(data_dir):
    updates = data_dir / "updates"
    old = updates / "frozen-1.0.38-1-1000"
    recent = updates / "frozen-1.0.50-2-2000"
    old.mkdir(parents=True)
    recent.mkdir(parents=True)
    (old / "release.zip").write_bytes(b"old")
    (recent / "release.zip").write_bytes(b"new")

    old_time = time.time() - 3600
    recent_time = time.time() - 60
    for path, mtime in ((old, old_time), (recent, recent_time)):
        Path(path / "release.zip").touch()
        import os

        os.utime(path, (mtime, mtime))

    removed = update_paths.prune_old_update_workspaces(keep_recent_seconds=600)
    assert removed == 1
    assert not old.exists()
    assert recent.exists()


def test_prune_skips_missing_root(data_dir):
    assert update_paths.prune_old_update_workspaces() == 0


def test_remove_update_workspace_deletes_directory(data_dir):
    target = data_dir / "updates" / "portable-1.0.40-99"
    target.mkdir(parents=True)
    (target / "staging").mkdir()
    assert update_paths.remove_update_workspace(target) is True
    assert not target.exists()
