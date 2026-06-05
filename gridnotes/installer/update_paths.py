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
# Keep very recent folders in case an update batch is still running.
ACTIVE_UPDATE_GRACE_SECONDS = 20 * 60


def update_log_path() -> Path:
    return get_data_dir_path() / UPDATE_LOG_NAME


def update_workspace_root() -> Path:
    return get_data_dir_path() / UPDATE_WORK_SUBDIR


def update_workspace_dir(*, version: str, pid: int, kind: str) -> Path:
    """
    Staging directory for an in-flight update.

    Lives under the GridNotes data folder (e.g. AppData), not Downloads or Desktop.
    """
    safe_version = "".join(c if c.isalnum() or c in ".-" else "_" for c in version)
    path = (
        update_workspace_root()
        / f"{kind}-{safe_version}-{pid}-{int(time.time())}"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def remove_update_workspace(path: Path) -> bool:
    """Delete a single update staging folder (best effort)."""
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return True
        if path.is_file():
            path.unlink(missing_ok=True)
            return True
    except OSError as exc:
        logger.debug("Could not remove update workspace %s: %s", path, exc)
    return False


def prune_old_update_workspaces(
    *,
    keep_recent_seconds: int = ACTIVE_UPDATE_GRACE_SECONDS,
) -> int:
    """
    Remove leftover update staging folders and files from interrupted or finished updates.

    Returns the number of entries removed.
    """
    root = update_workspace_root()
    if not root.is_dir():
        return 0
    cutoff = time.time() - max(0, keep_recent_seconds)
    removed = 0
    for child in list(root.iterdir()):
        try:
            if child.stat().st_mtime >= cutoff:
                continue
        except OSError as exc:
            logger.debug("Could not stat update workspace %s: %s", child, exc)
            continue
        if remove_update_workspace(child):
            removed += 1
    if removed:
        logger.info("Removed %d old update staging folder(s) from %s", removed, root)
    return removed
