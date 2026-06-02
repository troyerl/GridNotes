"""Background workers for iRacing Data API fetch and import."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from ..data.data_retention import DEFAULT_RETENTION, SETTING_KEY, purge_expired_race_results
from ..data.db import connect_db, get_db_path, get_setting
from .iracing_data_api import (
    event_result_has_race_data,
    fetch_event_result_json,
    format_api_error,
    package_available,
    package_unavailable_reason,
    test_connection_with_token,
)
from .iracing_import import import_race_entries, parse_races_from_json

logger = logging.getLogger(__name__)

# iRacing may need time to publish results after a session ends
FETCH_RETRY_DELAYS_SEC = (3, 10, 30, 60, 120)


@dataclass
class SubsessionFetchResult:
    subsession_id: int
    races_imported: int = 0
    results_imported: int = 0
    results_updated: int = 0
    results_skipped: int = 0
    retention_deleted: int = 0


class ApiConnectionTestWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, *, access_token: str, parent=None) -> None:
        super().__init__(parent)
        self._access_token = access_token

    def run(self) -> None:
        logger.info("iRacing Data API connection test started")
        try:
            ok, message = test_connection_with_token(self._access_token)
            self.finished.emit(ok, message)
        except Exception as exc:
            logger.exception("API connection test failed")
            self.finished.emit(False, str(exc))


class SubsessionFetchWorker(QThread):
    """Fetch subsession results from the Data API and import into the local DB."""

    finished = pyqtSignal(object)  # SubsessionFetchResult
    failed = pyqtSignal(int, str)  # subsession_id, message
    status = pyqtSignal(str)

    def __init__(self, subsession_id: int, parent=None) -> None:
        super().__init__(parent)
        self._subsession_id = subsession_id

    def run(self) -> None:
        sub_id = self._subsession_id
        if not package_available():
            reason = package_unavailable_reason()
            logger.warning(
                "Auto-fetch for subsession %s skipped: %s",
                sub_id,
                reason,
            )
            self.failed.emit(sub_id, reason)
            return

        last_error = "Results not available yet."
        event_result: dict | None = None

        for attempt, delay in enumerate(FETCH_RETRY_DELAYS_SEC):
            if attempt:
                self.status.emit(
                    f"Waiting for session #{sub_id} results ({delay}s)…"
                )
                self.msleep(delay * 1000)
            else:
                self.status.emit(f"Fetching results for session #{sub_id}…")

            try:
                event_result = fetch_event_result_json(sub_id)
                if event_result_has_race_data(event_result):
                    break
                last_error = "Race results not published yet."
                event_result = None
            except Exception as exc:
                logger.warning(
                    "Fetch attempt %s for subsession %s failed: %s",
                    attempt + 1,
                    sub_id,
                    exc,
                )
                last_error = format_api_error(exc)
                event_result = None

        if event_result is None:
            logger.warning(
                "Auto-fetch for subsession %s failed after retries: %s",
                sub_id,
                last_error,
            )
            self.failed.emit(sub_id, last_error)
            return

        conn = None
        try:
            conn = connect_db(get_db_path())
            cursor = conn.cursor()
            conn.execute("BEGIN")

            races, series_name, race_timestamp = parse_races_from_json(event_result)
            license_text_fallback = None
            data = event_result.get("data")
            if isinstance(data, dict):
                cat = data.get("license_category")
                license_text_fallback = str(cat) if cat else None

            races_imported, results_imported, results_updated, results_skipped = (
                import_race_entries(
                    cursor,
                    races,
                    series_name,
                    race_timestamp,
                    license_text_fallback,
                )
            )
            conn.commit()

            retention = get_setting(SETTING_KEY, DEFAULT_RETENTION) or DEFAULT_RETENTION
            retention_deleted = purge_expired_race_results(conn, retention)
            if retention_deleted:
                conn.commit()

            self.finished.emit(
                SubsessionFetchResult(
                    subsession_id=sub_id,
                    races_imported=races_imported,
                    results_imported=results_imported,
                    results_updated=results_updated,
                    results_skipped=results_skipped,
                    retention_deleted=retention_deleted,
                )
            )
        except Exception as exc:
            logger.exception("Subsession import failed for %s", sub_id)
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            self.failed.emit(sub_id, format_api_error(exc))
        finally:
            if conn is not None:
                conn.close()
