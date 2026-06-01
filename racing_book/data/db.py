import sqlite3
import sys
from pathlib import Path

from .user_paths import APP_NAME, LEGACY_APP_NAME, data_dir_candidates, resolve_writable_data_dir


def _local_install_data_candidates() -> list[Path]:
    """Folders that may hold data from older installs (database next to main.py)."""
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        candidates.append(resolved)

    add(Path.cwd())
    if sys.argv:
        add(Path(sys.argv[0]).resolve().parent)
    pkg_root = Path(__file__).resolve().parent.parent.parent
    add(pkg_root)
    return candidates


def _migrate_file_if_missing(*, source: Path, dest: Path) -> None:
    if not source.is_file() or dest.exists():
        return
    import shutil

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def _get_data_dir() -> Path:
    """Return a stable per-user folder for database, settings, and logs."""
    base = resolve_writable_data_dir()

    for folder in data_dir_candidates(include_legacy=True):
        if folder.resolve() == base.resolve():
            continue
        legacy_db = folder / "driver_history.db"
        if legacy_db.is_file():
            _migrate_file_if_missing(source=legacy_db, dest=base / "driver_history.db")
        for log_name in ("gridnotes.log", "racingbook.log", "launch-error.log"):
            _migrate_file_if_missing(source=folder / log_name, dest=base / log_name)

    if not getattr(sys, "frozen", False):
        app_db = base / "driver_history.db"
        for folder in _local_install_data_candidates():
            local_db = folder / "driver_history.db"
            if local_db.is_file():
                _migrate_file_if_missing(source=local_db, dest=app_db)
                break

    return base


def get_data_dir_path() -> Path:
    return _get_data_dir()


def get_launch_log_path() -> Path:
    """User-writable launch diagnostics (install folder may be read-only)."""
    return get_data_dir_path() / "launch-error.log"


def get_db_path() -> str:
    return str(_get_data_dir() / "driver_history.db")


def get_db_file_size() -> int | None:
    path = _get_data_dir() / "driver_history.db"
    try:
        return path.stat().st_size
    except OSError:
        return None


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
    _sync_driver_last_seen_from_results(cursor)

    # Backfill older imports (pre-series_name) with best available info.
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


def _sync_driver_last_seen_from_results(cursor: sqlite3.Cursor) -> None:
    """Repair last_seen_at from race result timestamps when missing or stale."""
    try:
        cursor.execute(
            """
            UPDATE drivers
            SET last_seen_at = (
                SELECT MAX(r.race_at)
                FROM race_results r
                WHERE r.cust_id = drivers.cust_id
                  AND r.race_at IS NOT NULL
                  AND TRIM(r.race_at) != ''
            )
            WHERE EXISTS (
                SELECT 1
                FROM race_results r
                WHERE r.cust_id = drivers.cust_id
                  AND r.race_at IS NOT NULL
                  AND TRIM(r.race_at) != ''
            )
            AND (
                last_seen_at IS NULL
                OR TRIM(COALESCE(last_seen_at, '')) = ''
                OR last_seen_at < (
                    SELECT MAX(r.race_at)
                    FROM race_results r
                    WHERE r.cust_id = drivers.cust_id
                      AND r.race_at IS NOT NULL
                      AND TRIM(r.race_at) != ''
                )
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

