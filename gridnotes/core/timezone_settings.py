"""Display timezone preference (defaults to the system timezone)."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

from ..data.db import get_setting, set_setting

logger = logging.getLogger(__name__)

TIMEZONE_SETTING_KEY = "display_timezone"
FALLBACK_TIMEZONE = "UTC"

# Checked when only a UTC offset is known (no IANA id from the OS).
_US_OFFSET_CANDIDATES = (
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Phoenix",
    "America/Anchorage",
    "Pacific/Honolulu",
)

_WINDOWS_TZ_MAP: dict[str, str] = {
    "Pacific Standard Time": "America/Los_Angeles",
    "Mountain Standard Time": "America/Denver",
    "US Mountain Standard Time": "America/Phoenix",
    "Central Standard Time": "America/Chicago",
    "Eastern Standard Time": "America/New_York",
    "US Eastern Standard Time": "America/Indiana/Indianapolis",
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


_tzpath_configured = False


def configure_tzpath_for_frozen() -> None:
    """Ensure bundled tzdata is visible to zoneinfo in PyInstaller builds."""
    global _tzpath_configured
    if _tzpath_configured or not getattr(sys, "frozen", False):
        return
    _tzpath_configured = True
    try:
        base = getattr(sys, "_MEIPASS", "")
        for subpath in ("tzdata/zoneinfo", "zoneinfo"):
            tz_root = os.path.join(base, subpath)
            if not os.path.isdir(tz_root):
                continue
            existing = os.environ.get("TZPATH", "")
            parts = [p for p in existing.split(os.pathsep) if p]
            if tz_root in parts:
                return
            parts.append(tz_root)
            os.environ["TZPATH"] = os.pathsep.join(parts)
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


def _normalize_iana_id(raw) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="ignore").strip()
    else:
        text = str(raw).strip()
    if not text:
        return None
    if text.startswith(":"):
        text = text[1:]
    if _is_valid_zone(text):
        return text
    return None


def _detect_qt_system_timezone() -> str | None:
    """PyQt reads the OS zone (Windows, macOS, Linux) as an IANA id."""
    try:
        from PyQt6.QtCore import QTimeZone

        zone_id = QTimeZone.systemTimeZone().id()
        return _normalize_iana_id(zone_id)
    except Exception:
        logger.debug("Could not read timezone from Qt", exc_info=True)
        return None


def _detect_tz_environment() -> str | None:
    raw = os.environ.get("TZ", "").strip()
    if not raw or raw.upper() == "UTC":
        return None
    return _normalize_iana_id(raw)


def _detect_unix_localtime() -> str | None:
    if sys.platform == "win32":
        return None
    for path in ("/etc/localtime", "/private/etc/localtime"):
        try:
            target = os.path.realpath(path)
        except OSError:
            continue
        marker = "zoneinfo/"
        if marker in target:
            zone = target.split(marker, 1)[1]
            if _is_valid_zone(zone):
                return zone
    return None


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


def _detect_from_clock_key() -> str | None:
    configure_tzpath_for_frozen()
    try:
        local = datetime.now().astimezone().tzinfo
        key = getattr(local, "key", None)
        if isinstance(key, str) and _is_valid_zone(key):
            return key
    except Exception:
        logger.debug("Could not read timezone key from local clock", exc_info=True)
    return None


def _detect_from_utc_offset() -> str | None:
    """Match the PC offset to a US zone (EST/CST/MST/PST, etc.) when IANA id is missing."""
    configure_tzpath_for_frozen()
    try:
        local_offset = datetime.now().astimezone().utcoffset()
    except Exception:
        return None
    if local_offset is None:
        return None

    for name in _US_OFFSET_CANDIDATES:
        try:
            if datetime.now(ZoneInfo(name)).utcoffset() == local_offset:
                return name
        except Exception:
            continue
    return None


def detect_system_timezone() -> str:
    """Best-effort IANA timezone for the PC running GridNotes."""
    for detector in (
        _detect_qt_system_timezone,
        _detect_from_clock_key,
        _detect_tz_environment,
        _detect_unix_localtime,
        _detect_windows_timezone,
        _detect_from_utc_offset,
    ):
        zone = detector()
        if zone:
            return zone
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


def timezone_abbrev_for(iana: str, *, when: datetime | None = None) -> str:
    """Short label such as EST, CDT, PST (uses Qt when available)."""
    when = when or datetime.now(_zone_info_cached(iana))
    try:
        from PyQt6.QtCore import QDateTime, QTimeZone

        qt_zone = QTimeZone(iana.encode("utf-8"))
        if qt_zone.isValid():
            qt_dt = QDateTime.fromSecsSinceEpoch(int(when.timestamp()))
            abbr = qt_zone.abbreviation(qt_dt).strip()
            if abbr:
                return abbr
    except Exception:
        pass
    try:
        abbr = when.astimezone(_zone_info_cached(iana)).tzname() or ""
        if abbr.strip():
            return abbr.strip()
    except Exception:
        pass
    return iana.split("/")[-1].replace("_", " ")


def timezone_label(iana: str) -> str:
    """Human-readable label for combobox entries, e.g. ``America/Chicago (CDT)``."""
    try:
        zi = _zone_info_cached(iana)
        now = datetime.now(zi)
        abbr = timezone_abbrev_for(iana, when=now)
        place = iana.replace("_", " ")
        if abbr and abbr not in place:
            return f"{place} ({abbr})"
        return place
    except Exception:
        return iana.replace("_", " ")


def system_timezone_summary() -> str:
    """One-line system zone for Settings copy, e.g. ``Eastern (EDT)``."""
    zone = detect_system_timezone()
    abbr = timezone_abbrev_for(zone)
    if zone.startswith("America/"):
        region = zone.rsplit("/", 1)[-1].replace("_", " ")
        if abbr:
            return f"{region} ({abbr})"
    return timezone_label(zone)


def display_timezone_abbrev() -> str:
    """Short suffix for UI copy (e.g. EST, CDT, PST)."""
    return timezone_abbrev_for(get_display_timezone())


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
    rows: list[tuple[str, str]] = [
        ("", f"System default — {system_timezone_summary()}"),
    ]
    for zone in available_display_timezones():
        rows.append((zone, timezone_label(zone)))
    return rows
