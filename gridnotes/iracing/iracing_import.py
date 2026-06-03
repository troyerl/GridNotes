"""iRacing JSON parsing and race result import."""

from __future__ import annotations

import sqlite3
from typing import Literal

from ..core.utils import normalize_1_based, sqlite_row_to_int

# iRacing reason_out_id (0 = finished on track; excluded from DNF stats)
REASON_OUT_RUNNING = 0
REASON_OUT_DISCONNECTED = 1
REASON_OUT_EJECTED = 2
REASON_OUT_QUIT = 3
REASON_OUT_DISQUALIFIED = 4

REASON_OUT_TEXT_TO_ID = {
    "running": REASON_OUT_RUNNING,
    "disconnected": REASON_OUT_DISCONNECTED,
    "ejected": REASON_OUT_EJECTED,
    "quit": REASON_OUT_QUIT,
    "disqualified": REASON_OUT_DISQUALIFIED,
}

ImportOutcome = Literal["imported", "updated", "skipped"]


def normalize_reason_out_id(reason_out_id, reason_out) -> int | None:
    """Return 0 for Running, 1-4 for known DNF reasons, None if unknown/missing."""
    if isinstance(reason_out_id, int) and reason_out_id in REASON_OUT_TEXT_TO_ID.values():
        return reason_out_id
    if isinstance(reason_out, str):
        key = reason_out.strip().lower()
        if key in REASON_OUT_TEXT_TO_ID:
            return REASON_OUT_TEXT_TO_ID[key]
    return None


def _license_group_from_level(level: int | None) -> str | None:
    if not isinstance(level, int):
        return None
    if level <= 4:
        return "R"
    if level <= 8:
        return "D"
    if level <= 12:
        return "C"
    if level <= 16:
        return "B"
    if level <= 20:
        return "A"
    if level <= 24:
        return "Pro"
    if level <= 28:
        return "Pro/WC"
    return None


def _sr_from_sub_level(sub_level: int | None) -> float | None:
    if not isinstance(sub_level, int) or sub_level < 0:
        return None
    return round(sub_level / 100.0, 2)


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


def _upsert_driver(cursor: sqlite3.Cursor, cust_id: int, name) -> None:
    cursor.execute(
        """
        INSERT INTO drivers (cust_id, driver_name)
        VALUES (?, ?)
        ON CONFLICT(cust_id) DO UPDATE SET driver_name=excluded.driver_name
        """,
        (cust_id, name),
    )


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


