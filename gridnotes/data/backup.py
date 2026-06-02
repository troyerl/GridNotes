"""Export and restore the GridNotes SQLite database."""

from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .db import delete_sqlite_sidecar_files, get_db_path

logger = logging.getLogger(__name__)


def export_database_backup(
    dest: Path,
    *,
    connection: sqlite3.Connection | None = None,
) -> tuple[bool, str]:
    """Copy the live database to *dest* (safe while the app is running)."""
    dest = dest.expanduser().resolve()
    src = Path(get_db_path())
    if not src.is_file():
        return False, "No database found yet — nothing to back up."

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if connection is not None:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.commit()
        shutil.copy2(src, dest)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{src}{suffix}")
            if sidecar.is_file():
                shutil.copy2(sidecar, Path(f"{dest}{suffix}"))
    except OSError as exc:
        logger.exception("Database export failed")
        return False, f"Could not save backup:\n{exc}"

    return True, f"Backup saved to:\n{dest}"


def import_database_backup(
    src: Path,
    *,
    connection: sqlite3.Connection | None = None,
) -> tuple[bool, str]:
    """
    Replace the current database with *src*.

    *connection* must be closed by the caller before import, or passed here to
    checkpoint and close.
    """
    src = src.expanduser().resolve()
    if not src.is_file():
        return False, "That backup file does not exist."

    dest = Path(get_db_path())
    try:
        if connection is not None:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.commit()
            connection.close()

        if dest.is_file():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            backup_current = dest.with_name(f"driver_history.db.before-restore-{stamp}")
            shutil.copy2(dest, backup_current)
            delete_sqlite_sidecar_files(dest)

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        delete_sqlite_sidecar_files(dest)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{src}{suffix}")
            if sidecar.is_file():
                shutil.copy2(sidecar, Path(f"{dest}{suffix}"))
    except OSError as exc:
        logger.exception("Database import failed")
        return False, f"Could not restore backup:\n{exc}"

    return True, "Backup restored. Restart GridNotes if anything looks wrong."
