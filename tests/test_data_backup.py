"""Tests for gridnotes.data.backup."""

from pathlib import Path

from gridnotes.data.db import connect_db
from gridnotes.data.backup import export_database_backup, import_database_backup


def test_export_and_import_backup(file_db, tmp_path):
    db_path, conn = file_db
    conn.execute(
        "INSERT INTO drivers (cust_id, driver_name, notes) VALUES (1, 'Backup Test', 'note')"
    )
    conn.commit()

    backup_path = tmp_path / "backup.db"
    ok, message = export_database_backup(backup_path, connection=conn)
    assert ok is True
    assert backup_path.is_file()

    conn.execute("DELETE FROM drivers")
    conn.commit()

    ok_restore, _ = import_database_backup(backup_path, connection=conn)
    assert ok_restore is True

    conn2 = connect_db(db_path)
    row = conn2.execute(
        "SELECT driver_name FROM drivers WHERE cust_id = 1"
    ).fetchone()
    conn2.close()
    assert row is not None
    assert row[0] == "Backup Test"
