"""Starting-grid order from iRacing SDK (grid walk / pre-race review)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GridSlot:
    position: int
    cust_id: int
    name: str
    car_idx: int | None = None


def build_car_idx_directory(ir) -> dict[int, tuple[int, str]]:
    """Map telemetry CarIdx to (cust_id, display name)."""
    directory: dict[int, tuple[int, str]] = {}
    try:
        driver_info = ir["DriverInfo"]
        if not isinstance(driver_info, dict):
            return directory
        drivers_raw = driver_info.get("Drivers") or []
    except Exception:
        return directory

    if not isinstance(drivers_raw, list):
        return directory

    for entry in drivers_raw:
        if not isinstance(entry, dict):
            continue
        if entry.get("CarIsPaceCar") or entry.get("IsPaceCar"):
            continue
        if entry.get("UserName") == "Pace Car":
            continue

        car_idx = entry.get("CarIdx")
        cust_id = entry.get("UserID")
        if cust_id is None:
            cust_id = entry.get("CustID")
        if car_idx is None or cust_id is None:
            continue

        try:
            idx = int(car_idx)
            cid = int(cust_id)
        except (TypeError, ValueError):
            continue

        name = entry.get("UserName") or entry.get("UserNameShort") or f"Driver {cid}"
        directory[idx] = (cid, str(name))

    return directory


def _player_cust_id(ir, directory: dict[int, tuple[int, str]]) -> int | None:
    try:
        player_idx = int(ir["PlayerCarIdx"])
    except Exception:
        return None
    pair = directory.get(player_idx)
    return pair[0] if pair else None


def _slots_from_car_idx_position(ir, directory: dict[int, tuple[int, str]]) -> list[GridSlot]:
    try:
        positions = list(ir["CarIdxPosition"])
    except Exception:
        return []

    slots: list[GridSlot] = []
    for car_idx, raw_pos in enumerate(positions):
        try:
            position = int(raw_pos)
        except (TypeError, ValueError):
            continue
        if position <= 0:
            continue
        pair = directory.get(car_idx)
        if pair is None:
            continue
        cust_id, name = pair
        slots.append(
            GridSlot(position=position, cust_id=cust_id, name=name, car_idx=car_idx)
        )

    slots.sort(key=lambda s: s.position)
    return _dedupe_positions(slots)


def _dedupe_positions(slots: list[GridSlot]) -> list[GridSlot]:
    seen: set[int] = set()
    unique: list[GridSlot] = []
    for slot in slots:
        if slot.position in seen:
            continue
        seen.add(slot.position)
        unique.append(slot)
    return unique


def _current_session_dict(ir) -> dict | None:
    session_num = 0
    try:
        session_num = int(ir["SessionNum"] or 0)
    except Exception:
        session_num = 0

    try:
        info = ir["SessionInfo"]
        if not isinstance(info, dict):
            return None
        sessions = info.get("Sessions")
        if not isinstance(sessions, list):
            return None
    except Exception:
        return None

    for entry in sessions:
        if isinstance(entry, dict) and int(entry.get("SessionNum", -1)) == session_num:
            return entry

    for entry in reversed(sessions):
        if isinstance(entry, dict):
            return entry
    return None


def _slots_from_results_positions(
    ir, directory: dict[int, tuple[int, str]]
) -> list[GridSlot]:
    session = _current_session_dict(ir)
    if session is None:
        return []

    results = session.get("ResultsPositions")
    if results is None:
        return []

    entries: list[dict] = []
    if isinstance(results, list):
        entries = [e for e in results if isinstance(e, dict)]
    elif isinstance(results, dict):
        entries = [v for v in results.values() if isinstance(v, dict)]

    slots: list[GridSlot] = []
    for entry in entries:
        try:
            position = int(entry.get("Position") or 0)
        except (TypeError, ValueError):
            continue
        if position <= 0:
            continue

        cust_id = entry.get("UserID")
        if cust_id is None:
            cust_id = entry.get("CustID")
        name = entry.get("UserName") or entry.get("UserNameShort")

        car_idx = entry.get("CarIdx")
        try:
            car_idx_int = int(car_idx) if car_idx is not None else None
        except (TypeError, ValueError):
            car_idx_int = None

        if cust_id is None and car_idx_int is not None:
            pair = directory.get(car_idx_int)
            if pair:
                cust_id, name = pair

        if cust_id is None:
            continue

        try:
            cid = int(cust_id)
        except (TypeError, ValueError):
            continue

        if not name and car_idx_int is not None:
            pair = directory.get(car_idx_int)
            name = pair[1] if pair else f"Driver {cid}"
        slots.append(
            GridSlot(
                position=position,
                cust_id=cid,
                name=str(name or f"Driver {cid}"),
                car_idx=car_idx_int,
            )
        )

    slots.sort(key=lambda s: s.position)
    return _dedupe_positions(slots)


def parse_starting_grid(ir) -> tuple[list[GridSlot], int | None] | None:
    """
    Return grid slots in starting order and the player's cust_id, or None if unknown.
    Prefers live CarIdxPosition, then SessionInfo ResultsPositions.
    """
    directory = build_car_idx_directory(ir)
    if not directory:
        return None

    from_positions = _slots_from_car_idx_position(ir, directory)
    from_results = _slots_from_results_positions(ir, directory)
    slots = from_positions if len(from_positions) >= len(from_results) else from_results

    if len(slots) < 2:
        return None

    player_cust = _player_cust_id(ir, directory)
    return slots, player_cust


def slots_to_payload(slots: list[GridSlot]) -> list[dict]:
    return [
        {
            "position": s.position,
            "cust_id": s.cust_id,
            "name": s.name,
            "car_idx": s.car_idx,
        }
        for s in slots
    ]
