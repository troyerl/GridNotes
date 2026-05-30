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
    _ensure_column(cursor, "drivers", "tags", "TEXT")  # comma-separated tags

    # per-race fields
    _ensure_column(cursor, "race_results", "starting_position", "INTEGER")
    _ensure_column(cursor, "race_results", "reason_out", "TEXT")
    _ensure_column(cursor, "race_results", "reason_out_id", "INTEGER")
    _ensure_column(cursor, "race_results", "series_name", "TEXT")
    _ensure_column(cursor, "race_results", "race_at", "TEXT")  # ISO race end/start time

    _backfill_race_at(cursor)
    # Not perfect, but better than leaving historical data unfilterable.
    try:
        cursor.execute(
            """
            UPDATE race_results
            SET series_name = (
                SELECT d.last_series
                FROM drivers d
                WHERE d.cust_id = race_results.cust_id
            )
            WHERE TRIM(COALESCE(series_name, '')) = ''
              AND EXISTS (
                  SELECT 1
                  FROM drivers d
                  WHERE d.cust_id = race_results.cust_id
                    AND TRIM(COALESCE(d.last_series, '')) != ''
              )
            """
        )
    except Exception:
        pass

    # Backfill older imports where reason_out_id wasn't set but reason_out text exists.
    # This avoids expensive LOWER/TRIM logic during aggregation queries.
    try:
        cursor.execute(
            """
            UPDATE race_results
            SET reason_out_id =
                CASE
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'disconnected' THEN 1
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'ejected' THEN 2
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'quit' THEN 3
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'disqualified' THEN 4
                    ELSE reason_out_id
                END
            WHERE reason_out_id IS NULL
              AND TRIM(COALESCE(reason_out, '')) != ''
            """
        )
    except Exception:
        pass

    _ensure_subsession_dedup_index(cursor)
    _ensure_perf_indexes(cursor)


def _backfill_race_at(cursor: sqlite3.Cursor) -> None:
    """Best-effort timestamp for older rows (uses driver last_seen_at)."""
    try:
        cursor.execute(
            """
            UPDATE race_results
            SET race_at = (
                SELECT d.last_seen_at
                FROM drivers d
                WHERE d.cust_id = race_results.cust_id
            )
            WHERE race_at IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM drivers d
                  WHERE d.cust_id = race_results.cust_id
                    AND d.last_seen_at IS NOT NULL
                    AND TRIM(d.last_seen_at) != ''
              )
            """
        )
    except Exception:
        pass


def _dedupe_race_results_by_subsession(cursor: sqlite3.Cursor) -> None:
    """Keep one row per driver per subsession before adding the unique index."""
    cursor.execute(
        """
        DELETE FROM race_results
        WHERE subsession_id IS NOT NULL
          AND subsession_id != 0
          AND id NOT IN (
              SELECT MIN(id)
              FROM race_results
              WHERE subsession_id IS NOT NULL
                AND subsession_id != 0
              GROUP BY cust_id, subsession_id
          )
        """
    )


def _ensure_subsession_dedup_index(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_race_results_cust_subsession'"
    )
    if cursor.fetchone():
        return
    _dedupe_race_results_by_subsession(cursor)
    cursor.execute(
        """
        CREATE UNIQUE INDEX idx_race_results_cust_subsession
        ON race_results (cust_id, subsession_id)
        WHERE subsession_id != 0
        """
    )


def _ensure_perf_indexes(cursor: sqlite3.Cursor) -> None:
    # Speed up stats filtering + aggregation queries.
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_results_cust_id ON race_results (cust_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_results_series_name ON race_results (series_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_results_license_class ON race_results (license_class)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_results_reason_out_id ON race_results (reason_out_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_results_race_at ON race_results (race_at)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_race_results_cust_reason ON race_results (cust_id, reason_out_id)"
    )
    # Expression index for the license prefix filter (R/D/C/B/A/P)
    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_race_results_license_prefix "
            "ON race_results (UPPER(SUBSTR(COALESCE(license_class, ''), 1, 1)))"
        )
    except Exception:
        pass


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

