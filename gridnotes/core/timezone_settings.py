"""Display timezone preference (defaults to the system timezone)."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

from ..data.db import get_setting, set_setting

logger = logging.getLogger(__name__)

TIMEZONE_SETTING_KEY = "display_timezone"
FALLBACK_TIMEZONE = "UTC"

_WINDOWS_TZ_MAP: dict[str, str] = {
    "Pacific Standard Time": "America/Los_Angeles",
    "Mountain Standard Time": "America/Denver",
    "US Mountain Standard Time": "America/Phoenix",
    "Central Standard Time": "America/Chicago",
    "Eastern Standard Time": "America/New_York",
    "Atlantic Standard Time": "America/Halifax",
    "Alaskan Standard Time": "America/Anchorage",
    "Hawaiian Standard Time": "Pacific/Honolulu",
    "GMT Standard Time": "Europe/London",
    "W. Europe Standard Time": "Europe/Berlin",
    "Central Europe Standard Time": "Europe/Budapest",
    "Romance Standard Time": "Europe/Paris",
    "FLE Standard Time": "Europe/Helsinki",
    "E. Europe Standard Time": "Europe/Bucharest",
    "Turkey Standard Time": "Europe/Istanbul",
    "Arab Standard Time": "Asia/Riyadh",
    "India Standard Time": "Asia/Kolkata",
    "China Standard Time": "Asia/Shanghai",
    "Tokyo Standard Time": "Asia/Tokyo",
    "AUS Eastern Standard Time": "Australia/Sydney",
    "Cen. Australia Standard Time": "Australia/Adelaide",
    "W. Australia Standard Time": "Australia/Perth",
    "New Zealand Standard Time": "Pacific/Auckland",
    "UTC": "UTC",
}


def configure_tzpath_for_frozen() -> None:
    """Ensure bundled tzdata is visible to zoneinfo in PyInstaller builds."""
    if not getattr(sys, "frozen", False):
        return
    try:
        import os

        base = getattr(sys, "_MEIPASS", "")
        for subpath in ("tzdata/zoneinfo", "zoneinfo"):
            tz_root = os.path.join(base, subpath)
            if os.path.isdir(tz_root):
                existing = os.environ.get("TZPATH", "")
                paths = [p for p in (existing, tz_root) if p]
                os.environ["TZPATH"] = os.pathsep.join(paths)
                return
    except Exception:
        logger.debug("Could not configure TZPATH for frozen build", exc_info=True)


def _is_valid_zone(name: str) -> bool:
    if not name or "/" not in name:
        return name == "UTC"
    try:
        configure_tzpath_for_frozen()
        ZoneInfo(name)
        return True
    except Exception:
        return False


def _detect_windows_timezone() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation",
        ) as key:
            win_name, _ = winreg.QueryValueEx(key, "TimeZoneKeyName")
        mapped = _WINDOWS_TZ_MAP.get(str(win_name).strip())
        if mapped and _is_valid_zone(mapped):
            return mapped
    except OSError:
        logger.debug("Could not read Windows timezone registry", exc_info=True)
    return None


def detect_system_timezone() -> str:
    """Best-effort IANA timezone for the PC running GridNotes."""
    configure_tzpath_for_frozen()
    try:
        local = datetime.now().astimezone().tzinfo
        key = getattr(local, "key", None)
        if isinstance(key, str) and _is_valid_zone(key):
            return key
    except Exception:
        logger.debug("Could not read timezone from local clock", exc_info=True)

    mapped = _detect_windows_timezone()
    if mapped:
        return mapped

    return FALLBACK_TIMEZONE


def get_saved_timezone() -> str | None:
    """Explicit user choice, or None to follow the system timezone."""
    raw = get_setting(TIMEZONE_SETTING_KEY)
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if _is_valid_zone(text):
        return text
    logger.warning("Ignoring invalid display_timezone setting: %s", text)
    return None


def get_display_timezone() -> str:
    """IANA zone used for last-raced and other local timestamps."""
    saved = get_saved_timezone()
    if saved:
        return saved
    return detect_system_timezone()


def set_display_timezone(iana: str | None) -> None:
    """Persist timezone; pass None or '' to use system default."""
    text = (iana or "").strip()
    if not text:
        set_setting(TIMEZONE_SETTING_KEY, None)
    elif _is_valid_zone(text):
        set_setting(TIMEZONE_SETTING_KEY, text)
    else:
        raise ValueError(f"Unknown timezone: {iana}")
    clear_timezone_cache()


def uses_system_timezone() -> bool:
    return get_saved_timezone() is None


@lru_cache(maxsize=64)
def _zone_info_cached(name: str) -> ZoneInfo:
    configure_tzpath_for_frozen()
    return ZoneInfo(name)


def display_zone_info() -> ZoneInfo:
    return _zone_info_cached(get_display_timezone())


def clear_timezone_cache() -> None:
    _zone_info_cached.cache_clear()


def timezone_label(iana: str) -> str:
    """Human-readable label for combobox entries."""
    try:
        zi = _zone_info_cached(iana)
        now = datetime.now(zi)
        abbr = (now.tzname() or "").strip()
        place = iana.replace("_", " ")
        if abbr and abbr not in place:
            return f"{place} ({abbr})"
        return place
    except Exception:
        return iana.replace("_", " ")


def display_timezone_abbrev() -> str:
    """Short suffix for UI copy (e.g. ET, CDT, BST)."""
    try:
        now = datetime.now(display_zone_info())
        abbr = (now.tzname() or "").strip()
        if abbr:
            return abbr
    except Exception:
        pass
    name = get_display_timezone()
    return name.split("/")[-1].replace("_", " ")


def available_display_timezones() -> list[str]:
    zones = sorted(
        z
        for z in available_timezones()
        if "/" in z and not z.startswith("Etc/")
    )
    if FALLBACK_TIMEZONE not in zones:
        zones.insert(0, FALLBACK_TIMEZONE)
    return zones


def timezone_combo_entries() -> list[tuple[str, str]]:
    """
    Combo box rows: (stored value, label).
    Empty value means follow the system timezone.
    """
    system = detect_system_timezone()
    rows: list[tuple[str, str]] = [
        ("", f"System default — {timezone_label(system)}"),
    ]
    for zone in available_display_timezones():
        rows.append((zone, timezone_label(zone)))
    return rows
