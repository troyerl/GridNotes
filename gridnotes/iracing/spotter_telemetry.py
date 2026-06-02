"""iRacing SDK telemetry helpers for the audio spotter."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SPOTTER_GAP_SECONDS = 1.5

# iRacing SessionFlags (fallbacks if pyirsdk constants are missing)
_SESS_FLAG_GREEN = 0x0004
_SESS_FLAG_CHECKERED = 0x0008
_SESS_FLAG_YELLOW = 0x0002


def _session_flag_constants() -> tuple[int, int, int]:
    try:
        import irsdk

        return (
            int(getattr(irsdk, "SESS_FLAG_GREEN", _SESS_FLAG_GREEN)),
            int(getattr(irsdk, "SESS_FLAG_CHECKERED", _SESS_FLAG_CHECKERED)),
            int(getattr(irsdk, "SESS_FLAG_YELLOW", _SESS_FLAG_YELLOW)),
        )
    except Exception:
        return _SESS_FLAG_GREEN, _SESS_FLAG_CHECKERED, _SESS_FLAG_YELLOW


def _normalize_lap_dist_delta(delta: float) -> float:
    if delta > 0.5:
        delta -= 1.0
    elif delta < -0.5:
        delta += 1.0
    return delta


def _as_float_list(value, length: int = 64) -> list[float]:
    if value is None:
        return []
    try:
        items = list(value)
    except TypeError:
        return []
    return [float(items[i]) if i < len(items) else 0.0 for i in range(min(len(items), length))]


def _as_int_list(value, length: int = 64) -> list[int]:
    if value is None:
        return []
    try:
        items = list(value)
    except TypeError:
        return []
    return [int(items[i]) if i < len(items) else 0 for i in range(min(len(items), length))]


def _as_bool_list(value, length: int = 64) -> list[bool]:
    if value is None:
        return []
    try:
        items = list(value)
    except TypeError:
        return []
    return [bool(items[i]) if i < len(items) else False for i in range(min(len(items), length))]


def build_car_idx_to_cust_id(ir) -> dict[int, int]:
    """Map telemetry CarIdx to iRacing customer ID from DriverInfo."""
    mapping: dict[int, int] = {}
    try:
        driver_info = ir["DriverInfo"]
        if not isinstance(driver_info, dict):
            return mapping
        drivers_raw = driver_info.get("Drivers") or []
    except Exception:
        return mapping

    if not isinstance(drivers_raw, list):
        return mapping

    for entry in drivers_raw:
        if not isinstance(entry, dict):
            continue
        car_idx = entry.get("CarIdx")
        cust_id = entry.get("UserID")
        if cust_id is None:
            cust_id = entry.get("CustID")
        if car_idx is None or cust_id is None:
            continue
        try:
            mapping[int(car_idx)] = int(cust_id)
        except (TypeError, ValueError):
            continue
    return mapping


def is_green_flag_run(ir) -> bool:
    """True when the session is under green (not checker/yellow-only)."""
    try:
        if bool(ir["IsReplayPlaying"]):
            return False
    except Exception:
        pass

    try:
        flags = int(ir["SessionFlags"] or 0)
    except Exception:
        return False

    green, checker, yellow = _session_flag_constants()
    if flags & checker:
        return False
    if (flags & yellow) and not (flags & green):
        return False
    if not (flags & green):
        return False

    try:
        player = int(ir["PlayerCarIdx"])
        on_pit = _as_bool_list(ir["CarIdxOnPitRoad"])
        if player < len(on_pit) and on_pit[player]:
            return False
    except Exception:
        pass

    try:
        speed = float(ir["Speed"] or 0)
        if speed < 1.0:
            return False
    except Exception:
        pass

    return True


def find_car_behind(ir, max_gap_sec: float = SPOTTER_GAP_SECONDS) -> tuple[int, float] | None:
    """Return (car_idx, gap_seconds) for the closest car behind the player within *max_gap_sec*."""
    try:
        player = int(ir["PlayerCarIdx"])
        lap_dist = _as_float_list(ir["CarIdxLapDistPct"])
        lap = _as_int_list(ir["CarIdxLap"])
        on_pit = _as_bool_list(ir["CarIdxOnPitRoad"])
    except Exception:
        return None

    if player >= len(lap_dist):
        return None
    if player < len(on_pit) and on_pit[player]:
        return None

    player_dist = lap_dist[player]
    player_lap = lap[player] if player < len(lap) else 0

    est: list[float] | None = None
    try:
        est = _as_float_list(ir["CarIdxEstTime"])
    except Exception:
        est = None

    lap_time = 90.0
    try:
        current = float(ir["LapCurrentLapTime"] or 0)
        if current > 1.0:
            lap_time = current
        else:
            last = float(ir["LapLastLapTime"] or 0)
            if last > 1.0:
                lap_time = last
    except Exception:
        pass

    best_idx: int | None = None
    best_gap = max_gap_sec + 1.0
    limit = min(64, len(lap_dist))

    for car_idx in range(limit):
        if car_idx == player:
            continue
        if car_idx < len(on_pit) and on_pit[car_idx]:
            continue
        if car_idx < len(lap) and int(lap[car_idx]) != player_lap:
            continue

        delta = _normalize_lap_dist_delta(lap_dist[car_idx] - player_dist)
        if delta >= 0:
            continue

        if est is not None and car_idx < len(est) and player < len(est):
            gap = float(est[car_idx]) - float(est[player])
            if gap <= 0:
                continue
        else:
            gap = abs(delta) * lap_time

        if 0 < gap <= max_gap_sec and gap < best_gap:
            best_gap = gap
            best_idx = car_idx

    if best_idx is None:
        return None
    return best_idx, best_gap


def resolve_cust_id_behind(
    ir,
    car_idx_map: dict[int, int],
    max_gap_sec: float = SPOTTER_GAP_SECONDS,
) -> tuple[int, float] | None:
    """Return (cust_id, gap_seconds) for a flagged car behind the player, if any."""
    behind = find_car_behind(ir, max_gap_sec=max_gap_sec)
    if behind is None:
        return None
    car_idx, gap = behind
    cust_id = car_idx_map.get(car_idx)
    if cust_id is None:
        return None
    return cust_id, gap
