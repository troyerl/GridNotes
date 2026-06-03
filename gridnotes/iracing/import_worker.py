"""Background worker for importing race JSON files without blocking the UI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from PyQt6.QtCore import QThread, pyqtSignal

from ..data.data_retention import DEFAULT_RETENTION, SETTING_KEY, purge_expired_race_results
from ..data.db import connect_db, get_db_path, get_setting
from .iracing_import import import_race_entries, parse_races_from_json

logger = logging.getLogger(__name__)


@dataclass
class ImportJobResult:
    total_files: int = 0
    total_races_imported: int = 0
    total_results_imported: int = 0
    total_results_updated: int = 0
    total_results_skipped: int = 0
    retention_deleted: int = 0
    affected_cust_ids: set[int] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)


class ImportWorker(QThread):
    """Parse and import race JSON on a worker thread."""

    finished = pyqtSignal(object)  # ImportJobResult
    failed = pyqtSignal(str)

    def __init__(self, file_paths: list[str], parent=None) -> None:
        super().__init__(parent)
        self._file_paths = [p for p in file_paths if p]

    def run(self) -> None:
        if not self._file_paths:
            self.finished.emit(ImportJobResult())
            return

        result = ImportJobResult()
        conn = None
        try:
            conn = connect_db(get_db_path())
            cursor = conn.cursor()
            conn.execute("BEGIN")

            for file_path in self._file_paths:
                result.total_files += 1
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    races, series_name, race_timestamp = parse_races_from_json(data)
                    license_text_fallback = None
                    if isinstance(data, dict) and isinstance(data.get("data"), dict):
                        cat = data["data"].get("license_category")
                        license_text_fallback = str(cat) if cat else None

                    races_imported, results_imported, results_updated, results_skipped, affected = (
                        import_race_entries(
                            cursor,
                            races,
                            series_name,
                            race_timestamp,
                            license_text_fallback,
                        )
                    )

                    result.total_races_imported += races_imported
                    result.total_results_imported += results_imported
                    result.total_results_updated += results_updated
                    result.total_results_skipped += results_skipped
                    result.affected_cust_ids.update(affected)

                    if results_imported == 0 and results_updated == 0 and results_skipped == 0:
                        msg = f"{file_path}: no race results found/imported"
                        result.errors.append(msg)
                        logger.warning("Import: %s", msg)

                except Exception as exc:
                    logger.exception("Import failed for %s", file_path)
                    msg = f"{file_path}: {exc}"
                    result.errors.append(msg)
                    logger.warning("Import: %s", msg)

            conn.commit()

            retention = get_setting(SETTING_KEY, DEFAULT_RETENTION) or DEFAULT_RETENTION
            result.retention_deleted = purge_expired_race_results(conn, retention)
            if result.retention_deleted:
                conn.commit()

            logger.info(
                "Import finished: files=%s races=%s new=%s updated=%s skipped=%s errors=%s",
                result.total_files,
                result.total_races_imported,
                result.total_results_imported,
                result.total_results_updated,
                result.total_results_skipped,
                len(result.errors),
            )
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("Import worker failed")
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            self.failed.emit(str(exc))
        finally:
            if conn is not None:
                conn.close()
