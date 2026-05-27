import json
import logging
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .db import connect_db, get_setting, init_db, set_setting
from .iracing_worker import IRacingWorker
from .theme import (
    STATUS_CONNECTED,
    STATUS_OFFLINE,
    STATUS_WAITING,
    configure_scroll_area,
    configure_widget_scrollbars,
)

logger = logging.getLogger(__name__)

# iRacing reason_out_id (0 = finished on track; excluded from DNF stats)
REASON_OUT_RUNNING = 0
REASON_OUT_DISCONNECTED = 1
REASON_OUT_EJECTED = 2
REASON_OUT_QUIT = 3
REASON_OUT_DISQUALIFIED = 4

REASON_OUT_SHORT = {
    REASON_OUT_DISCONNECTED: "Disc",
    REASON_OUT_EJECTED: "Eject",
    REASON_OUT_QUIT: "Quit",
    REASON_OUT_DISQUALIFIED: "DQ",
}

REASON_OUT_TEXT_TO_ID = {
    "running": REASON_OUT_RUNNING,
    "disconnected": REASON_OUT_DISCONNECTED,
    "ejected": REASON_OUT_EJECTED,
    "quit": REASON_OUT_QUIT,
    "disqualified": REASON_OUT_DISQUALIFIED,
}

ROW_BG_LIKED = QColor(42, 72, 52)
ROW_BG_DISLIKED = QColor(72, 42, 42)
ROW_BG_HOVER = QColor(45, 52, 64)
ROW_FG_FOR_HIGHLIGHT = QColor(232, 234, 237)
PREF_DATA_ROLE = Qt.ItemDataRole.UserRole + 1

COL_NAME = 0
COL_RACES = 1
COL_AVG_INC = 2
COL_AVG_FINISH = 3
COL_AVG_POS = 4
COL_DNFS = 5
COL_LAST_SR = 6
COL_LAST_IR = 7
COL_SERIES = 8
COL_DNF_BREAKDOWN = 9
COL_NOTE = 10
COL_CUST_ID = 11
NOTE_INDICATOR = "+"

MSG_SESSION_NOT_CONNECTED = "Not connected to iRacing yet — start iRacing and join a session to enable."

_TABLE_DATA_SQL = """
    SELECT
        d.driver_name,
        ROUND(AVG(r.incidents), 1) AS avg_inc,
        ROUND(AVG(r.finish_position), 1) AS avg_fin,
        COUNT(r.id) AS total_races,
        d.last_irating,
        d.last_safety,
        d.last_series,
        ROUND(
            AVG(
                CASE
                    WHEN r.starting_position IS NOT NULL AND r.finish_position IS NOT NULL
                    THEN (r.starting_position - r.finish_position)
                END
            ),
            1
        ) AS avg_pos_delta,
        d.cust_id,
        d.race_preference,
        COALESCE(dnf.dnf_total, 0),
        COALESCE(dnf.disc, 0),
        COALESCE(dnf.eject, 0),
        COALESCE(dnf.quit_, 0),
        COALESCE(dnf.dq, 0),
        COALESCE(dnf.other, 0),
        CASE WHEN TRIM(COALESCE(d.notes, '')) != '' THEN 1 ELSE 0 END AS has_notes
    FROM drivers d
    LEFT JOIN race_results r ON d.cust_id = r.cust_id
    LEFT JOIN (
        SELECT
            cust_id,
            COUNT(*) AS dnf_total,
            SUM(CASE WHEN rid = 1 THEN 1 ELSE 0 END) AS disc,
            SUM(CASE WHEN rid = 2 THEN 1 ELSE 0 END) AS eject,
            SUM(CASE WHEN rid = 3 THEN 1 ELSE 0 END) AS quit_,
            SUM(CASE WHEN rid = 4 THEN 1 ELSE 0 END) AS dq,
            SUM(CASE WHEN rid NOT IN (1, 2, 3, 4) THEN 1 ELSE 0 END) AS other
        FROM (
            SELECT
                cust_id,
                CASE
                    WHEN reason_out_id IN (1, 2, 3, 4) THEN reason_out_id
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'disconnected' THEN 1
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'ejected' THEN 2
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'quit' THEN 3
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'disqualified' THEN 4
                    ELSE NULL
                END AS rid
            FROM race_results
        )
        WHERE rid IS NOT NULL
        GROUP BY cust_id
    ) dnf ON d.cust_id = dnf.cust_id
    GROUP BY d.cust_id
    ORDER BY d.driver_name ASC
"""

_DRIVER_DETAIL_SQL = """
    SELECT
        d.driver_name,
        d.last_seen_at,
        d.last_series,
        ROUND(AVG(r.incidents), 1),
        ROUND(AVG(r.finish_position), 1),
        COUNT(r.id),
        d.last_irating,
        d.last_safety,
        ROUND(
            AVG(
                CASE
                    WHEN r.starting_position IS NOT NULL AND r.finish_position IS NOT NULL
                    THEN (r.starting_position - r.finish_position)
                END
            ),
            1
        ),
        COALESCE(dnf.dnf_total, 0),
        COALESCE(dnf.disc, 0),
        COALESCE(dnf.eject, 0),
        COALESCE(dnf.quit_, 0),
        COALESCE(dnf.dq, 0),
        COALESCE(dnf.other, 0)
    FROM drivers d
    LEFT JOIN race_results r ON d.cust_id = r.cust_id
    LEFT JOIN (
        SELECT
            cust_id,
            COUNT(*) AS dnf_total,
            SUM(CASE WHEN rid = 1 THEN 1 ELSE 0 END) AS disc,
            SUM(CASE WHEN rid = 2 THEN 1 ELSE 0 END) AS eject,
            SUM(CASE WHEN rid = 3 THEN 1 ELSE 0 END) AS quit_,
            SUM(CASE WHEN rid = 4 THEN 1 ELSE 0 END) AS dq,
            SUM(CASE WHEN rid NOT IN (1, 2, 3, 4) THEN 1 ELSE 0 END) AS other
        FROM (
            SELECT
                cust_id,
                CASE
                    WHEN reason_out_id IN (1, 2, 3, 4) THEN reason_out_id
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'disconnected' THEN 1
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'ejected' THEN 2
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'quit' THEN 3
                    WHEN LOWER(TRIM(COALESCE(reason_out, ''))) = 'disqualified' THEN 4
                    ELSE NULL
                END AS rid
            FROM race_results
        )
        WHERE rid IS NOT NULL
        GROUP BY cust_id
    ) dnf ON d.cust_id = dnf.cust_id
    WHERE d.cust_id = ?
    GROUP BY d.cust_id
"""