def _save_race_result(
    cursor: sqlite3.Cursor,
    *,
    cust_id: int,
    sub_id: int,
    series_name: str | None,
    finish,
    incidents,
    ir_change: int,
    license_text: str,
    start_pos,
    reason_out,
    reason_out_id,
    race_timestamp: str | None,
) -> ImportOutcome:
    row_values = (
        cust_id,
        sub_id,
        series_name,
        finish,
        incidents,
        ir_change,
        license_text,
        start_pos,
        reason_out,
        reason_out_id,
        race_timestamp,
    )

    if sub_id != 0:
        cursor.execute(
            """
            UPDATE race_results
            SET series_name = ?,
                finish_position = ?,
                incidents = ?,
                irating_change = ?,
                license_class = ?,
                starting_position = ?,
                reason_out = ?,
                reason_out_id = ?,
                race_at = COALESCE(?, race_at)
            WHERE cust_id = ? AND subsession_id = ?
            """,
            (
                series_name,
                finish,
                incidents,
                ir_change,
                license_text,
                start_pos,
                reason_out,
                reason_out_id,
                race_timestamp,
                cust_id,
                sub_id,
            ),
        )
        if cursor.rowcount > 0:
            return "updated"

        cursor.execute(
            """
            INSERT INTO race_results (
                cust_id,
                subsession_id,
                series_name,
                finish_position,
                incidents,
                irating_change,
                license_class,
                starting_position,
                reason_out,
                reason_out_id,
                race_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row_values,
        )
        return "imported"

    cursor.execute(
        """
        INSERT OR IGNORE INTO race_results (
            cust_id,
            subsession_id,
            series_name,
            finish_position,
            incidents,
            irating_change,
            license_class,
            starting_position,
            reason_out,
            reason_out_id,
            race_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row_values,
    )
    return "imported" if cursor.rowcount else "skipped"


def parse_iracing_event_result(data: dict) -> tuple[list[dict], str | None, str | None]:
    payload = data.get("data")
    if not isinstance(payload, dict):
        return ([], None, None)

    sub_id = sqlite_row_to_int(payload.get("subsession_id")) or 0
    series_name = payload.get("series_name") or payload.get("season_name")
    race_timestamp = payload.get("end_time") or payload.get("start_time")
    sessions = payload.get("session_results", [])
    if not isinstance(sessions, list):
        return ([], series_name, race_timestamp)

    for session in sessions:
        if not isinstance(session, dict):
            continue
        if session.get("simsession_type_name") == "Race" or session.get("simsession_type") == 6:
            return (
                [{"subsession_id": sub_id, "results": session.get("results", [])}],
                series_name,
                race_timestamp,
            )
    return ([], series_name, race_timestamp)


def parse_races_from_json(data) -> tuple[list[dict], str | None, str | None]:
    if isinstance(data, dict) and data.get("type") == "event_result":
        return parse_iracing_event_result(data)
    if isinstance(data, dict):
        races = data.get("races", [])
        return (races if isinstance(races, list) else [], None, None)
    if isinstance(data, list):
        return (data, None, None)
    return ([], None, None)


def import_race_entries(
    cursor: sqlite3.Cursor,
    races: list[dict],
    series_name: str | None,
    race_timestamp: str | None,
    license_text_fallback: str | None,
) -> tuple[int, int, int, int, set[int]]:
    """Returns (races_imported, results_imported, results_updated, results_skipped, affected_cust_ids)."""
    races_imported = 0
    results_imported = 0
    results_updated = 0
    results_skipped = 0
    affected_cust_ids: set[int] = set()

    for entry in races:
        if not isinstance(entry, dict):
            continue
        sub_id = sqlite_row_to_int(entry.get("subsession_id"))
        if sub_id is None:
            sub_id = sqlite_row_to_int(entry.get("session_id"))
        sub_id = sub_id or 0
        results = entry.get("results", [])
        if not isinstance(results, list):
            continue

        race_had_result = False
        for driver in results:
            if not isinstance(driver, dict):
                continue

            cust_id = sqlite_row_to_int(driver.get("cust_id"))
            if cust_id is None:
                continue

            affected_cust_ids.add(int(cust_id))
            name = driver.get("name", driver.get("display_name"))
            _upsert_driver(cursor, cust_id, name)

            finish = driver.get("finish", driver.get("finish_position"))
            finish = normalize_1_based(finish) if finish is not None else None
            start_pos = normalize_1_based(driver.get("starting_position"))

            reason_out = driver.get("reason_out")
            reason_out = reason_out.strip() if isinstance(reason_out, str) and reason_out.strip() else None
            reason_out_id = normalize_reason_out_id(driver.get("reason_out_id"), reason_out)
            if reason_out_id == REASON_OUT_RUNNING:
                reason_out = reason_out or "Running"

            license_text = driver.get("license", "Unknown")
            if license_text == "Unknown" and license_text_fallback:
                license_text = license_text_fallback

            outcome = _save_race_result(
                cursor,
                cust_id=cust_id,
                sub_id=sub_id,
                series_name=series_name,
                finish=finish,
                incidents=driver.get("incidents", 0),
                ir_change=_compute_irating_change(driver),
                license_text=license_text,
                start_pos=start_pos,
                reason_out=reason_out,
                reason_out_id=reason_out_id,
                race_timestamp=race_timestamp,
            )

            if outcome == "skipped":
                results_skipped += 1
                continue
            if outcome == "updated":
                results_updated += 1
            else:
                results_imported += 1

            _maybe_update_last_seen(
                cursor,
                cust_id,
                race_timestamp,
                _compute_new_irating(driver),
                _compute_new_sr(driver),
                _compute_last_license(driver),
                series_name,
                start_pos,
            )
            race_had_result = True

        if race_had_result:
            races_imported += 1

    return (
        races_imported,
        results_imported,
        results_updated,
        results_skipped,
        affected_cust_ids,
    )


def sync_live_session_drivers(cursor: sqlite3.Cursor, active_drivers: list[dict]) -> list[int]:
    """Ensure live session drivers exist in the book. Returns newly added cust_ids."""
    added_ids: list[int] = []
    for driver in active_drivers:
        if not isinstance(driver, dict):
            continue
        cust_id = sqlite_row_to_int(driver.get("cust_id"))
        if cust_id is None:
            continue
        name = driver.get("name") or driver.get("display_name") or f"Driver {cust_id}"
        cursor.execute("SELECT 1 FROM drivers WHERE cust_id = ?", (cust_id,))
        existed = cursor.fetchone() is not None
        _upsert_driver(cursor, cust_id, name)
        if not existed:
            added_ids.append(cust_id)
    return added_ids
