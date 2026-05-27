import json
import html
import random
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .db import DB_NAME, get_setting, init_db, set_setting
from .iracing_worker import IRacingWorker

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

ROW_BG_LIKED = QColor(210, 255, 210)
ROW_BG_DISLIKED = QColor(255, 210, 210)
ROW_FG_FOR_HIGHLIGHT = QColor(0, 0, 0)


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

    sub_id = payload.get("subsession_id", 0)
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
) -> tuple[int, int]:
    races_imported = 0
    results_imported = 0

    for entry in races:
        if not isinstance(entry, dict):
            continue
        sub_id = entry.get("subsession_id", 0)
        results = entry.get("results", [])
        if not isinstance(results, list):
            continue

        any_result = False
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
                INSERT INTO race_results (
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

            any_result = True
            results_imported += 1

        if any_result:
            races_imported += 1

    return (races_imported, results_imported)


class RaceBookApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iRacing Driver Book & Race Logger")
        self.setMinimumSize(1000, 600)

        self.current_subsession_id = 0
        self.selected_cust_id = None
        self.worker = None
        self.active_cust_ids: set[int] = set()

        init_db()
        self.init_ui()
        self.start_sdk_worker()

    def init_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(main_splitter)

        # LEFT: Controls & Driver List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.status_label = QLabel("Status: Waiting for iRacing connection...")
        self.status_label.setStyleSheet("font-weight: bold; color: #ff9900;")
        left_layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.btn_import = QPushButton("Import Old Race JSON")
        self.btn_import.clicked.connect(self.import_json_data)
        btn_layout.addWidget(self.btn_import)

        self.chk_current_race_only = QCheckBox("Show current race only")
        self.chk_current_race_only.setEnabled(False)  # enabled only when SDK connected
        self.chk_current_race_only.setChecked(False)
        self.chk_current_race_only.stateChanged.connect(self.apply_driver_filters)
        btn_layout.addWidget(self.chk_current_race_only)

        self.btn_reset_db = QPushButton("Reset Database")
        self.btn_reset_db.clicked.connect(self.reset_database)
        btn_layout.addWidget(self.btn_reset_db)

        left_layout.addLayout(btn_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search driver name…")
        self.search_input.textChanged.connect(self.apply_driver_filters)
        left_layout.addWidget(self.search_input)

        ignore_layout = QHBoxLayout()
        self.ignore_name_input = QLineEdit()
        self.ignore_name_input.setPlaceholderText("Ignore name (e.g. Logan Troyer)")
        self.ignore_name_input.setText(get_setting("ignore_driver_name", "") or "")
        self.ignore_name_input.textChanged.connect(self.apply_driver_filters)
        ignore_layout.addWidget(self.ignore_name_input)

        self.btn_save_ignore = QPushButton("Save")
        self.btn_save_ignore.clicked.connect(self.save_ignore_name)
        ignore_layout.addWidget(self.btn_save_ignore)
        left_layout.addLayout(ignore_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            [
                "Driver Name",
                "Avg Incidents",
                "Avg Finish",
                "Races Tracked",
                "Last iRating",
                "Last SR",
                "Last Series",
                "Avg +/- Pos",
                "DNFs",
                "DNF Breakdown",
                "Customer ID",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_driver_selected)
        left_layout.addWidget(self.table)

        main_splitter.addWidget(left_widget)

        # RIGHT: Notes
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(QLabel("### Driver Intel & Scouting Notes"))
        self.driver_title_label = QLabel("Select a driver to view/edit notes.")
        self.driver_title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        right_layout.addWidget(self.driver_title_label)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Type behavioral traits here... (e.g., 'Aggressive on restarts', 'Clean racer, gives space', 'Prone to self-spinning under pressure')"
        )
        right_layout.addWidget(self.notes_edit)

        pref_layout = QHBoxLayout()
        pref_layout.addWidget(QLabel("Racing preference:"))

        self.btn_pref_like = QPushButton("Liked")
        self.btn_pref_like.setCheckable(True)
        self.btn_pref_like.clicked.connect(lambda: self.set_race_preference(1))
        pref_layout.addWidget(self.btn_pref_like)

        self.btn_pref_dislike = QPushButton("Didn't like")
        self.btn_pref_dislike.setCheckable(True)
        self.btn_pref_dislike.clicked.connect(lambda: self.set_race_preference(-1))
        pref_layout.addWidget(self.btn_pref_dislike)

        self.btn_pref_clear = QPushButton("Clear")
        self.btn_pref_clear.clicked.connect(lambda: self.set_race_preference(None))
        pref_layout.addWidget(self.btn_pref_clear)

        right_layout.addLayout(pref_layout)

        self.btn_save_notes = QPushButton("Save Driver Notes")
        self.btn_save_notes.clicked.connect(self.save_driver_notes)
        right_layout.addWidget(self.btn_save_notes)

        main_splitter.addWidget(right_widget)

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
            name_item = self.table.item(row, 0)
            name = (name_item.text() if name_item else "").strip()
            name_lc = name.lower()

            hidden = False
            if q and q not in name_lc:
                hidden = True
            if ignore_name and name_lc == ignore_name:
                hidden = True
            if current_only:
                cust_item = self.table.item(row, 10)
                try:
                    cust_id = int(cust_item.text()) if cust_item else None
                except Exception:
                    cust_id = None
                if cust_id is None or cust_id not in self.active_cust_ids:
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

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM race_results")
        cursor.execute("DELETE FROM drivers")
        conn.commit()
        conn.close()

        self.current_subsession_id = 0
        self.selected_cust_id = None
        self.active_cust_ids = set()
        if hasattr(self, "chk_current_race_only"):
            self.chk_current_race_only.setChecked(False)
            self.chk_current_race_only.setEnabled(False)
        self.notes_edit.setText("")
        self.driver_title_label.setText("Select a driver to view/edit notes.")
        self.table.clearSelection()
        self.refresh_ui_table()

        QMessageBox.information(self, "Database Reset", "Database cleared successfully.")

    def start_sdk_worker(self):
        worker = IRacingWorker()
        if not getattr(worker, "available", False):
            self.status_label.setText("Status: Offline mode (iRacing SDK not available).")
            self.status_label.setStyleSheet("font-weight: bold; color: #666666;")
            if hasattr(self, "chk_current_race_only"):
                self.chk_current_race_only.setChecked(False)
                self.chk_current_race_only.setEnabled(False)
            self.worker = None
            return

        self.worker = worker
        self.worker.drivers_updated.connect(self.handle_sdk_update)
        self.worker.start()

    def handle_sdk_update(self, active_drivers, subsession_id):
        self.current_subsession_id = subsession_id
        self.status_label.setText(
            f"Status: Connected to live Session #{subsession_id} ({len(active_drivers)} drivers found)"
        )
        self.status_label.setStyleSheet("font-weight: bold; color: #00aa00;")
        if hasattr(self, "chk_current_race_only"):
            self.chk_current_race_only.setEnabled(True)

        self.active_cust_ids = {d.get("cust_id") for d in active_drivers if d.get("cust_id") is not None}

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        for d in active_drivers:
            cursor.execute(
                """
                INSERT INTO drivers (cust_id, driver_name)
                VALUES (?, ?)
                ON CONFLICT(cust_id) DO UPDATE SET driver_name=excluded.driver_name
                """,
                (d["cust_id"], d["name"]),
            )
        conn.commit()
        conn.close()
        self.apply_driver_filters()

    def refresh_ui_table(self):
        rows, pref_by_driver, dnf_by_driver = self._fetch_table_data()

        was_sorting = self.table.isSortingEnabled()
        if was_sorting:
            self.table.setSortingEnabled(False)

        self.table.setRowCount(0)
        for row_idx, row_data in enumerate(rows):
            self.table.insertRow(row_idx)
            display_row, cust_id = self._build_display_row(row_data, dnf_by_driver)
            self._render_table_row(row_idx, display_row)
            self._apply_preference_row_style(row_idx, len(display_row), pref_by_driver.get(cust_id))

        if was_sorting:
            self.table.setSortingEnabled(True)
        self.apply_driver_filters()

    def _fetch_table_data(
        self,
    ) -> tuple[list[tuple], dict[int, int], dict[int, list[int]]]:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                d.driver_name,
                ROUND(AVG(r.incidents), 1) as avg_inc,
                ROUND(AVG(r.finish_position), 1) as avg_fin,
                COUNT(r.id) as total_races,
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
                ) as avg_pos_delta,
                d.cust_id
            FROM drivers d
            LEFT JOIN race_results r ON d.cust_id = r.cust_id
            GROUP BY d.cust_id
            ORDER BY total_races DESC, d.driver_name ASC
            """
        )
        rows = cursor.fetchall()

        pref_by_driver: dict[int, int] = {}
        cursor.execute("SELECT cust_id, race_preference FROM drivers WHERE race_preference IS NOT NULL")
        for cust_id, pref in cursor.fetchall():
            cid = _sqlite_row_to_int(cust_id)
            p = _sqlite_row_to_int(pref)
            if cid is not None and p is not None:
                pref_by_driver[cid] = p

        dnf_by_driver: dict[int, list[int]] = {}
        cursor.execute("SELECT cust_id, reason_out_id, reason_out FROM race_results")
        for cust_id, reason_out_id, reason_out in cursor.fetchall():
            cid = _sqlite_row_to_int(cust_id)
            if cid is None:
                continue
            rid = _normalize_reason_out_id(reason_out_id, reason_out)
            if rid is None or rid == REASON_OUT_RUNNING:
                continue

            # total, disc, eject, quit, dq, other
            if cid not in dnf_by_driver:
                dnf_by_driver[cid] = [0, 0, 0, 0, 0, 0]
            dnf_by_driver[cid][0] += 1
            if rid == REASON_OUT_DISCONNECTED:
                dnf_by_driver[cid][1] += 1
            elif rid == REASON_OUT_EJECTED:
                dnf_by_driver[cid][2] += 1
            elif rid == REASON_OUT_QUIT:
                dnf_by_driver[cid][3] += 1
            elif rid == REASON_OUT_DISQUALIFIED:
                dnf_by_driver[cid][4] += 1
            else:
                dnf_by_driver[cid][5] += 1

        conn.close()
        return rows, pref_by_driver, dnf_by_driver

    def _build_display_row(
        self, row_data: tuple, dnf_by_driver: dict[int, list[int]]
    ) -> tuple[list, int]:
        name, avg_inc, avg_fin, total_races, last_ir, last_sr, last_series, avg_pos_delta, cust_id = row_data
        cid = int(cust_id)
        dnf_total, disc, eject, quit_, dq, other = dnf_by_driver.get(cid, [0, 0, 0, 0, 0, 0])
        breakdown = _format_dnf_breakdown(disc, eject, quit_, dq, other) or "—"
        return (
            [
                name,
                avg_inc,
                avg_fin,
                total_races,
                last_ir,
                last_sr,
                last_series,
                avg_pos_delta,
                dnf_total,
                breakdown,
                cid,
            ],
            cid,
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

    def _render_table_row(self, row_idx: int, display_row: list) -> None:
        for col_idx, value in enumerate(display_row):
            self.table.setItem(row_idx, col_idx, self._make_table_item(value))

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
            return

        row = selected_ranges[0].topRow()
        cust_id_item = self.table.item(row, 10)
        if not cust_id_item:
            return

        self.selected_cust_id = int(cust_id_item.text())
        driver_name = self.table.item(row, 0).text()

        def cell_text(col: int) -> str:
            item = self.table.item(row, col)
            if not item:
                return "N/A"
            txt = item.text().strip()
            return txt if txt else "N/A"

        last_seen_at, notes, pref = self._fetch_driver_notes_meta(self.selected_cust_id)

        self._update_preference_buttons(pref)
        last_seen_fmt = _format_last_seen_et_mmddyyyy_hm(last_seen_at)

        series_value = cell_text(6)
        self.driver_title_label.setText(
            self._build_notes_header_html(
                driver_name=driver_name,
                cust_id=self.selected_cust_id,
                last_seen_fmt=last_seen_fmt,
                series_value=series_value,
                cell_text=cell_text,
            )
        )
        self.notes_edit.setText(notes or "")

    def _fetch_driver_notes_meta(self, cust_id: int) -> tuple[str | None, str, int | None]:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_seen_at, notes, race_preference FROM drivers WHERE cust_id = ?",
            (cust_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None, "", None

        last_seen_at = row[0]
        notes = row[1] or ""
        pref = _sqlite_row_to_int(row[2])
        return last_seen_at, notes, pref

    def _build_notes_header_html(
        self,
        driver_name: str,
        cust_id: int,
        last_seen_fmt: str,
        series_value: str,
        cell_text,
    ) -> str:
        driver_line = (
            f"<b>{html.escape(driver_name)}</b> (ID: {cust_id})"
            f" — Last raced: {html.escape(last_seen_fmt)} ET"
        )
        series_line = (
            f"<b>Series:</b> {html.escape(series_value)}"
            if series_value != "N/A"
            else "<b>Series:</b> N/A"
        )

        cols = [2, 3, 4, 5, 7, 8, 9, 10]
        kvs: list[tuple[str, str]] = []
        for col_idx in cols:
            header = self.table.horizontalHeaderItem(col_idx)
            label = header.text() if header else f"Col {col_idx}"
            kvs.append((label, cell_text(col_idx)))

        split_at = (len(kvs) + 1) // 2
        left = kvs[:split_at]
        right = kvs[split_at:]

        rows_html: list[str] = []
        for i in range(max(len(left), len(right))):
            l = left[i] if i < len(left) else ("", "")
            r = right[i] if i < len(right) else ("", "")
            left_txt = f"<b>{html.escape(l[0])}:</b> {html.escape(l[1])}" if l[0] else ""
            right_txt = f"<b>{html.escape(r[0])}:</b> {html.escape(r[1])}" if r[0] else ""
            rows_html.append(
                "<tr>"
                f"<td style='padding-right:18px; white-space:nowrap;'>{left_txt}</td>"
                f"<td style='white-space:nowrap;'>{right_txt}</td>"
                "</tr>"
            )

        return (
            driver_line
            + "<br/>"
            + series_line
            + "<br/>"
            + "<table style='border-collapse:collapse;'>"
            + "".join(rows_html)
            + "</table>"
        )

    def _update_preference_buttons(self, pref: int | None):
        # Visually select the matching preference button.
        self.btn_pref_like.setChecked(pref == 1)
        self.btn_pref_dislike.setChecked(pref == -1)

        # Filled styling so selection is obvious even with OS themes.
        if pref == 1:
            self.btn_pref_like.setStyleSheet(
                "font-weight: bold; background-color: #6EEB83; color: #000000; border-radius: 10px; padding: 6px 10px;"
            )
            self.btn_pref_dislike.setStyleSheet("")
        elif pref == -1:
            self.btn_pref_dislike.setStyleSheet(
                "font-weight: bold; background-color: #FF6B6B; color: #000000; border-radius: 10px; padding: 6px 10px;"
            )
            self.btn_pref_like.setStyleSheet("")
        else:
            self.btn_pref_like.setStyleSheet("")
            self.btn_pref_dislike.setStyleSheet("")

    def _select_driver_row_by_cust_id(self, cust_id: int):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 10)
            if not item:
                continue
            try:
                row_id = int(item.text())
            except Exception:
                continue
            if row_id == cust_id:
                self.table.selectRow(row)
                return

    def save_driver_notes(self):
        if not self.selected_cust_id:
            QMessageBox.warning(
                self, "Selection Required", "Please click a driver on the left side first."
            )
            return

        notes_text = self.notes_edit.toPlainText()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE drivers SET notes = ? WHERE cust_id = ?",
            (notes_text, self.selected_cust_id),
        )
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Saved", "Driver notebook updated successfully.")

    def set_race_preference(self, pref: int | None):
        if not self.selected_cust_id:
            QMessageBox.warning(self, "Selection Required", "Please click a driver first.")
            return

        cust_id = self.selected_cust_id
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE drivers SET race_preference = ? WHERE cust_id = ?",
            (pref, cust_id),
        )
        conn.commit()
        conn.close()
        self.refresh_ui_table()
        self._select_driver_row_by_cust_id(cust_id)

    def import_json_data(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Historic Race Log(s)", "", "JSON Files (*.json)"
        )
        if not file_paths:
            return

        total_files = 0
        total_races_imported = 0
        total_results_imported = 0
        errors: list[str] = []

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        for file_path in file_paths:
            if not file_path:
                continue
            total_files += 1
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                races, series_name, race_timestamp = _parse_races_from_json(data)
                license_text_fallback = None
                if isinstance(data, dict) and isinstance(data.get("data"), dict):
                    # For event_result payloads we used license_category as a fallback earlier; keep that behavior.
                    cat = data["data"].get("license_category")
                    license_text_fallback = str(cat) if cat else None

                races_imported, results_imported = _import_race_entries(
                    cursor,
                    races,
                    series_name,
                    race_timestamp,
                    license_text_fallback,
                )

                total_races_imported += races_imported
                total_results_imported += results_imported

                if results_imported == 0:
                    errors.append(f"{file_path}: no race results found/imported")

            except Exception as e:
                errors.append(f"{file_path}: {e}")

        conn.commit()
        conn.close()

        self.refresh_ui_table()

        if total_results_imported == 0:
            QMessageBox.warning(
                self,
                "Import Completed (No Results Found)",
                "No race results were imported from the selected file(s).\n\n"
                "This usually means the JSON structure/keys don't match what the importer expects.\n"
                "Supported:\n"
                "- iRacing 'event_result' JSON (imports Race session), or\n"
                "- custom {'races': [...]} format.\n\n"
                + ("\n\nDetails:\n" + "\n".join(errors[:10]) if errors else ""),
            )
            return

        detail = ""
        if errors:
            detail = "\n\nSome files had issues:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                detail += f"\n... and {len(errors) - 10} more."

        QMessageBox.information(
            self,
            "Import Successful",
            f"Imported {total_results_imported} driver results across {total_races_imported} races from {total_files} file(s)."
            + detail,
        )

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.stop()
        event.accept()