class WrappingLabel(QLabel):
    """Label that wraps long text and reports correct height in scroll areas."""

    def __init__(self, text: str = "—", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        if width <= 0:
            return super().sizeHint().height()
        bounds = self.fontMetrics().boundingRect(
            0,
            0,
            width,
            10_000,
            int(Qt.TextFlag.TextWordWrap),
            self.text(),
        )
        return bounds.height() + 6


def _display_val(value) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text and text.lower() != "none" else "—"


def _normalize_reason_out_id(reason_out_id, reason_out) -> int | None:
    """Return 0 for Running, 1-4 for known DNF reasons, None if unknown/missing."""
    if isinstance(reason_out_id, int) and reason_out_id in REASON_OUT_TEXT_TO_ID.values():
        return reason_out_id
    if isinstance(reason_out, str):
        key = reason_out.strip().lower()
        if key in REASON_OUT_TEXT_TO_ID:
            return REASON_OUT_TEXT_TO_ID[key]
    return None


def _format_dnf_breakdown(disc: int, eject: int, quit_: int, dq: int, other: int) -> str:
    parts = []
    if disc:
        parts.append(f"Disc:{disc}")
    if eject:
        parts.append(f"Eject:{eject}")
    if quit_:
        parts.append(f"Quit:{quit_}")
    if dq:
        parts.append(f"DQ:{dq}")
    if other:
        parts.append(f"Other:{other}")
    return ", ".join(parts) if parts else ""


def _license_group_from_level(level: int | None) -> str | None:
    if not isinstance(level, int):
        return None
    # Based on iRacing license "level" groupings (matches your allowed_licenses ranges).
    if level <= 4:
        return "R"
    if 5 <= level <= 8:
        return "D"
    if 9 <= level <= 12:
        return "C"
    if 13 <= level <= 16:
        return "B"
    if 17 <= level <= 20:
        return "A"
    if 21 <= level <= 24:
        return "Pro"
    if 25 <= level <= 28:
        return "Pro/WC"
    return None


def _sr_from_sub_level(sub_level: int | None) -> float | None:
    # In event_result payloads, sub-level is typically SR * 100 (e.g. 367 -> 3.67).
    if not isinstance(sub_level, int):
        return None
    if sub_level < 0:
        return None
    return round(sub_level / 100.0, 2)


def _format_last_seen_et_mmddyyyy_hm(last_seen_at: str | None) -> str:
    """
    Convert stored ISO timestamp (typically UTC like 2026-05-27T01:51:32Z)
    to Eastern Time and format as MM/DD/YYYY h:mm AM/PM.
    """
    if not last_seen_at or not isinstance(last_seen_at, str):
        return "N/A"
    try:
        s = last_seen_at.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        et = dt.astimezone(ZoneInfo("America/New_York"))
        # Example: 05/26/2026 9:51 PM
        return et.strftime("%m/%d/%Y %-I:%M %p")
    except Exception:
        return "N/A"


def _sqlite_row_to_int(value) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _normalize_1_based(pos) -> int | None:
    # iRacing event_result uses 0-based positions (0 == P1).
    if isinstance(pos, int) and pos >= 0:
        return pos + 1
    return None


def _parse_iracing_event_result(data: dict) -> tuple[list[dict], str | None, str | None]:
    """
    Parse iRacing `event_result` JSON into our internal `races` format:
      [{"subsession_id": int, "results": list[dict]}]
    Returns (races, series_name, race_timestamp).
    """
    payload = data.get("data")
    if not isinstance(payload, dict):
        return ([], None, None)

    sub_id = _sqlite_row_to_int(payload.get("subsession_id")) or 0
    series_name = payload.get("series_name") or payload.get("season_name")
    race_timestamp = payload.get("end_time") or payload.get("start_time")

    sessions = payload.get("session_results", [])
    if not isinstance(sessions, list):
        return ([], series_name, race_timestamp)

    for s in sessions:
        if not isinstance(s, dict):
            continue
        if s.get("simsession_type_name") == "Race" or s.get("simsession_type") == 6:
            results = s.get("results", [])
            return ([{"subsession_id": sub_id, "results": results}], series_name, race_timestamp)

    return ([], series_name, race_timestamp)


def _parse_races_from_json(data) -> tuple[list[dict], str | None, str | None]:
    """
    Supported formats:
      1) {"races": [{"subsession_id":..., "results":[...]}]}
      2) [{"subsession_id":..., "results":[...]}]
      3) iRacing event_result payload:
         {"type":"event_result","data":{...}}
    Returns (races, series_name, race_timestamp).
    """
    if isinstance(data, dict) and data.get("type") == "event_result":
        return _parse_iracing_event_result(data)

    if isinstance(data, dict):
        races = data.get("races", [])
        return (races if isinstance(races, list) else [], None, None)

    if isinstance(data, list):
        return (data, None, None)

    return ([], None, None)


def _compute_last_license(driver: dict) -> str | None:
    sr = _sr_from_sub_level(driver.get("new_sub_level"))
    if sr is None:
        sr = _sr_from_sub_level(driver.get("old_sub_level"))

    lic_group = _license_group_from_level(driver.get("new_license_level"))
    if lic_group is None:
        lic_group = _license_group_from_level(driver.get("old_license_level"))

    if lic_group and sr is not None:
        return f"{lic_group} {sr:.2f}"
    return None


def _compute_irating_change(driver: dict) -> int:
    ir_change = driver.get("irating_change")
    if isinstance(ir_change, int):
        return ir_change
    old_ir = driver.get("oldi_rating")
    new_ir = driver.get("newi_rating")
    if isinstance(old_ir, int) and isinstance(new_ir, int):
        return new_ir - old_ir
    return 0


def _compute_new_irating(driver: dict) -> int | None:
    new_ir = driver.get("newi_rating")
    if isinstance(new_ir, int):
        return new_ir
    old_ir = driver.get("oldi_rating")
    return old_ir if isinstance(old_ir, int) else None


def _compute_new_sr(driver: dict) -> float | None:
    sr = _sr_from_sub_level(driver.get("new_sub_level"))
    if sr is not None:
        return sr
    return _sr_from_sub_level(driver.get("old_sub_level"))


def _maybe_update_last_seen(
    cursor: sqlite3.Cursor,
    cust_id: int,
    race_timestamp: str | None,
    new_ir: int | None,
    new_sr: float | None,
    last_license: str | None,
    series_name: str | None,
    start_pos: int | None,
) -> None:
    if not race_timestamp:
        return

    cursor.execute("SELECT last_seen_at FROM drivers WHERE cust_id = ?", (cust_id,))
    row = cursor.fetchone()
    existing_last_seen = row[0] if row and row[0] else None

    # ISO strings compare lexicographically in chronological order (when normalized).
    if existing_last_seen is not None and existing_last_seen >= race_timestamp:
        return

    cursor.execute(
        """
        UPDATE drivers
        SET last_irating = COALESCE(?, last_irating),
            last_safety = COALESCE(?, last_safety),
            last_license = COALESCE(?, last_license),
            last_series = COALESCE(?, last_series),
            last_starting_pos = COALESCE(?, last_starting_pos),
            last_seen_at = ?
        WHERE cust_id = ?
        """,
        (new_ir, new_sr, last_license, series_name, start_pos, race_timestamp, cust_id),
    )


def _import_race_entries(
    cursor: sqlite3.Cursor,
    races: list[dict],
    series_name: str | None,
    race_timestamp: str | None,
    license_text_fallback: str | None,
) -> tuple[int, int, int]:
    races_imported = 0
    results_imported = 0
    results_skipped = 0

    for entry in races:
        if not isinstance(entry, dict):
            continue
        sub_id = _sqlite_row_to_int(entry.get("subsession_id"))
        if sub_id is None:
            sub_id = _sqlite_row_to_int(entry.get("session_id"))
        sub_id = sub_id or 0
        results = entry.get("results", [])
        if not isinstance(results, list):
            continue

        race_had_new_result = False
        for driver in results:
            if not isinstance(driver, dict):
                continue

            cust_id = _sqlite_row_to_int(driver.get("cust_id"))
            if cust_id is None:
                continue

            name = driver.get("name", driver.get("display_name"))

            cursor.execute(
                """
                INSERT INTO drivers (cust_id, driver_name)
                VALUES (?, ?)
                ON CONFLICT(cust_id) DO UPDATE SET driver_name=excluded.driver_name
                """,
                (cust_id, name),
            )

            finish = driver.get("finish", driver.get("finish_position"))
            finish = _normalize_1_based(finish) if finish is not None else None

            start_pos = _normalize_1_based(driver.get("starting_position"))

            reason_out = driver.get("reason_out")
            reason_out = reason_out.strip() if isinstance(reason_out, str) and reason_out.strip() else None
            reason_out_id = _normalize_reason_out_id(driver.get("reason_out_id"), reason_out)
            if reason_out_id == REASON_OUT_RUNNING:
                reason_out = reason_out or "Running"

            ir_change = _compute_irating_change(driver)
            new_ir = _compute_new_irating(driver)
            new_sr = _compute_new_sr(driver)
            last_license = _compute_last_license(driver)

            license_text = driver.get("license", "Unknown")
            if license_text == "Unknown" and license_text_fallback:
                license_text = license_text_fallback

            cursor.execute(
                """
                INSERT OR IGNORE INTO race_results (
                    cust_id,
                    subsession_id,
                    finish_position,
                    incidents,
                    irating_change,
                    license_class,
                    starting_position,
                    reason_out,
                    reason_out_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cust_id,
                    sub_id,
                    finish,
                    driver.get("incidents", 0),
                    ir_change,
                    license_text,
                    start_pos,
                    reason_out,
                    reason_out_id,
                ),
            )
            if cursor.rowcount == 0:
                results_skipped += 1
                continue

            _maybe_update_last_seen(
                cursor,
                cust_id,
                race_timestamp,
                new_ir,
                new_sr,
                last_license,
                series_name,
                start_pos,
            )

            race_had_new_result = True
            results_imported += 1

        if race_had_new_result:
            races_imported += 1

    return (races_imported, results_imported, results_skipped)


class RaceBookApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GridNotes")
        self.setMinimumSize(1280, 760)
        self.resize(1440, 860)

        self.current_subsession_id = 0
        self.selected_cust_id = None
        self.worker = None
        self.active_cust_ids: set[int] = set()
        self._hover_row: int | None = None

        init_db()
        self._db_conn = connect_db()
        self.init_ui()
        self.start_sdk_worker()

    def _polish_property(self, widget: QWidget, name: str, value) -> None:
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _set_status(self, status: str, message: str) -> None:
        self.status_label.setText(message)
        self._polish_property(self.status_label, "status", status)

    def _configure_driver_table(self) -> None:
        self.table.setObjectName("driverTable")

        body_font = QFont()
        body_font.setPointSize(12)
        self.table.setFont(body_font)

        header_font = QFont(body_font)
        header_font.setPointSize(11)
        header_font.setBold(True)
        header = self.table.horizontalHeader()
        header.setFont(header_font)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.setToolTip("Click a column header to sort")
        header.setMinimumSectionSize(64)
        header.setDefaultSectionSize(100)
        header.setStretchLastSection(False)

        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        row_h = self.table.verticalHeader().defaultSectionSize()
        configure_widget_scrollbars(
            self.table,
            single_step=row_h,
            page_step=row_h * 4,
            horizontal_single=72,
            horizontal_page=240,
            always_show=True,
        )

        for col in (
            COL_RACES,
            COL_AVG_INC,
            COL_AVG_FINISH,
            COL_AVG_POS,
            COL_DNFS,
            COL_LAST_SR,
            COL_LAST_IR,
            COL_NOTE,
            COL_DNF_BREAKDOWN,
        ):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SERIES, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnHidden(COL_CUST_ID, True)
        self.table.setColumnWidth(COL_NAME, 200)
        self.table.setColumnWidth(COL_SERIES, 180)

        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item is not None:
                label = header_item.text()
                header_item.setToolTip(f"Click to sort by {label}")

        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.entered.connect(self._on_table_row_entered)
        self.table.viewport().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.table.viewport() and event.type() == QEvent.Type.Leave:
            self._clear_table_row_hover()
        return super().eventFilter(obj, event)

    def _pref_for_row(self, row_idx: int) -> int | None:
        name_item = self.table.item(row_idx, COL_NAME)
        if name_item is None:
            return None
        return _sqlite_row_to_int(name_item.data(PREF_DATA_ROLE))

    def _restore_row_background(self, row_idx: int) -> None:
        pref = self._pref_for_row(row_idx)
        if pref in (1, -1):
            self._apply_preference_row_style(row_idx, self.table.columnCount(), pref)
        else:
            self._clear_row_style(row_idx)

    def _apply_row_hover(self, row_idx: int) -> None:
        selected = self.table.selectionModel().selectedRows()
        if selected and selected[0].row() == row_idx:
            return
        for col_idx in range(self.table.columnCount()):
            item = self.table.item(row_idx, col_idx)
            if item is not None:
                item.setBackground(ROW_BG_HOVER)

    def _clear_table_row_hover(self) -> None:
        if self._hover_row is None:
            return
        self._restore_row_background(self._hover_row)
        self._hover_row = None

    def _on_table_row_entered(self, index) -> None:
        if not index.isValid():
            return
        row = index.row()
        if row == self._hover_row:
            return
        self._clear_table_row_hover()
        self._hover_row = row
        self._apply_row_hover(row)

    def _update_live_session_filter(self, *, active: bool, hint: str) -> None:
        self.chk_current_race_only.setVisible(active)
        self.chk_current_race_only.setEnabled(active)
        self.live_session_note.setVisible(not active)
        self.live_session_note.setText(hint)
        if not active:
            self.chk_current_race_only.setChecked(False)

    def _set_detail_field(self, key: str, value) -> None:
        label = self._detail_fields.get(key)
        if label is None:
            return
        text = _display_val(value)
        label.setText(text)
        if key in ("series", "dnf_breakdown"):
            label.setToolTip(text if text != "—" else "")
            label.updateGeometry()

    def _clear_driver_details(self) -> None:
        self.driver_name_label.clear()
        self.driver_meta_label.clear()
        for label in self._detail_fields.values():
            label.setText("—")

    def _fetch_driver_detail_row(self, cust_id: int) -> tuple | None:
        cursor = self._db_conn.cursor()
        cursor.execute(_DRIVER_DETAIL_SQL, (cust_id,))
        return cursor.fetchone()

    def _populate_driver_details(self, cust_id: int) -> None:
        row = self._fetch_driver_detail_row(cust_id)
        if not row:
            return

        (
            name,
            last_seen_at,
            last_series,
            avg_inc,
            avg_fin,
            total_races,
            last_ir,
            last_sr,
            avg_pos_delta,
            dnf_total,
            disc,
            eject,
            quit_,
            dq,
            other,
        ) = row

        last_seen_fmt = _format_last_seen_et_mmddyyyy_hm(last_seen_at)
        breakdown = _format_dnf_breakdown(disc, eject, quit_, dq, other)

        self.driver_name_label.setText(name or "Unknown driver")
        self.driver_meta_label.setText(
            f"ID {cust_id}  ·  Last raced {last_seen_fmt} ET"
        )
        self._set_detail_field("series", last_series)
        self._set_detail_field("avg_finish", avg_fin)
        self._set_detail_field("avg_incidents", avg_inc)
        self._set_detail_field("races", total_races)
        self._set_detail_field("last_irating", last_ir)
        self._set_detail_field("last_sr", last_sr)
        self._set_detail_field("avg_pos_delta", avg_pos_delta)
        self._set_detail_field("dnfs", dnf_total)
        self._set_detail_field("dnf_breakdown", breakdown if breakdown else None)

    def _set_driver_panel_enabled(self, enabled: bool) -> None:
        self.empty_state_label.setVisible(not enabled)
        self.driver_detail_scroll.setVisible(enabled)
        self.notes_edit.setEnabled(enabled)
        self.btn_pref_like.setEnabled(enabled)
        self.btn_pref_dislike.setEnabled(enabled)
        self.btn_pref_clear.setEnabled(enabled)
        self.btn_save_notes.setEnabled(enabled)

    def init_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(12)
        self.setCentralWidget(root)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        app_title = QLabel("GridNotes")
        app_title.setObjectName("appTitle")
        app_subtitle = QLabel("Driver scouting notes & race history")
        app_subtitle.setObjectName("appSubtitle")
        title_block.addWidget(app_title)
        title_block.addWidget(app_subtitle)
        header.addLayout(title_block)
        header.addStretch()
        self.status_label = QLabel("Waiting for iRacing…")
        self.status_label.setObjectName("statusBadge")
        self._set_status(STATUS_WAITING, "Waiting for iRacing…")
        header.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root_layout.addLayout(header)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(main_splitter, stretch=1)

        # --- Left: drivers ---
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout(controls_group)
        controls_layout.setHorizontalSpacing(10)
        controls_layout.setVerticalSpacing(8)

        self.btn_import = QPushButton("Import race JSON…")
        self.btn_import.setObjectName("primaryBtn")
        self.btn_import.setToolTip("Import iRacing event_result JSON or custom race logs")
        self.btn_import.clicked.connect(self.import_json_data)
        controls_layout.addWidget(self.btn_import, 0, 0)

        self.btn_reset_db = QPushButton("Reset all data")
        self.btn_reset_db.setObjectName("dangerBtn")
        self.btn_reset_db.setToolTip("Permanently delete all drivers, notes, and race results")
        self.btn_reset_db.clicked.connect(self.reset_database)
        controls_layout.addWidget(self.btn_reset_db, 0, 1)

        live_session_row = QHBoxLayout()
        live_session_row.setSpacing(8)
        self.chk_current_race_only = QCheckBox("Current session only")
        self.chk_current_race_only.setChecked(False)
        self.chk_current_race_only.setToolTip(
            "Show only drivers in this iRacing session who already have saved race history"
        )
        self.chk_current_race_only.stateChanged.connect(self.apply_driver_filters)
        live_session_row.addWidget(self.chk_current_race_only)
        self.live_session_note = QLabel(MSG_SESSION_NOT_CONNECTED)
        self.live_session_note.setObjectName("sectionHint")
        self.live_session_note.setWordWrap(True)
        live_session_row.addWidget(self.live_session_note, stretch=1)
        controls_layout.addLayout(live_session_row, 0, 2, 1, 2)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.apply_driver_filters)
        controls_layout.addWidget(self.search_input, 1, 0, 1, 2)

        self.ignore_name_input = QLineEdit()
        self.ignore_name_input.setPlaceholderText("Hide your name (optional)")
        self.ignore_name_input.setText(get_setting("ignore_driver_name", "") or "")
        self.ignore_name_input.textChanged.connect(self.apply_driver_filters)
        controls_layout.addWidget(self.ignore_name_input, 1, 2)

        self.btn_save_ignore = QPushButton("Save")
        self.btn_save_ignore.setToolTip("Save the hidden name to settings")
        self.btn_save_ignore.clicked.connect(self.save_ignore_name)
        controls_layout.addWidget(self.btn_save_ignore, 1, 3)

        left_layout.addWidget(controls_group)

        drivers_label = QLabel("Drivers — click a row for notes  ·  scroll horizontally for all columns")
        drivers_label.setObjectName("sectionHint")
        left_layout.addWidget(drivers_label)

        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels(
            [
                "Driver Name",
                "Races",
                "Avg Incidents",
                "Avg Finish",
                "Avg +/- Pos",
                "DNFs",
                "Last SR",
                "Last iRating",
                "Last Series",
                "DNF Breakdown",
                "Note",
                "ID",
            ]
        )
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setToolTip("Click a row to open scouting notes")
        self.table.itemSelectionChanged.connect(self.on_driver_selected)
        self._configure_driver_table()
        left_layout.addWidget(self.table, stretch=1)

        main_splitter.addWidget(left_panel)

        # --- Right: driver detail ---
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(8)

        detail_title = QLabel("Driver details")
        detail_title.setObjectName("appTitle")
        detail_title.setStyleSheet("font-size: 16px;")
        right_layout.addWidget(detail_title)

        self.empty_state_label = QLabel(
            "Select a driver from the table to view stats, write scouting notes, "
            "and mark whether you liked racing with them."
        )
        self.empty_state_label.setObjectName("emptyState")
        self.empty_state_label.setWordWrap(True)
        right_layout.addWidget(self.empty_state_label)

        self.driver_detail_scroll = QScrollArea()
        self.driver_detail_scroll.setObjectName("driverDetailScroll")
        self.driver_detail_scroll.setWidgetResizable(True)
        self.driver_detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.driver_detail_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.driver_detail_frame = QFrame()
        self.driver_detail_frame.setStyleSheet("background: transparent;")
        detail_layout = QVBoxLayout(self.driver_detail_frame)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(4)

        self.driver_name_label = QLabel()
        self.driver_name_label.setObjectName("driverName")
        self.driver_name_label.setWordWrap(True)
        detail_layout.addWidget(self.driver_name_label)

        self.driver_meta_label = QLabel()
        self.driver_meta_label.setObjectName("driverMeta")
        self.driver_meta_label.setWordWrap(True)
        detail_layout.addWidget(self.driver_meta_label)

        series_title = QLabel("Series")
        series_title.setObjectName("statLabel")
        detail_layout.addWidget(series_title)
        self._detail_fields = {}
        series_value = WrappingLabel("—")
        series_value.setObjectName("seriesValue")
        detail_layout.addWidget(series_value)
        self._detail_fields["series"] = series_value

        stats_block = QVBoxLayout()
        stats_block.setSpacing(4)
        stats_block.setContentsMargins(0, 6, 0, 0)
        for key, title in [
            ("avg_finish", "Avg finish"),
            ("avg_incidents", "Avg incidents"),
            ("races", "Races tracked"),
            ("last_irating", "Last iRating"),
            ("last_sr", "Last SR"),
            ("avg_pos_delta", "Avg +/- pos"),
            ("dnfs", "DNFs"),
            ("dnf_breakdown", "DNF breakdown"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            label = QLabel(f"{title}:")
            label.setObjectName("statInlineLabel")
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            if key == "dnf_breakdown":
                value: QLabel = WrappingLabel("—")
            else:
                value = QLabel("—")
                value.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
            value.setObjectName("statValue")
            value.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
            row.addWidget(label, 0)
            row.addWidget(value, 1)
            stats_block.addLayout(row)
            self._detail_fields[key] = value
        detail_layout.addLayout(stats_block)

        self.driver_detail_scroll.setWidget(self.driver_detail_frame)
        configure_scroll_area(self.driver_detail_scroll, page_step=96)
        self.driver_detail_scroll.setVisible(False)
        right_layout.addWidget(self.driver_detail_scroll)

        notes_group = QGroupBox("Scouting notes")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "e.g. Aggressive on restarts, gives room on restarts, weak under pressure…"
        )
        self.notes_edit.setMinimumHeight(140)
        configure_widget_scrollbars(self.notes_edit, single_step=20, page_step=100)
        notes_layout.addWidget(self.notes_edit)
        right_layout.addWidget(notes_group, stretch=1)

        pref_group = QGroupBox("How was racing with them?")
        pref_layout = QHBoxLayout(pref_group)
        self.btn_pref_like = QPushButton("Liked")
        self.btn_pref_like.setObjectName("prefLike")
        self.btn_pref_like.setCheckable(True)
        self.btn_pref_like.setToolTip("Highlight row green in the driver list")
        self.btn_pref_like.clicked.connect(lambda: self.set_race_preference(1))
        pref_layout.addWidget(self.btn_pref_like)
        self.btn_pref_dislike = QPushButton("Didn't like")
        self.btn_pref_dislike.setObjectName("prefDislike")
        self.btn_pref_dislike.setCheckable(True)
        self.btn_pref_dislike.setToolTip("Highlight row red in the driver list")
        self.btn_pref_dislike.clicked.connect(lambda: self.set_race_preference(-1))
        pref_layout.addWidget(self.btn_pref_dislike)
        self.btn_pref_clear = QPushButton("Clear")
        self.btn_pref_clear.setToolTip("Remove like/dislike highlight")
        self.btn_pref_clear.clicked.connect(lambda: self.set_race_preference(None))
        pref_layout.addWidget(self.btn_pref_clear)
        right_layout.addWidget(pref_group)

        self.btn_save_notes = QPushButton("Save notes")
        self.btn_save_notes.setObjectName("primaryBtn")
        self.btn_save_notes.clicked.connect(self.save_driver_notes)
        right_layout.addWidget(self.btn_save_notes)

        main_splitter.addWidget(right_panel)
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(520)
        main_splitter.setStretchFactor(0, 5)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setSizes([1000, 340])

        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        self._set_driver_panel_enabled(False)
        self.refresh_ui_table()
        self.apply_driver_filters()

    def save_ignore_name(self):
        set_setting("ignore_driver_name", (self.ignore_name_input.text() or "").strip() or None)
        self.apply_driver_filters()

    def apply_driver_filters(self, *_):
        q = (self.search_input.text() or "").strip().lower()
        ignore_name = (self.ignore_name_input.text() or "").strip().lower()
        current_only = (
            hasattr(self, "chk_current_race_only")
            and self.chk_current_race_only.isEnabled()
            and self.chk_current_race_only.isChecked()
        )

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, COL_NAME)
            name = (name_item.text() if name_item else "").strip()
            name_lc = name.lower()

            hidden = False
            if q and q not in name_lc:
                hidden = True
            if ignore_name and name_lc == ignore_name:
                hidden = True
            if current_only:
                cust_item = self.table.item(row, COL_CUST_ID)
                try:
                    cust_id = int(cust_item.text()) if cust_item else None
                except Exception:
                    cust_id = None
                races_item = self.table.item(row, COL_RACES)
                try:
                    race_count = int(races_item.text()) if races_item else 0
                except (TypeError, ValueError):
                    race_count = 0
                if (
                    cust_id is None
                    or cust_id not in self.active_cust_ids
                    or race_count <= 0
                ):
                    hidden = True
            self.table.setRowHidden(row, hidden)

    def reset_database(self):
        res = QMessageBox.question(
            self,
            "Reset Database?",
            "This will permanently delete ALL drivers, notes, and race results from the local database.\n\n"
            "Are you sure you want to reset?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        conn = self._db_conn
        cursor = conn.cursor()
        cursor.execute("DELETE FROM race_results")
        cursor.execute("DELETE FROM drivers")
        conn.commit()

        self.current_subsession_id = 0
        self.selected_cust_id = None
        self.active_cust_ids = set()
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        self.notes_edit.clear()
        self._clear_driver_details()
        self._set_driver_panel_enabled(False)
        self.table.clearSelection()
        self.refresh_ui_table()

        QMessageBox.information(self, "Database Reset", "Database cleared successfully.")

    def start_sdk_worker(self):
        logger.info("Starting iRacing SDK worker…")

        worker = IRacingWorker()
        if not getattr(worker, "available", False):
            reason = getattr(worker, "unavailable_reason", "") or "pyirsdk unavailable"
            logger.warning("SDK worker not available: %s", reason)
            self._set_status(STATUS_OFFLINE, f"Offline — {reason}")
            self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
            self.worker = None
            return

        logger.info("SDK worker available; starting background thread")
        self.worker = worker
        self.worker.connection_changed.connect(self.handle_sdk_connection)
        self.worker.drivers_updated.connect(self.handle_sdk_update)
        self.worker.start()
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)

    def handle_sdk_connection(self, connected: bool, subsession_id: int) -> None:
        if connected:
            label = f"Live — session #{subsession_id}" if subsession_id else "Live — connected to iRacing"
            self._set_status(STATUS_CONNECTED, label)
            self._update_live_session_filter(active=True, hint="")
            self.current_subsession_id = subsession_id
            return

        self.current_subsession_id = 0
        self.active_cust_ids = set()
        self._set_status(STATUS_WAITING, "Waiting for iRacing…")
        self._update_live_session_filter(active=False, hint=MSG_SESSION_NOT_CONNECTED)
        if hasattr(self, "chk_current_race_only"):
            self.chk_current_race_only.setChecked(False)

    def handle_sdk_update(self, active_drivers, subsession_id):
        self.current_subsession_id = subsession_id
        driver_count = len(active_drivers)
        if subsession_id:
            status = f"Live — session #{subsession_id} · {driver_count} drivers"
        else:
            status = f"Live — connected · {driver_count} drivers"
        self._set_status(STATUS_CONNECTED, status)
        self._update_live_session_filter(active=True, hint="")

        self.active_cust_ids = {
            int(d["cust_id"])
            for d in active_drivers
            if d.get("cust_id") is not None
        }
        self.apply_driver_filters()

    def refresh_ui_table(self):
        rows = self._fetch_table_data()

        was_sorting = self.table.isSortingEnabled()
        if was_sorting:
            self.table.setSortingEnabled(False)

        self._clear_table_row_hover()
        self.table.setUpdatesEnabled(False)
        try:
            self.table.clearContents()
            self.table.setRowCount(len(rows))
            for row_idx, row_data in enumerate(rows):
                display_row, cust_id, pref = self._build_display_row(row_data)
                self._render_table_row(row_idx, display_row, cust_id, pref)
                self._apply_preference_row_style(row_idx, len(display_row), pref)
        finally:
            self.table.setUpdatesEnabled(True)

        if was_sorting:
            self.table.setSortingEnabled(True)
        self.table.sortByColumn(COL_NAME, Qt.SortOrder.AscendingOrder)
        self.table.horizontalHeader().setSortIndicator(COL_NAME, Qt.SortOrder.AscendingOrder)
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(COL_NAME, max(self.table.columnWidth(COL_NAME), 180))
        self.table.setColumnWidth(COL_SERIES, max(self.table.columnWidth(COL_SERIES), 160))
        self.apply_driver_filters()

    def _fetch_table_data(self) -> list[tuple]:
        cursor = self._db_conn.cursor()
        cursor.execute(_TABLE_DATA_SQL)
        return cursor.fetchall()

    def _build_display_row(self, row_data: tuple) -> tuple[list, int, int | None]:
        (
            name,
            avg_inc,
            avg_fin,
            total_races,
            last_ir,
            last_sr,
            last_series,
            avg_pos_delta,
            cust_id,
            race_preference,
            dnf_total,
            disc,
            eject,
            quit_,
            dq,
            other,
            has_notes,
        ) = row_data
        cid = int(cust_id)
        pref = _sqlite_row_to_int(race_preference)
        breakdown = _format_dnf_breakdown(disc, eject, quit_, dq, other) or "—"
        has_note = bool(has_notes)
        return (
            [
                name,
                total_races,
                avg_inc,
                avg_fin,
                avg_pos_delta,
                dnf_total,
                last_sr,
                last_ir,
                last_series,
                breakdown,
                has_note,
                cid,
            ],
            cid,
            pref,
        )

    def _make_table_item(self, value) -> QTableWidgetItem:
        item = QTableWidgetItem()
        if value is None:
            item.setText("N/A")
        else:
            if isinstance(value, (int, float)):
                item.setData(Qt.ItemDataRole.EditRole, value)
            item.setText(str(value))
        item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        return item

    def _make_note_item(self, has_note: bool) -> QTableWidgetItem:
        item = QTableWidgetItem(NOTE_INDICATOR if has_note else "")
        item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setData(Qt.ItemDataRole.UserRole, 1 if has_note else 0)
        if has_note:
            item.setToolTip("Has scouting notes")
        return item

    def _render_table_row(
        self, row_idx: int, display_row: list, cust_id: int, pref: int | None = None
    ) -> None:
        for col_idx, value in enumerate(display_row):
            if col_idx == COL_NOTE:
                item = self._make_note_item(bool(value))
            else:
                item = self._make_table_item(value)
            if col_idx == COL_NAME:
                item.setData(Qt.ItemDataRole.UserRole, cust_id)
                item.setData(PREF_DATA_ROLE, pref)
            self.table.setItem(row_idx, col_idx, item)

    def _apply_preference_row_style(self, row_idx: int, col_count: int, pref: int | None) -> None:
        if pref == 1:
            bg = ROW_BG_LIKED
        elif pref == -1:
            bg = ROW_BG_DISLIKED
        else:
            return

        for col_idx in range(col_count):
            it = self.table.item(row_idx, col_idx)
            if it is not None:
                it.setBackground(bg)
                it.setForeground(ROW_FG_FOR_HIGHLIGHT)

    def on_driver_selected(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            self.selected_cust_id = None
            self._set_driver_panel_enabled(False)
            return

        row = selected_ranges[0].topRow()
        name_item = self.table.item(row, COL_NAME)
        if not name_item:
            return

        cust_id = name_item.data(Qt.ItemDataRole.UserRole)
        if cust_id is None:
            cust_id_item = self.table.item(row, COL_CUST_ID)
            if not cust_id_item:
                return
            cust_id = int(cust_id_item.text())

        self.selected_cust_id = int(cust_id)
        _, notes, pref = self._fetch_driver_notes_meta(self.selected_cust_id)

        self._update_preference_buttons(pref)
        self._populate_driver_details(self.selected_cust_id)
        self.notes_edit.setText(notes or "")
        self._set_driver_panel_enabled(True)

    def _fetch_driver_notes_meta(self, cust_id: int) -> tuple[str | None, str, int | None]:
        cursor = self._db_conn.cursor()
        cursor.execute(
            "SELECT last_seen_at, notes, race_preference FROM drivers WHERE cust_id = ?",
            (cust_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None, "", None

        last_seen_at = row[0]
        notes = row[1] or ""
        pref = _sqlite_row_to_int(row[2])
        return last_seen_at, notes, pref

    def _update_preference_buttons(self, pref: int | None):
        self.btn_pref_like.setChecked(pref == 1)
        self.btn_pref_dislike.setChecked(pref == -1)
        self._polish_property(self.btn_pref_like, "selected", pref == 1)
        self._polish_property(self.btn_pref_dislike, "selected", pref == -1)

    def _row_for_cust_id(self, cust_id: int) -> int | None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_CUST_ID)
            if not item:
                continue
            try:
                if int(item.text()) == cust_id:
                    return row
            except Exception:
                continue
        return None

    def _select_driver_row_by_cust_id(self, cust_id: int):
        row = self._row_for_cust_id(cust_id)
        if row is not None:
            self.table.selectRow(row)

    def _set_note_indicator(self, cust_id: int, has_note: bool) -> None:
        row_idx = self._row_for_cust_id(cust_id)
        if row_idx is None:
            return
        self.table.setItem(row_idx, COL_NOTE, self._make_note_item(has_note))

    def _clear_row_style(self, row_idx: int) -> None:
        for col_idx in range(self.table.columnCount()):
            item = self.table.item(row_idx, col_idx)
            if item is None:
                continue
            item.setData(Qt.ItemDataRole.BackgroundRole, None)
            item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def save_driver_notes(self):
        if not self.selected_cust_id:
            QMessageBox.warning(
                self, "Selection Required", "Please click a driver on the left side first."
            )
            return

        notes_text = self.notes_edit.toPlainText()
        cursor = self._db_conn.cursor()
        cursor.execute(
            "UPDATE drivers SET notes = ? WHERE cust_id = ?",
            (notes_text, self.selected_cust_id),
        )
        self._db_conn.commit()
        self._set_note_indicator(self.selected_cust_id, bool(notes_text.strip()))
        QMessageBox.information(self, "Saved", "Driver notebook updated successfully.")

    def set_race_preference(self, pref: int | None):
        if not self.selected_cust_id:
            QMessageBox.warning(self, "Selection Required", "Please click a driver first.")
            return

        cust_id = self.selected_cust_id
        cursor = self._db_conn.cursor()
        cursor.execute(
            "UPDATE drivers SET race_preference = ? WHERE cust_id = ?",
            (pref, cust_id),
        )
        self._db_conn.commit()
        self._update_preference_buttons(pref)

        row_idx = self._row_for_cust_id(cust_id)
        if row_idx is not None:
            name_item = self.table.item(row_idx, COL_NAME)
            if name_item is not None:
                name_item.setData(PREF_DATA_ROLE, pref)
            if pref is None:
                self._clear_row_style(row_idx)
            else:
                self._apply_preference_row_style(row_idx, self.table.columnCount(), pref)

    def import_json_data(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Historic Race Log(s)", "", "JSON Files (*.json)"
        )
        if not file_paths:
            return

        total_files = 0
        total_races_imported = 0
        total_results_imported = 0
        total_results_skipped = 0
        errors: list[str] = []

        conn = self._db_conn
        cursor = conn.cursor()

        for file_path in file_paths:
            if not file_path:
                continue
            total_files += 1
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                races, series_name, race_timestamp = _parse_races_from_json(data)
                license_text_fallback = None
                if isinstance(data, dict) and isinstance(data.get("data"), dict):
                    cat = data["data"].get("license_category")
                    license_text_fallback = str(cat) if cat else None

                races_imported, results_imported, results_skipped = _import_race_entries(
                    cursor,
                    races,
                    series_name,
                    race_timestamp,
                    license_text_fallback,
                )

                total_races_imported += races_imported
                total_results_imported += results_imported
                total_results_skipped += results_skipped

                if results_imported == 0 and results_skipped == 0:
                    errors.append(f"{file_path}: no race results found/imported")

                del data, races

            except Exception as e:
                logger.exception("Import failed for %s", file_path)
                errors.append(f"{file_path}: {e}")

        conn.commit()
        logger.info(
            "Import finished: files=%s races=%s results=%s skipped=%s errors=%s",
            total_files,
            total_races_imported,
            total_results_imported,
            total_results_skipped,
            len(errors),
        )

        self.refresh_ui_table()

        if total_results_imported == 0 and total_results_skipped > 0:
            QMessageBox.information(
                self,
                "Data Already Saved",
                "This race session is already saved in your database.\n\n"
                f"{total_results_skipped} driver result(s) were not imported again "
                "(matched by subsession ID).\n\n"
                "Your stats and scouting notes were not changed.",
            )
            return

        if total_results_imported == 0:
            QMessageBox.warning(
                self,
                "Import Completed (No Results Found)",
                "No race results were imported from the selected file(s).\n\n"
                "This usually means the JSON structure/keys don't match what the importer expects.\n"
                "Supported:\n"
                "- iRacing 'event_result' JSON (imports Race session), or\n"
                "- custom {'races': [...]} format.\n\n"
                "Each result is stored once per driver per subsession ID; re-importing the same "
                "session does not duplicate stats.\n\n"
                + ("\n\nDetails:\n" + "\n".join(errors[:10]) if errors else ""),
            )
            return

        detail = ""
        if total_results_skipped:
            detail = (
                f"\n\n{total_results_skipped} driver result(s) were already saved and were not "
                "imported again."
            )
        if errors:
            detail += "\n\nSome files had issues:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                detail += f"\n... and {len(errors) - 10} more."

        title = "Import Complete"
        if total_results_skipped and not total_results_imported:
            title = "Data Already Saved"
        elif total_results_skipped:
            title = "Import Complete — Some Data Already Saved"

        QMessageBox.information(
            self,
            title,
            f"Imported {total_results_imported} new driver result(s) across "
            f"{total_races_imported} race(s) from {total_files} file(s)."
            + detail,
        )

    def closeEvent(self, event):
        logger.info("Application closing")
        if self.worker is not None:
            self.worker.stop()
        if hasattr(self, "_db_conn"):
            self._db_conn.close()
        event.accept()

