"""Private folders for in-app updates (never the user's Downloads directory)."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from ..data.db import get_data_dir_path

logger = logging.getLogger(__name__)

UPDATE_WORK_SUBDIR = "updates"
UPDATE_LOG_NAME = "gridnotes-update.log"


def update_log_path() -> Path:
    return get_data_dir_path() / UPDATE_LOG_NAME


def update_workspace_dir(*, version: str, pid: int, kind: str) -> Path:
    """
    Staging directory for an in-flight update.

    Lives under the GridNotes data folder (e.g. AppData), not Downloads or Desktop.
    """
    safe_version = "".join(c if c.isalnum() or c in ".-" else "_" for c in version)
    path = (
        get_data_dir_path()
        / UPDATE_WORK_SUBDIR
        / f"{kind}-{safe_version}-{pid}-{int(time.time())}"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def prune_old_update_workspaces(*, max_age_seconds: int = 48 * 3600) -> None:
    """Remove leftover update staging folders from interrupted runs."""
    root = get_data_dir_path() / UPDATE_WORK_SUBDIR
    if not root.is_dir():
        return
    cutoff = time.time() - max_age_seconds
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            if child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError as exc:
            logger.debug("Could not prune update workspace %s: %s", child, exc)
