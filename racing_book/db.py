import os
import sqlite3
import sys
from pathlib import Path

APP_NAME = "GridNotes"
LEGACY_APP_NAME = "RacingBook"  # pre-rename data folder


def _install_data_dir(name: str) -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / name
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / name
    return Path.home() / ".local" / "share" / name


def _get_data_dir() -> Path:
    """Return a stable writable folder for app data (dev vs bundled)."""
    if getattr(sys, "frozen", False):
        base = _install_data_dir(APP_NAME)
        legacy = _install_data_dir(LEGACY_APP_NAME)
        if not base.exists() and legacy.exists():
            import shutil

            shutil.copytree(legacy, base)
    else:
        base = Path.cwd()

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_data_dir_path() -> Path:
    return _get_data_dir()


def get_db_path() -> str:
    return str(_get_data_dir() / "driver_history.db")


DB_NAME = get_db_path()


def connect_db(db_name: str = DB_NAME) -> sqlite3.Connection:
    """Open SQLite with a small page cache to keep memory use low."""
    conn = sqlite3.connect(db_name)
    conn.execute("PRAGMA cache_size = -512")  # 512 KiB page cache
    conn.execute("PRAGMA mmap_size = 0")
    conn.execute("PRAGMA temp_store = FILE")
    return conn


def _existing_columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _ensure_column(cursor: sqlite3.Cursor, table: str, column: str, col_type: str) -> None:
    cols = _existing_columns(cursor, table)
    if column in cols:
        return
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def _migrate_schema(cursor: sqlite3.Cursor) -> None:
    # "last seen" fields for quick scouting context
    _ensure_column(cursor, "drivers", "last_irating", "INTEGER")
    _ensure_column(cursor, "drivers", "last_safety", "REAL")  # SR like 3.67
    _ensure_column(cursor, "drivers", "last_license", "TEXT")  # e.g. "A 3.67"
    _ensure_column(cursor, "drivers", "last_series", "TEXT")  # series / event name
    _ensure_column(cursor, "drivers", "last_starting_pos", "INTEGER")
    _ensure_column(cursor, "drivers", "last_seen_at", "TEXT")  # ISO timestamp (end_time/start_time)
    _ensure_column(cursor, "drivers", "race_preference", "INTEGER")  # 1=liked, -1=disliked, NULL=unset

    # per-race fields
    _ensure_column(cursor, "race_results", "starting_position", "INTEGER")
    _ensure_column(cursor, "race_results", "reason_out", "TEXT")
    _ensure_column(cursor, "race_results", "reason_out_id", "INTEGER")


def init_db(db_name: str = DB_NAME) -> None:
    conn = connect_db(db_name)
    cursor = conn.cursor()

    # Track core driver identity and permanent notes
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS drivers (
            cust_id INTEGER PRIMARY KEY,
            driver_name TEXT,
            notes TEXT DEFAULT ''
        )
        """
    )

    # Track historical race performance records per driver
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS race_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cust_id INTEGER,
            subsession_id INTEGER,
            finish_position INTEGER,
            incidents INTEGER,
            irating_change INTEGER,
            license_class TEXT,
            FOREIGN KEY(cust_id) REFERENCES drivers(cust_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    _migrate_schema(cursor)
    conn.commit()
    conn.close()


def get_setting(key: str, default: str | None = None, db_name: str = DB_NAME) -> str | None:
    conn = connect_db(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else default


def set_setting(key: str, value: str | None, db_name: str = DB_NAME) -> None:
    conn = connect_db(db_name)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()

